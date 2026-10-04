"""Subprocess execution for CLI integrations: timeouts, cancellation, and process-group cleanup."""

from __future__ import annotations

import locale
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from fmind_dot.errors import CommandTimeoutError, DotError

# SIGTERM grace before SIGKILL: long enough for git to unlock, short enough for Ctrl+C.
_TERMINATION_GRACE_SECONDS = 2.0
_TERMINATION_TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class CommandResult:
    """Captured command outcome."""

    stdout: str
    stderr: str
    returncode: int


_CREDENTIAL_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
# Provider token prefixes, plus any long opaque run that could be a credential or signature.
_OPAQUE_TOKEN = re.compile(r"\b(?:gh[opsur]_|github_pat_|glpat-)?[A-Za-z0-9_+/=-]{32,}")


def diagnostic_line(text: str, limit: int = 160) -> str:
    """Return the first non-empty output line without credentials, control characters, or excess length."""
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    line = "".join(character for character in line if character.isprintable())
    line = _OPAQUE_TOKEN.sub("<redacted>", _CREDENTIAL_URL.sub(r"\1<redacted>@", line))
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"


def _environment(env: Mapping[str, str] | None) -> dict[str, str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return command_env


def _signal(process: subprocess.Popen[str], signum: signal.Signals, *, group: bool = True) -> None:
    """Signal the child's process group, falling back to the child itself."""
    if group:
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signum)
            return
    # Popen ignores signals once the child has been reaped.
    with suppress(ProcessLookupError):
        process.send_signal(signum)


def _terminate(process: subprocess.Popen[str], *, group: bool = True) -> None:
    """Stop the launched process and keep escaped descendants holding pipes from blocking."""
    try:
        # Let tools such as git release locks and refs before the hard kill.
        _signal(process, signal.SIGTERM, group=group)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
    finally:
        # A second interrupt during the grace period must still kill the process.
        _signal(process, signal.SIGKILL, group=group)
    # A descendant may create a new session while retaining these descriptors.
    # Closing our ends keeps its lifetime from extending the caller's timeout.
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    try:
        process.wait(timeout=_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()


@contextmanager
def _deferred_interrupts() -> Iterator[None]:
    """Leave Ctrl+C to an interactive child, which shares dot's foreground process group."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    # A handler, unlike SIG_IGN, resets to the default in the executed child.
    previous = signal.signal(signal.SIGINT, lambda _signum, _frame: None)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def _is_terminal(stream: IO[str] | None, default: IO[str]) -> bool:
    """Whether the child inherits a terminal on this descriptor (None means dot's own stream)."""
    with suppress(AttributeError, OSError, ValueError):
        return os.isatty((stream if stream is not None else default).fileno())
    return False


def _relay_lines(source: IO[str], target: IO[str] | None, on_line: Callable[[str], None]) -> None:
    """Echo each child line as it arrives, then let the caller react to it."""
    destination = target if target is not None else sys.stderr
    # The daemon thread owns the pipe and closes it at EOF, after any escaped descendant holding it exits.
    with suppress(OSError, ValueError), source:
        for line in source:
            destination.write(line)
            destination.flush()
            on_line(line)


class Runner:
    """Run external tools with timeout and process-group cleanup."""

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._process_lock = threading.Lock()
        self._processes: set[subprocess.Popen[str]] = set()

    def cancel(self) -> None:
        """Stop captured worker processes and prohibit subsequent commands."""
        self._cancelled.set()
        with self._process_lock:
            processes = tuple(self._processes)
        # The communicating worker owns its pipes and reaps the child.
        for process in processes:
            _signal(process, signal.SIGTERM)
        deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < deadline and any(process.poll() is None for process in processes):
            time.sleep(0.05)
        for process in processes:
            _signal(process, signal.SIGKILL)

    def which(self, command: str) -> Path | None:
        resolved = shutil.which(command)
        return Path(resolved) if resolved else None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        """Capture a command's output in its own session; undecodable bytes are replaced."""
        if not args:
            raise DotError("cannot run an empty command")
        if self._cancelled.is_set():
            raise DotError("operation cancelled")
        process = subprocess.Popen(  # noqa: S603 - argv is always a sequence, never a shell string. # nosemgrep: dangerous-subprocess-use-audit
            list(args),
            cwd=cwd,
            env=_environment(env),
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Text mode also applies universal newlines; tool output is not trusted text.
            encoding=locale.getencoding(),
            errors="replace",
            start_new_session=True,
        )
        try:
            with self._process_lock:
                self._processes.add(process)
            # Cancellation can land between launch and registration. Use the same
            # cleanup path as other failures, without trying to read closed pipes.
            if self._cancelled.is_set():
                raise DotError("operation cancelled")
            stdout, stderr = process.communicate(input_text, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            _terminate(process)
            raise CommandTimeoutError(f"command timed out: {args[0]}") from error
        except BaseException:
            _terminate(process)
            raise
        finally:
            with self._process_lock:
                self._processes.discard(process)
        if check and process.returncode != 0:
            # Tool stderr can contain credentials or provider payloads; callers opt in
            # to rendering bounded diagnostics only after they have classified them.
            raise DotError(f"command failed ({process.returncode}): {args[0]}")
        return CommandResult(stdout=stdout, stderr=stderr, returncode=process.returncode)

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stderr_line: Callable[[str], None] | None = None,
    ) -> int:
        """Run with the caller's terminal; `on_stderr_line` relays stderr so callers can react to prompts.

        A child using the terminal stays in dot's process group, so the terminal delivers Ctrl+C and
        Ctrl+Z to both. Without one, it gets its own group so that a SIGTERM to dot (timeout, a
        supervisor, CI cancellation) also stops the child's descendants.
        """
        if not args:
            raise DotError("cannot run an empty command")
        streams = [(stdin, sys.stdin), (stdout, sys.stdout)]
        if on_stderr_line is None:
            streams.append((stderr, sys.stderr))
        detached = not any(_is_terminal(stream, default) for stream, default in streams)
        with nullcontext() if detached else _deferred_interrupts():
            process = subprocess.Popen(  # noqa: S603 - argv is always a sequence, never a shell string. # nosemgrep: dangerous-subprocess-use-audit
                list(args),
                cwd=cwd,
                env=_environment(env),
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE if on_stderr_line is not None else stderr,
                text=True,
                errors="replace",
                process_group=0 if detached else None,
            )
            relay = None
            if on_stderr_line is not None and process.stderr is not None:
                # The relay owns the pipe: closing it while the thread reads would wait on its buffer lock.
                source, process.stderr = process.stderr, None
                relay = threading.Thread(target=_relay_lines, args=(source, stderr, on_stderr_line), daemon=True)
                relay.start()
            try:
                code = process.wait()
                if relay is not None:
                    # An escaped descendant may keep the pipe open; never wait on it indefinitely.
                    relay.join(timeout=_TERMINATION_TIMEOUT_SECONDS)
                if code == -signal.SIGINT:
                    raise KeyboardInterrupt
                return code
            except BaseException:
                _terminate(process, group=detached)
                raise


def run_parallel[T, R](runner: Runner, function: Callable[[T], R], items: Sequence[T], workers: int) -> list[R]:
    """Map items over a bounded pool; an interruption cancels every running command."""
    if not items:
        return []
    executor = ThreadPoolExecutor(max_workers=min(workers, len(items)))
    try:
        return list(executor.map(function, items))
    except BaseException:
        # Cancelled runners refuse new commands, so queued workers stop at their next call.
        runner.cancel()
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
