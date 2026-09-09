"""Bounded subprocess execution for CLI integrations."""

from __future__ import annotations

import codecs
import io
import locale
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock
from typing import IO

from fmind_dot.errors import DotError

_TERMINATION_TIMEOUT_SECONDS = 3
_PIPE_WRITE_BYTES = 4096


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
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        if timeout is None:
            raise RuntimeError("subprocess deadline requires a timeout")
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


def _terminate(process: subprocess.Popen[str] | subprocess.Popen[bytes]) -> None:
    """Kill the launched process and stop escaped descendants holding pipes from blocking."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            if process.poll() is None:
                process.kill()
    elif process.poll() is None:
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
        os.tcsetpgrp(terminal, group)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


@contextmanager
def _foreground_terminal(process: subprocess.Popen[str], stream: IO[str] | None) -> Iterator[int | None]:
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
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGCONT)
        yield terminal
    finally:
        if terminal is not None:
            _set_foreground(terminal, os.getpgrp())


def _relay_terminal_stop(process: subprocess.Popen[str], terminal: int | None) -> None:
    if terminal is None or process.poll() is not None:
        return
    stopped = os.waitid(os.P_PID, process.pid, os.WSTOPPED | os.WNOHANG)
    if stopped is not None:
        _set_foreground(terminal, os.getpgrp())
        # Let the shell suspend/resume dot as a job, then return the terminal to
        # its child. SIGSTOP also works when a host inherited ignored SIGTSTP.
        os.kill(os.getpid(), signal.SIGSTOP)
        _set_foreground(terminal, process.pid)
        os.killpg(process.pid, signal.SIGCONT)


def _wait_interactive(
    process: subprocess.Popen[str],
    terminal: int | None,
    output: IO[str],
    on_stdout_line: Callable[[str], None] | None,
) -> int:
    if on_stdout_line is None or process.stdout is None:
        if terminal is None:
            return process.wait()
        while True:
            _relay_terminal_stop(process, terminal)
            try:
                return process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
    # Read chunks so a partial stdout line cannot block cancellation or job
    # control. Preserve the text/universal-newline contract of Popen.readline.
    decoder = io.IncrementalNewlineDecoder(codecs.getincrementaldecoder(locale.getencoding())("replace"), True)
    pending = ""
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map() or process.poll() is None:
            _relay_terminal_stop(process, terminal)
            for key, _events in selector.select(timeout=0.1):
                content = os.read(key.fd, 65536)
                pending += decoder.decode(content, final=not content)
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    output.write(line + "\n")
                    output.flush()
                    on_stdout_line(line + "\n")
                if not content:
                    selector.unregister(key.fileobj)
                    if pending:
                        output.write(pending)
                        output.flush()
                        on_stdout_line(pending)
                        pending = ""
    return process.wait()


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
            for process in self._processes:
                # The communicating worker owns its pipes and reaps the child.
                if os.name == "posix":
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                elif process.poll() is None:
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
        return self._run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)

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
        return self._run(
            args,
            cwd=cwd,
            input_text=input_text,
            env=env,
            timeout=timeout,
            check=check,
            max_output_bytes=max_output_bytes,
        )

    def _run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None,
        input_text: str | None,
        env: Mapping[str, str] | None,
        timeout: float | None,
        check: bool,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        if not args:
            raise DotError("cannot run an empty command")
        if max_output_bytes is not None and max_output_bytes <= 0:
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
            text=max_output_bytes is None,
            start_new_session=os.name == "posix",
        )
        with self._process_lock:
            self._processes.add(process)
            if self._cancelled.is_set():
                _terminate(process)
        try:
            if max_output_bytes is None:
                stdout, stderr = process.communicate(input_text, timeout=timeout)
                result = CommandResult(stdout=stdout, stderr=stderr, returncode=process.returncode)
            else:
                capture = _communicate_bounded(
                    process,
                    input_text.encode(encoding) if input_text is not None else None,
                    timeout,
                    max_output_bytes,
                )
                result = CommandResult(
                    stdout=capture.stdout.decode(encoding, errors="replace"),
                    stderr=capture.stderr.decode(encoding, errors="replace"),
                    returncode=process.returncode,
                    stdout_truncated=capture.stdout_truncated,
                    stderr_truncated=capture.stderr_truncated,
                )
        except subprocess.TimeoutExpired as error:
            _terminate(process)
            raise DotError(f"command timed out: {args[0]}") from error
        except KeyboardInterrupt:
            _terminate(process)
            raise
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
        on_stdout_line: Callable[[str], None] | None = None,
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
            stdout=subprocess.PIPE if on_stdout_line is not None else stdout,
            stderr=stderr,
            process_group=0 if os.name == "posix" else None,
            text=on_stdout_line is not None,
            encoding=locale.getencoding() if on_stdout_line is not None else None,
            errors="replace" if on_stdout_line is not None else None,
        )
        try:
            with _foreground_terminal(process, stdin) as terminal:
                code = _wait_interactive(process, terminal, sys.stdout if stdout is None else stdout, on_stdout_line)
                if code == -signal.SIGINT:
                    raise KeyboardInterrupt
                return code
        except BaseException:
            _terminate(process)
            raise
        finally:
            if process.stdout is not None:
                process.stdout.close()
