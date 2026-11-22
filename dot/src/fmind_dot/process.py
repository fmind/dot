"""Subprocess execution for CLI integrations: timeouts, cancellation, and process-group cleanup."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO
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


def _signal(process: subprocess.Popen[str], signum: signal.Signals, *, group: bool = True) -> None:
    if group:
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signum)
            return
    with suppress(ProcessLookupError):
        process.send_signal(signum)


def _terminate(process: subprocess.Popen[str], *, group: bool = True) -> None:
    try:
        _signal(process, signal.SIGTERM, group=group)
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
    finally:
        _signal(process, signal.SIGKILL, group=group)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                with suppress(OSError):
                    stream.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


@contextmanager
def _deferred_launch_interrupts() -> Generator[None]:
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    pending: list[int] = []
    try:
        with ExitStack() as restore:
            for sig in (signal.SIGINT, signal.SIGTERM):
                if callable(prev := signal.getsignal(sig)):
                    signal.signal(sig, lambda s, _f: pending.append(s))
                    restore.callback(signal.signal, sig, prev)
            yield
    finally:
        for sig in pending:
            signal.raise_signal(sig)


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
        self._processes: set[subprocess.Popen[str]] = set()

    def cancel(self) -> None:
        self._cancelled.set()
        with self._process_lock:
            processes = tuple(self._processes)
        for proc in processes:
            _signal(proc, signal.SIGTERM)
        deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < deadline and any(p.poll() is None for p in processes):
            time.sleep(0.05)
        for proc in processes:
            _signal(proc, signal.SIGKILL)

    def which(self, command: str) -> Path | None:
        return Path(resolved) if (resolved := shutil.which(command)) else None

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
        if not args:
            raise DotError("cannot run an empty command")
        if self._cancelled.is_set():
            raise DotError("operation cancelled")
        process: subprocess.Popen[str] | None = None
        try:
            with _deferred_launch_interrupts():
                process = subprocess.Popen(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
                    list(args),
                    cwd=cwd,
                    env={**os.environ, **env} if env else None,
                    stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    errors="replace",
                    start_new_session=True,
                )
                with self._process_lock:
                    self._processes.add(process)
            if self._cancelled.is_set():
                raise DotError("operation cancelled")
            stdout, stderr = process.communicate(input_text, timeout=timeout)
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
                with self._process_lock:
                    self._processes.discard(process)
        if check and process.returncode != 0:
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
