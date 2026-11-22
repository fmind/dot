"""Pin fmind/theme externals to one upstream commit with per-file checksums."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.client
import re
import subprocess
import sys
import tomllib
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from dot_tasks import ROOT
from fmind_dot.private_files import write_atomic_file

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


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed https URL
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError(f"theme file exceeds {MAX_BYTES} bytes: {url}")
    return content


def prefetch(revision: str, template: str, download: Fetch = fetch) -> Fetch:
    """Download every distinct upstream theme file for a revision concurrently."""
    if not (paths := [m.group("path") for m in ENTRY.finditer(template)]):
        return download
    raw = [
        RAW.format(revision=revision, path=p) for p in [*paths, *(u for u, _ in COPIED.values()), *RAW_COPIES.values()]
    ]
    urls = list(dict.fromkeys(raw))
    with ThreadPoolExecutor(max_workers=min(8, len(urls))) as executor:
        cache = dict(zip(urls, executor.map(download, urls), strict=True))
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
    except _PIN_ERRORS as error:
        sys.stderr.write(f"Cannot pin fmind/theme: {error}\n")
        return 1
    sys.stdout.write(f"fmind/theme pinned to {revision}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
