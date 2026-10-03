"""Pin fmind/theme externals to one upstream commit with per-file checksums.

Several theme files execute (Fish, Neovim Lua, ptpython, Git includes), so apply
must never fetch a moving branch; `mise run upgrade` advances the pin instead.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

REPOSITORY = "https://github.com/fmind/theme"
RAW = "https://raw.githubusercontent.com/fmind/theme/{revision}/themes/{path}"
MAX_BYTES = 1_000_000
BASE = re.compile(r'(\{\{ \$base := "https://raw\.githubusercontent\.com/fmind/theme/)([0-9a-f]{40})(/themes" \}\})')
ENTRY = re.compile(r'(    url = "\{\{ \$base \}\}/(?P<path>[^"]+)"\n    checksum\.sha256 = ")[0-9a-f]{64}(")')

Fetch = Callable[[str], bytes]


def resolve_head(branch: str = "main") -> str:
    """Return the upstream branch commit without needing GitHub API credentials."""
    result = subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
        ["git", "ls-remote", REPOSITORY, f"refs/heads/{branch}"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    revision = result.stdout.split("\t", 1)[0]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"cannot resolve {REPOSITORY} {branch}")
    return revision


def fetch(url: str) -> bytes:
    """Download one theme file with a size bound."""
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed https URL
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError(f"theme file exceeds {MAX_BYTES} bytes: {url}")
    return content


def pin(template: str, revision: str, download: Fetch) -> str:
    """Rewrite the theme revision and every theme checksum for that revision."""
    if not BASE.search(template):
        raise ValueError("theme base URL with a pinned revision not found")
    entries = list(ENTRY.finditer(template))
    if not entries:
        raise ValueError("no checksummed theme entries found")
    pinned = BASE.sub(lambda match: match.group(1) + revision + match.group(3), template)

    def checksum(match: re.Match[str]) -> str:
        digest = hashlib.sha256(download(RAW.format(revision=revision, path=match.group("path")))).hexdigest()
        return match.group(1) + digest + match.group(3)

    return ENTRY.sub(checksum, pinned)


def main() -> int:
    """Advance the theme pin to upstream main, or verify a given revision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="commit to pin instead of upstream main")
    arguments = parser.parse_args()
    path = Path(__file__).resolve().parents[2] / ".chezmoiexternal.toml.tmpl"
    try:
        revision = arguments.revision or resolve_head()
        template = path.read_text(encoding="utf-8")
        updated = pin(template, revision, fetch)
        if updated != template:
            path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Cannot pin fmind/theme: {error}\n")
        return 1
    sys.stdout.write(f"fmind/theme pinned to {revision}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
