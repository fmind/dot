"""Subprocess execution for CLI integrations: timeouts, cancellation, and process-group cleanup."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any
from urllib.parse import urlsplit

from fmind_dot.errors import CommandTimeoutError, DotError

_TERMINATION_GRACE_SECONDS = 2.0
_CREDENTIAL_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
_PREFIXED_TOKEN = re.compile(
    r"(?:\b(?:gh[opsur]_|github_pat_|glpat-|sk-|xai-|pypi-|hf_|npm_)[A-Za-z0-9_+/=-]{20,}"
    r"|\bxox[abprs]-[A-Za-z0-9_+/=-]{10,}|\bAIza[A-Za-z0-9_+/=-]{35,}|\bya29\.[A-Za-z0-9._-]{20,}"
    r"|(?<![A-Za-z0-9])1//0[A-Za-z0-9_+/=-]{20,}|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)"
)
_OPAQUE_TOKEN = re.compile(rf"{_PREFIXED_TOKEN.pattern}|(?<![A-Za-z0-9_+/=-])[A-Za-z0-9_+/=-]{{32,}}")
_PATH = re.compile(r"(?<![^\s'\"(=])[~/][^\s'\"]*")
_TOKEN_SEGMENT = re.compile(
    r"(?<![^/])(?=[A-Za-z0-9_+=-]*[A-Z])(?=[A-Za-z0-9_+=-]*[a-z])(?=[A-Za-z0-9_+=-]*[0-9])"
    r"[A-Za-z0-9_+=-]{20,}(?=/|[:.,;)]*$)"
)


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class BytesResult:
    stdout: bytes
    stderr: bytes
    returncode: int


def _redact(text: str) -> str:
    redacted, position = [], 0
    for path in _PATH.finditer(text):
        redacted += [
            _OPAQUE_TOKEN.sub("<redacted>", text[position : path.start()]),
            _TOKEN_SEGMENT.sub("<redacted>", _PREFIXED_TOKEN.sub("<redacted>", path.group())),
        ]
        position = path.end()
    return "".join([*redacted, _OPAQUE_TOKEN.sub("<redacted>", text[position:])])


def diagnostic_line(text: str, limit: int = 160) -> str:
    """Return the first non-empty output line without credentials, control characters, or excess length."""
    line = "".join(c for c in next((i.strip() for i in text.splitlines() if i.strip()), "") if c.isprintable())
    redacted = _redact(_CREDENTIAL_URL.sub(r"\1<redacted>@", line))
    return redacted if len(redacted) <= limit else redacted[: limit - 1].rstrip() + "…"


def _signal(process: subprocess.Popen[Any], signum: signal.Signals, *, group: bool = True) -> None:
    if group:
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass
        except PermissionError:
            return
        else:
            return
    with suppress(ProcessLookupError, PermissionError):
        process.send_signal(signum)


def terminate_process(process: subprocess.Popen[Any], *, group: bool = True, close_streams: bool = True) -> None:
    """Terminate a process (or its process group) with SIGTERM grace before SIGKILL and reap it."""
    timed_out = False
    group_alive = group
    deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
    try:
        if process.returncode is None or group:
            _signal(process, signal.SIGTERM, group=group)
        if process.returncode is None:
            try:
                process.wait(timeout=_TERMINATION_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
        if group and not timed_out:
            # Leader may exit on SIGTERM while children in its PGID are still running; poll PGID until grace expires.
            while True:
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError, PermissionError:
                    group_alive = False
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.05, remaining))
    finally:
        if timed_out or process.returncode is None or (group and group_alive):
            _signal(process, signal.SIGKILL, group=group)
        if close_streams:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    with suppress(OSError):
                        stream.close()
        if process.returncode is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError, PermissionError):
                    process.kill()


_terminate = terminate_process


def _interrupt_on_sigterm(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


@contextmanager
def sigterm_as_keyboard_interrupt() -> Generator[None]:
    """Translate SIGTERM into KeyboardInterrupt on the main thread so cleanup runs cleanly."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.signal(signal.SIGTERM, _interrupt_on_sigterm)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@contextmanager
def deferred_launch_interrupts() -> Generator[None]:
    """Defer SIGINT/SIGTERM while launching and recording a child process so cleanup cannot be skipped."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    pending: list[int] = []
    try:
        with ExitStack() as restore:
            for sig in (signal.SIGINT, signal.SIGTERM):
                if callable(prev := signal.getsignal(sig)):
                    restore.callback(signal.signal, sig, prev)
                    signal.signal(sig, lambda s, _f: pending.append(s))
            yield
    finally:
        for sig in pending:
            signal.raise_signal(sig)


_deferred_launch_interrupts = deferred_launch_interrupts


@contextmanager
def _deferred_interrupts() -> Generator[None]:
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    prev = signal.signal(signal.SIGINT, lambda _s, _f: None)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, prev)


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_URL_TRAILING_PUNCT = ".,;:!?"


def _is_safe_https_url(url: str) -> bool:
    if any(ch.isspace() or ord(ch) <= 0x1F or ord(ch) == 0x7F for ch in url):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None


def _open_browser(url: str) -> None:
    if not _is_safe_https_url(url) or os.environ.get("SSH_TTY") or os.environ.get("SSH_CONNECTION"):
        return
    if sys.platform == "darwin":
        opener = "/usr/bin/open"
        if not Path(opener).exists():
            return
    else:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return
        opener = shutil.which("xdg-open")
        if not opener:
            return
    with suppress(OSError):
        subprocess.Popen(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            [opener, url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def _forward_stderr(stream: IO[str], target: IO[str], open_url: re.Pattern[str], *, open_browser: bool) -> None:
    opened = False
    with stream:
        for line in stream:
            target.write(line)
            target.flush()
            if not open_browser or opened:
                continue
            if match := open_url.search(_ANSI_ESCAPE_RE.sub("", line)):
                opened = True
                _open_browser(match.group(0).rstrip(_URL_TRAILING_PUNCT))


class Runner:
    """Run external tools with timeout and process-group cleanup."""

    requires_tty: bool = True

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._process_lock = threading.Lock()
        self._process_done = threading.Condition(self._process_lock)
        self._processes: set[subprocess.Popen[Any]] = set()

    def cancel(self) -> None:
        self._cancelled.set()
        with self._process_done:
            processes = [proc for proc in self._processes if proc.returncode is None]
        alive = processes
        try:
            for proc in processes:
                _signal(proc, signal.SIGTERM)
            deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
            with self._process_done:
                while True:
                    alive = [proc for proc in processes if proc in self._processes and proc.returncode is None]
                    remaining = deadline - time.monotonic()
                    if not alive or remaining <= 0:
                        break
                    self._process_done.wait(timeout=remaining)
        finally:
            with self._process_done:
                remaining_alive = [proc for proc in alive if proc in self._processes and proc.returncode is None]
            for proc in remaining_alive:
                _signal(proc, signal.SIGKILL)

    def which(self, command: str) -> Path | None:
        return Path(resolved) if (resolved := shutil.which(command)) else None

    def _run_raw(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_data: str | bytes | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        binary: bool = False,
    ) -> tuple[Any, Any, int]:
        if not args:
            raise DotError("cannot run an empty command")
        if self._cancelled.is_set():
            raise DotError("operation cancelled")
        process: subprocess.Popen[Any] | None = None
        try:
            with _deferred_launch_interrupts():
                kwargs: dict[str, Any] = {} if binary else {"encoding": "utf-8", "errors": "replace"}
                process = subprocess.Popen(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
                    list(args),
                    cwd=cwd,
                    env={**os.environ, **env} if env else None,
                    stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                    **kwargs,
                )
                with self._process_lock:
                    self._processes.add(process)
            if self._cancelled.is_set():
                raise DotError("operation cancelled")
            stdout, stderr = process.communicate(input_data, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            if process is not None:
                _terminate(process)
            raise CommandTimeoutError(f"command timed out: {args[0]}") from error
        except BaseException:
            if process is not None:
                _terminate(process)
            raise
        finally:
            if process is not None:
                with self._process_done:
                    self._processes.discard(process)
                    self._process_done.notify_all()
        return stdout, stderr, process.returncode

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
        stdout, stderr, returncode = self._run_raw(
            args, cwd=cwd, input_data=input_text, env=env, timeout=timeout, binary=False
        )
        if check and returncode != 0:
            raise DotError(f"command failed ({returncode}): {args[0]}")
        return CommandResult(stdout=stdout, stderr=stderr, returncode=returncode)

    def run_bytes(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_bytes: bytes | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> BytesResult:
        stdout, stderr, returncode = self._run_raw(args, cwd=cwd, input_data=input_bytes, timeout=timeout, binary=True)
        if check and returncode != 0:
            raise DotError(f"command failed ({returncode}): {args[0]}")
        return BytesResult(stdout=stdout, stderr=stderr, returncode=returncode)

    def stream_stdout[T](
        self,
        args: Sequence[str],
        handler: Callable[[IO[bytes]], T],
        *,
        cwd: Path | None = None,
        input_bytes: bytes | None = None,
        timeout: float | None = None,
    ) -> tuple[T, int, bytes]:
        """Run a command with an unlinked temp stdin file and stream raw stdout through ``handler``."""
        if not args:
            raise DotError("cannot run an empty command")
        if self._cancelled.is_set():
            raise DotError("command cancelled")
        done_lock = threading.Lock()
        done = threading.Event()
        timed_out = False
        failed = False
        process: subprocess.Popen[bytes] | None = None
        timer: threading.Timer | None = None
        stderr_chunks: list[bytes] = []
        stderr_thread: threading.Thread | None = None
        deadline = time.monotonic() + timeout if timeout is not None else None
        with ExitStack() as stack:
            stdin_handle: IO[bytes] | int = subprocess.DEVNULL
            if input_bytes is not None:
                tmp = stack.enter_context(tempfile.TemporaryFile())
                tmp.write(input_bytes)
                tmp.seek(0)
                stdin_handle = tmp
            try:
                with _deferred_launch_interrupts():
                    process = subprocess.Popen(  # noqa: S603
                        list(args),
                        cwd=cwd,
                        stdin=stdin_handle,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )
                    with self._process_done:
                        cancelled = self._cancelled.is_set()
                        if not cancelled:
                            self._processes.add(process)
                if cancelled:
                    raise DotError("command cancelled")
                if process.stdout is None or process.stderr is None:
                    raise DotError(f"pipe unavailable: {args[0]}")

                def _drain_stderr(stream: IO[bytes]) -> None:
                    kept = 0
                    with suppress(OSError, ValueError):
                        while chunk := stream.read(8192):
                            if kept < 4096:
                                piece = chunk[: 4096 - kept]
                                stderr_chunks.append(piece)
                                kept += len(piece)

                stderr_thread = threading.Thread(target=_drain_stderr, args=(process.stderr,), daemon=True)
                stderr_thread.start()

                if timeout is not None:

                    def _on_timeout() -> None:
                        nonlocal timed_out
                        with done_lock:
                            if done.is_set() or (process is not None and process.returncode is not None):
                                return
                            timed_out = True
                            if process is not None:
                                _signal(process, signal.SIGTERM)
                        if process is not None and not done.wait(_TERMINATION_GRACE_SECONDS):
                            with done_lock:
                                if not done.is_set():
                                    _signal(process, signal.SIGKILL)

                    timer = threading.Timer(timeout, _on_timeout)
                    timer.daemon = True
                    timer.start()

                value = handler(process.stdout)
                # Close stdout immediately so early-returning handlers signal EPIPE instead of deadlocking.
                with suppress(OSError):
                    process.stdout.close()
                remaining = max(0.0, deadline - time.monotonic()) if deadline is not None else None
                process.wait(timeout=remaining)
                with done_lock:
                    done.set()
                if timer is not None:
                    timer.cancel()
                stderr_thread.join(timeout=2.0)
            except subprocess.TimeoutExpired as error:
                failed = True
                raise CommandTimeoutError(f"command timed out after {timeout:g}s: {args[0]}") from error
            except KeyboardInterrupt:
                failed = True
                raise
            except Exception as error:
                failed = True
                with done_lock:
                    done.set()
                    did_timeout = timed_out
                if did_timeout:
                    raise CommandTimeoutError(f"command timed out after {timeout:g}s: {args[0]}") from error
                raise
            finally:
                with done_lock:
                    done.set()
                    did_timeout = timed_out
                if timer is not None:
                    timer.cancel()
                if process is not None:
                    needs_cleanup = (
                        process.returncode is None
                        or failed
                        or did_timeout
                        or (stderr_thread is not None and stderr_thread.is_alive())
                    )
                    if needs_cleanup:
                        _terminate(process, close_streams=False)
                    if process.stdout is not None:
                        with suppress(OSError):
                            process.stdout.close()
                if stderr_thread is not None:
                    stderr_thread.join(timeout=2.0)
                if (
                    process is not None
                    and process.stderr is not None
                    and (stderr_thread is None or not stderr_thread.is_alive())
                ):
                    with suppress(OSError):
                        process.stderr.close()
                if process is not None:
                    with self._process_done:
                        self._processes.discard(process)
                        self._process_done.notify_all()
            if did_timeout:
                raise CommandTimeoutError(f"command timed out after {timeout:g}s: {args[0]}")
            return value, process.returncode, b"".join(stderr_chunks)

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        open_url: re.Pattern[str] | None = None,
    ) -> int:
        if not args:
            raise DotError("cannot run an empty command")
        detached = True
        for stream, default in ((stdin, sys.stdin), (stdout, sys.stdout), (stderr, sys.stderr)):
            with suppress(AttributeError, OSError, ValueError):
                if (stream if stream is not None else default).isatty():
                    detached = False
                    break
        err_target = stderr if stderr is not None else sys.stderr
        for stream in (stdout if stdout is not None else sys.stdout, err_target):
            with suppress(AttributeError, OSError, ValueError):
                stream.flush()
        with nullcontext() if detached else _deferred_interrupts():
            process: subprocess.Popen[str] | None = None
            try:
                with _deferred_launch_interrupts():
                    process = subprocess.Popen(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
                        list(args),
                        cwd=cwd,
                        env={**os.environ, **env} if env else None,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=subprocess.PIPE if open_url is not None else stderr,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        process_group=0 if detached else None,
                    )
                if open_url is not None and process.stderr is not None:
                    _forward_stderr(process.stderr, err_target, open_url, open_browser=not detached)
                code = process.wait()
            except BaseException:
                if process is not None:
                    _terminate(process, group=detached)
                raise
            if code == -signal.SIGINT:
                raise KeyboardInterrupt
            return code


def run_parallel[T, R](runner: Runner, function: Callable[[T], R], items: Sequence[T], workers: int) -> list[R]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    executor = ThreadPoolExecutor(max_workers=min(workers, len(items))) if len(items) > 1 else None
    try:
        return list(executor.map(function, items)) if executor else ([function(items[0])] if items else [])
    except BaseException as error:
        if not isinstance(error, Exception):
            runner.cancel()
        raise
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
