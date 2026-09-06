"""Bounded subprocess execution for CLI integrations."""

from __future__ import annotations

import locale
import os
import selectors
import shutil
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
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


class Runner:
    """Run external tools with timeout and process-group cleanup."""

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
        )
        try:
            return process.wait()
        except BaseException:
            _terminate(process)
            raise
