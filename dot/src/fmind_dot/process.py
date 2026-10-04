"""Bounded subprocess execution for CLI integrations."""

from __future__ import annotations

import locale
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock
from typing import IO

from fmind_dot.errors import DotError

# SIGTERM grace before SIGKILL: long enough for git to unlock, short enough for Ctrl+C.
_TERMINATION_GRACE_SECONDS = 2.0
_TERMINATION_TIMEOUT_SECONDS = 3
_PIPE_WRITE_BYTES = 4096
# Shared ceiling for every status probe captured with run_bounded.
PROBE_OUTPUT_LIMIT_BYTES = 64 * 1024
# Ceiling for ordinary captured commands; exceeding it fails instead of truncating their output.
RUN_OUTPUT_LIMIT_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class CommandResult:
    """Captured command outcome."""

    stdout: str
    stderr: str
    returncode: int
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def output_truncated(self) -> bool:
        """Report whether either captured stream exceeded the shared byte budget."""
        return self.stdout_truncated or self.stderr_truncated


_CREDENTIAL_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
# Provider token prefixes, plus any long opaque run that could be a credential or signature.
_OPAQUE_TOKEN = re.compile(r"\b(?:gh[opsur]_|github_pat_|glpat-)?[A-Za-z0-9_+/=-]{32,}")


def diagnostic_line(text: str, limit: int = 160) -> str:
    """Return the first non-empty output line without credentials, control characters, or excess length."""
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    line = "".join(character for character in line if character.isprintable())
    line = _OPAQUE_TOKEN.sub("<redacted>", _CREDENTIAL_URL.sub(r"\1<redacted>@", line))
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"


def _universal_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class _BoundedCapture:
    """Keep a shared output budget while callers continue draining both pipes."""

    def __init__(self, limit: int) -> None:
        self._remaining = limit
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.stdout_truncated = False
        self.stderr_truncated = False

    def append(self, stream: str, chunk: bytes) -> None:
        retained = chunk[: self._remaining]
        target = self.stdout if stream == "stdout" else self.stderr
        target.extend(retained)
        self._remaining -= len(retained)
        if len(retained) != len(chunk):
            if stream == "stdout":
                self.stdout_truncated = True
            else:
                self.stderr_truncated = True


def _remaining_time(deadline: float | None, timeout: float | None) -> float | None:
    if deadline is None or timeout is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("command", timeout)
    return remaining


def _communicate_bounded(
    process: subprocess.Popen[bytes],
    input_bytes: bytes | None,
    timeout: float | None,
    limit: int,
) -> _BoundedCapture:
    """Drain child pipes without retaining more than ``limit`` bytes in memory."""
    deadline = None if timeout is None else time.monotonic() + timeout
    captured = _BoundedCapture(limit)
    input_offset = 0
    input_view = memoryview(input_bytes or b"")
    with selectors.DefaultSelector() as selector:
        if process.stdin is not None:
            if input_bytes:
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()
        if process.stdout is not None:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        if process.stderr is not None:
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")

        while selector.get_map():
            ready = selector.select(_remaining_time(deadline, timeout))
            if not ready:
                _remaining_time(deadline, timeout)
                continue
            for key, _events in ready:
                if key.data == "stdin":
                    try:
                        input_offset += os.write(key.fd, input_view[input_offset : input_offset + _PIPE_WRITE_BYTES])
                    except BrokenPipeError:
                        if process.stdin is not None:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                    else:
                        if input_offset >= len(input_view) and process.stdin is not None:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                    continue
                chunk = os.read(key.fd, 32 * 1024)
                if chunk:
                    captured.append(key.data, chunk)
                else:
                    output = process.stdout if key.data == "stdout" else process.stderr
                    if output is not None:
                        selector.unregister(output)
                        output.close()
    process.wait(timeout=_remaining_time(deadline, timeout))
    return captured


def _signal_group(process: subprocess.Popen[str] | subprocess.Popen[bytes], signum: signal.Signals) -> bool:
    """Signal the child's process group and report whether the signal was delivered."""
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError, PermissionError:
        return False
    return True


def _terminate(process: subprocess.Popen[str] | subprocess.Popen[bytes]) -> None:
    """Stop the launched process group and keep escaped descendants holding pipes from blocking."""
    try:
        if os.name == "posix" and _signal_group(process, signal.SIGTERM):
            # Children own their session, so a terminal Ctrl+C never reaches them.
            # Let tools such as git release locks and refs before the hard kill.
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=_TERMINATION_GRACE_SECONDS)
    finally:
        # A second interrupt during the grace period must still kill the group.
        killed = os.name == "posix" and _signal_group(process, signal.SIGKILL)
        if not killed and process.poll() is None:
            process.kill()
    # A descendant may create a new session while retaining these descriptors.
    # Closing our ends keeps its lifetime from extending the caller's timeout.
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    try:
        process.wait(timeout=_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()


def _set_foreground(terminal: int, group: int) -> None:
    # The wrapper is in the background while its child owns the terminal.
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTTOU})
    try:
        with suppress(OSError):
            os.tcsetpgrp(terminal, group)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


@contextmanager
def _foreground_terminal(process: subprocess.Popen[bytes], stream: IO[str] | None) -> Iterator[int | None]:
    terminal = None
    if os.name == "posix":
        try:
            descriptor = (stream if stream is not None else sys.stdin).fileno()
            if os.isatty(descriptor) and os.tcgetpgrp(descriptor) == os.getpgrp():
                terminal = descriptor
        except OSError, ValueError:
            pass
    try:
        if terminal is not None:
            _set_foreground(terminal, process.pid)
            # A fast child may already have stopped on SIGTTIN before the handoff.
            with suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGCONT)
        yield terminal
    finally:
        if terminal is not None:
            _set_foreground(terminal, os.getpgrp())


def _relay_terminal_stop(process: subprocess.Popen[bytes], terminal: int | None) -> None:
    if terminal is None or process.poll() is not None:
        return
    try:
        stopped = os.waitid(os.P_PID, process.pid, os.WSTOPPED | os.WNOHANG)
    except ChildProcessError:
        return
    if stopped is not None:
        _set_foreground(terminal, os.getpgrp())
        # Let the shell suspend/resume dot as a job, then return the terminal to
        # its child. SIGSTOP also works when a host inherited ignored SIGTSTP.
        os.kill(os.getpid(), signal.SIGSTOP)
        _set_foreground(terminal, process.pid)
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGCONT)


def _wait_interactive(process: subprocess.Popen[bytes], terminal: int | None) -> int:
    if terminal is None:
        return process.wait()
    while True:
        _relay_terminal_stop(process, terminal)
        try:
            return process.wait(timeout=0.1)
        except subprocess.TimeoutExpired:
            pass


class Runner:
    """Run external tools with timeout and process-group cleanup."""

    def __init__(self) -> None:
        self._cancelled = Event()
        self._process_lock = Lock()
        self._processes: set[subprocess.Popen[bytes]] = set()

    def cancel(self) -> None:
        """Stop captured worker processes and prohibit subsequent commands."""
        self._cancelled.set()
        with self._process_lock:
            processes = tuple(self._processes)
        # The communicating worker owns its pipes and reaps the child.
        if os.name != "posix":
            for process in processes:
                if process.poll() is None:
                    process.kill()
            return
        for process in processes:
            if not _signal_group(process, signal.SIGTERM) and process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < deadline and any(process.poll() is None for process in processes):
            time.sleep(0.05)
        for process in processes:
            if not _signal_group(process, signal.SIGKILL) and process.poll() is None:
                process.kill()

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
        """Run a command whose complete output the caller needs; oversized output is an error."""
        result = self.run_bounded(
            args,
            cwd=cwd,
            input_text=input_text,
            env=env,
            timeout=timeout,
            check=check,
            max_output_bytes=RUN_OUTPUT_LIMIT_BYTES,
        )
        if result.output_truncated:
            raise DotError(f"command output exceeded {RUN_OUTPUT_LIMIT_BYTES} bytes: {args[0]}")
        return result

    def run_bounded(
        self,
        args: Sequence[str],
        *,
        max_output_bytes: int,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        """Run a command while draining all output and retaining one bounded byte budget."""
        if not args:
            raise DotError("cannot run an empty command")
        if max_output_bytes <= 0:
            raise DotError("maximum captured output must be positive")
        if self._cancelled.is_set():
            raise DotError("operation cancelled")
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        encoding = locale.getencoding()
        process = subprocess.Popen(  # noqa: S603 - argv is always a sequence, never a shell string. # nosemgrep: dangerous-subprocess-use-audit
            list(args),
            cwd=cwd,
            env=command_env,
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
        try:
            with self._process_lock:
                self._processes.add(process)
            # Cancellation can land between launch and registration. Use the same
            # cleanup path as other failures, without trying to read closed pipes.
            if self._cancelled.is_set():
                raise DotError("operation cancelled")
            capture = _communicate_bounded(
                process,
                input_text.encode(encoding) if input_text is not None else None,
                timeout,
                max_output_bytes,
            )
            # Undecodable bytes are replaced; tool output is not trusted text. Universal
            # newlines keep the text contract of subprocess text mode for every caller.
            result = CommandResult(
                stdout=_universal_newlines(capture.stdout.decode(encoding, errors="replace")),
                stderr=_universal_newlines(capture.stderr.decode(encoding, errors="replace")),
                returncode=process.returncode,
                stdout_truncated=capture.stdout_truncated,
                stderr_truncated=capture.stderr_truncated,
            )
        except subprocess.TimeoutExpired as error:
            _terminate(process)
            raise DotError(f"command timed out: {args[0]}") from error
        except BaseException:
            _terminate(process)
            raise
        finally:
            with self._process_lock:
                self._processes.discard(process)
        if check and result.returncode != 0:
            # Tool stderr can contain credentials or provider payloads; callers opt in
            # to rendering bounded diagnostics only after they have classified them.
            raise DotError(f"command failed ({result.returncode}): {args[0]}")
        return result

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> int:
        if not args:
            raise DotError("cannot run an empty command")
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        process = subprocess.Popen(  # noqa: S603 - argv is always a sequence, never a shell string. # nosemgrep: dangerous-subprocess-use-audit
            list(args),
            cwd=cwd,
            env=command_env,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            process_group=0 if os.name == "posix" else None,
        )
        try:
            with _foreground_terminal(process, stdin) as terminal:
                code = _wait_interactive(process, terminal)
                if code == -signal.SIGINT:
                    raise KeyboardInterrupt
                return code
        except BaseException:
            _terminate(process)
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
