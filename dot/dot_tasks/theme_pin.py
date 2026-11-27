"""Pin fmind/theme externals to one upstream commit with per-file checksums."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.client
import random
import re
import ssl
import subprocess
import sys
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from typing import Any

from dot_tasks import ROOT
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import sigterm_as_keyboard_interrupt

REPOSITORY = "https://github.com/fmind/theme"
RAW = "https://raw.githubusercontent.com/fmind/theme/{revision}/{path}"
MAX_BYTES = 1_000_000
BASE = re.compile(r'(\{\{ \$base := "https://raw\.githubusercontent\.com/fmind/theme/)([0-9a-f]{40})(" \}\})')
ENTRY = re.compile(r'(    url = "\{\{ \$base \}\}/(?P<path>[^"]+)"\n    checksum\.sha256 = ")[0-9a-f]{64}(")')

# Source file -> (upstream theme file, key paths copied from it); suffix selects parser.
COPIED: dict[str, tuple[str, tuple[tuple[str, ...], ...]]] = {
    "dot_config/ripgrep/config.tmpl": ("themes/ripgrep/fmind.ripgreprc", (("colors",),)),
    "dot_config/starship.toml": ("themes/starship/fmind.toml", (("palette",), ("palettes",))),
}

# Byte-for-byte raw copies synchronized with upstream files in COPIED's revision.
RAW_COPIES: dict[str, str] = {
    "skills/draft/references/typst-deck/templates/fmind.typ": "themes/typst/fmind.typ",
}

Fetch = Callable[[str], bytes]
_PIN_ERRORS = (
    OSError,
    http.client.HTTPException,
    ValueError,
    subprocess.SubprocessError,
    tomllib.TOMLDecodeError,
)


def resolve_head(branch: str = "main") -> str:
    """Return the upstream branch commit without needing GitHub API credentials."""
    cmd = ["git", "ls-remote", REPOSITORY, f"refs/heads/{branch}"]
    revision = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout.split("\t", 1)[0]  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"cannot resolve {REPOSITORY} {branch}")
    return revision


_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_FETCH_ATTEMPTS = 3


def _retry_delay(attempt: int) -> float:
    return 0.25 * (2**attempt) + random.uniform(0.0, 0.15)  # noqa: S311


def _validate_https(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"theme URL must use https: {url}")
    return parsed


def _read_bounded_response(response: Any, url: str) -> bytes:
    content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError(f"theme file exceeds {MAX_BYTES} bytes: {url}")
    remaining = getattr(response, "length", None)
    if isinstance(remaining, int) and remaining > 0:
        raise http.client.IncompleteRead(content, remaining)
    return content


def fetch(url: str) -> bytes:
    _validate_https(url)
    for attempt in range(_FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - validated https URL
                return _read_bounded_response(response, url)
        except urllib.error.HTTPError as error:
            if error.code not in _RETRY_STATUSES or attempt + 1 >= _FETCH_ATTEMPTS:
                raise
            with suppress(OSError):
                error.close()
        except http.client.HTTPException, OSError:
            if attempt + 1 >= _FETCH_ATTEMPTS:
                raise
        time.sleep(_retry_delay(attempt))
    raise AssertionError("unreachable")


class _NonRetryableHTTPError(http.client.HTTPException):
    """Non-retryable HTTP status error from a keep-alive connection."""


class _KeepAliveFetcher:
    """Thread-local HTTPS keep-alive pool for fetching pinned theme files from one host."""

    def __init__(self, cancel: threading.Event | None = None) -> None:
        self._local = threading.local()
        self._lock = threading.Lock()
        self._connections: list[http.client.HTTPSConnection] = []
        self._ssl_context = ssl.create_default_context()
        self._cancel = cancel or threading.Event()

    def _connection(self, host: str, port: int | None) -> http.client.HTTPSConnection:
        conns: dict[tuple[str, int | None], http.client.HTTPSConnection] = getattr(self._local, "conns", None) or {}
        self._local.conns = conns
        key = (host, port)
        if key not in conns:
            conn = http.client.HTTPSConnection(host, port=port, timeout=30, context=self._ssl_context)
            conns[key] = conn
            with self._lock:
                self._connections.append(conn)
        return conns[key]

    def _reset(self, host: str, port: int | None) -> None:
        conns: dict[tuple[str, int | None], http.client.HTTPSConnection] = getattr(self._local, "conns", None) or {}
        if (conn := conns.pop((host, port), None)) is not None:
            with suppress(OSError):
                conn.close()

    def _sleep(self, attempt: int) -> None:
        if self._cancel.wait(_retry_delay(attempt)):
            raise KeyboardInterrupt

    def __call__(self, url: str) -> bytes:
        parsed = _validate_https(url)
        host = parsed.hostname or ""
        port = parsed.port
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        redirect = False
        for attempt in range(_FETCH_ATTEMPTS):
            if self._cancel.is_set():
                raise KeyboardInterrupt
            try:
                conn = self._connection(host, port)
                conn.request("GET", target, headers={"Connection": "keep-alive"})
                resp = conn.getresponse()
                if resp.status in {301, 302, 307, 308}:
                    self._reset(host, port)
                    redirect = True
                    break
                if resp.status in _RETRY_STATUSES:
                    status = resp.status
                    self._reset(host, port)
                    if attempt + 1 < _FETCH_ATTEMPTS:
                        self._sleep(attempt)
                        continue
                    raise _NonRetryableHTTPError(f"HTTP {status} for {url}")
                if resp.status != 200:
                    status = resp.status
                    self._reset(host, port)
                    raise _NonRetryableHTTPError(f"HTTP {status} for {url}")
                try:
                    return _read_bounded_response(resp, url)
                except ValueError:
                    self._reset(host, port)
                    raise
            except _NonRetryableHTTPError:
                raise
            except http.client.HTTPException, OSError:
                self._reset(host, port)
                if attempt + 1 >= _FETCH_ATTEMPTS:
                    raise
                self._sleep(attempt)
        if redirect:
            return fetch(url)
        raise AssertionError("unreachable")

    def close(self) -> None:
        with self._lock:
            for conn in self._connections:
                with suppress(OSError):
                    conn.close()
            self._connections.clear()


def prefetch(revision: str, template: str, download: Fetch = fetch) -> Fetch:
    """Download every distinct upstream theme file for a revision concurrently."""
    if not (paths := [m.group("path") for m in ENTRY.finditer(template)]):
        return download
    raw = [
        RAW.format(revision=revision, path=p) for p in [*paths, *(u for u, _ in COPIED.values()), *RAW_COPIES.values()]
    ]
    urls = list(dict.fromkeys(raw))
    cancel = threading.Event()
    pool = _KeepAliveFetcher(cancel) if download is fetch and not urllib.request.getproxies() else None
    worker = pool if pool is not None else download
    executor = ThreadPoolExecutor(max_workers=min(8, len(urls)))
    drained = False
    try:
        cache = dict(zip(urls, executor.map(worker, urls), strict=True))
    except BaseException:
        cancel.set()
        raise
    finally:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
            drained = True
        finally:
            if pool is not None and drained:
                pool.close()
    return lambda url: cache[url] if url in cache else download(url)


def pin(template: str, revision: str, download: Fetch) -> str:
    """Rewrite the theme revision and every theme checksum for that revision."""
    if not BASE.search(template):
        raise ValueError("theme base URL with a pinned revision not found")
    if not ENTRY.search(template):
        raise ValueError("no checksummed theme entries found")
    pinned = BASE.sub(lambda m: m.group(1) + revision + m.group(3), template)

    def digest(m: re.Match[str]) -> str:
        return hashlib.sha256(download(RAW.format(revision=revision, path=m.group("path")))).hexdigest()

    return ENTRY.sub(lambda m: m.group(1) + digest(m) + m.group(3), pinned)


def parse(text: str, upstream: str) -> dict[str, Any]:
    """Parse a theme or native config in the upstream file's format."""
    match Path(upstream).suffix:
        case ".toml":
            return tomllib.loads(text)
        case ".ripgreprc":
            return {"colors": [line for line in text.splitlines() if line.startswith("--colors=")]}
    raise ValueError(f"unsupported theme format: {upstream}")


def render(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".tmpl":
        return text
    cmd = ["chezmoi", "--source", ".", "execute-template"]
    return subprocess.run(cmd, cwd=ROOT, input=text, check=True, capture_output=True, text=True, timeout=30).stdout  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit


def dig(config: dict[str, Any], keys: tuple[str, ...]) -> Any:
    return functools.reduce(lambda cur, k: cur.get(k) if isinstance(cur, dict) else None, keys, config)


def stale_copies(revision: str, download: Fetch, read: Callable[[Path], str] = render) -> list[str]:
    """List copied theme blocks that differ from the upstream files at a revision."""
    stale: list[str] = []
    for source, (upstream, paths) in COPIED.items():
        theme = parse(download(RAW.format(revision=revision, path=upstream)).decode(), upstream)
        local = parse(read(ROOT / source), upstream)
        diffs = [k for k in paths if (exp := dig(theme, k)) is None or dig(local, k) != exp]
        stale.extend(f"{source}: {'.'.join(k)} differs from {upstream}" for k in diffs)
    return stale


def stale_raw_copies(revision: str, download: Fetch) -> list[str]:
    """List raw byte-for-byte theme copies that differ from upstream files at a revision."""
    return [
        f"{source}: differs from {upstream}"
        for source, upstream in RAW_COPIES.items()
        if download(RAW.format(revision=revision, path=upstream)) != (ROOT / source).read_bytes()
    ]


def main() -> int:
    """Advance the theme pin to upstream main, or verify a given revision."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("--revision", help="commit SHA to pin instead of upstream main")
    if (rev := parser.parse_args().revision) is not None and not re.fullmatch(r"[0-9a-f]{40}", rev):
        parser.error("expected a full 40-character lowercase commit SHA")
    path = ROOT / ".chezmoiexternal.toml.tmpl"
    with sigterm_as_keyboard_interrupt():
        try:
            revision, template = rev or resolve_head(), path.read_text(encoding="utf-8")
            download = prefetch(revision, template)
            updated = pin(template, revision, download)
            if stale := [*stale_copies(revision, download), *stale_raw_copies(revision, download)]:
                joined = "".join(f"{line}\n" for line in stale)
                sys.stderr.write(f"{joined}Copy the upstream blocks from {revision}, then rerun.\n")
                return 1
            if updated != template:
                write_atomic_file(path, updated.encode("utf-8"), mode=0o644)
        except KeyboardInterrupt:
            return 130
        except _PIN_ERRORS as error:
            sys.stderr.write(f"Cannot pin fmind/theme: {error}\n")
            return 1
    sys.stdout.write(f"fmind/theme pinned to {revision}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
