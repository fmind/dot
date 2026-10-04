"""Pin fmind/theme externals to one upstream commit with per-file checksums.

Several theme files execute (Fish, Neovim Lua, ptpython, Git includes), so apply
must never fetch a moving branch; `mise run upgrade` advances the pin instead.
Configs that cannot include a second file carry a copy of the upstream theme block;
the pin only advances while every copy matches the target revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

REPOSITORY = "https://github.com/fmind/theme"
RAW = "https://raw.githubusercontent.com/fmind/theme/{revision}/themes/{path}"
MAX_BYTES = 1_000_000
BASE = re.compile(r'(\{\{ \$base := "https://raw\.githubusercontent\.com/fmind/theme/)([0-9a-f]{40})(/themes" \}\})')
ENTRY = re.compile(r'(    url = "\{\{ \$base \}\}/(?P<path>[^"]+)"\n    checksum\.sha256 = ")[0-9a-f]{64}(")')

ROOT = Path(__file__).resolve().parents[2]
# Source file -> (upstream theme file, key paths copied from it). The upstream suffix
# selects the parser for both sides; ripgreprc keeps only its --colors flags.
COPIED: dict[str, tuple[str, tuple[tuple[str, ...], ...]]] = {
    "dot_config/bottom/bottom.toml": ("bottom/fmind.toml", (("styles",),)),
    "dot_config/fastfetch/config.jsonc": ("fastfetch/fmind.json", (("display", "color"),)),
    "dot_config/gh-dash/config.yml.tmpl": ("gh-dash/fmind.yml", (("theme",),)),
    "dot_config/lazydocker/config.yml": ("lazydocker/fmind.yml", (("gui", "theme"),)),
    "dot_config/ripgrep/config.tmpl": ("ripgrep/fmind.ripgreprc", (("colors",),)),
    "dot_config/starship.toml": ("starship/fmind.toml", (("palette",), ("palettes",))),
    "dot_gitconfig.tmpl": (
        "git/fmind.gitconfig",
        tuple((f'color "{section}"',) for section in ("diff", "status", "branch", "decorate")),
    ),
}

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


def parse(text: str, upstream: str) -> dict[str, Any]:
    """Parse a theme or native config in the upstream file's format."""
    suffix = Path(upstream).suffix
    if suffix == ".toml":
        return tomllib.loads(text)
    if suffix in {".yml", ".yaml"}:
        return yaml.safe_load(text) or {}
    if suffix == ".json":
        # Native configs may be JSONC; only whole-line comments occur in these files.
        return json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))
    if suffix == ".gitconfig":
        # Compare values without quotes: upstream leaves hex colors bare, Git needs them quoted.
        sections: dict[str, dict[str, str]] = {}
        section: dict[str, str] | None = None
        for line in map(str.strip, text.splitlines()):
            if line.startswith("["):
                section = sections.setdefault(line.strip("[]"), {})
            elif section is not None and "=" in line and not line.startswith(("#", ";")):
                key, value = (part.strip() for part in line.split("=", 1))
                section[key] = value.strip('"')
        return sections
    if suffix == ".ripgreprc":
        return {"colors": [line for line in text.splitlines() if line.startswith("--colors=")]}
    raise ValueError(f"unsupported theme format: {upstream}")


def render(path: Path) -> str:
    """Return a source file as chezmoi deploys it."""
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".tmpl":
        return text
    result = subprocess.run(  # nosemgrep: dangerous-subprocess-use-audit
        ["chezmoi", "execute-template"],  # noqa: S607
        input=text,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def dig(config: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the value at a key path, or None when any key is missing."""
    value: Any = config
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def stale_copies(revision: str, download: Fetch, read: Callable[[Path], str] = render) -> list[str]:
    """List copied theme blocks that differ from the upstream files at a revision."""
    stale = []
    for source, (upstream, paths) in COPIED.items():
        theme = parse(download(RAW.format(revision=revision, path=upstream)).decode(), upstream)
        local = parse(read(ROOT / source), upstream)
        for keys in paths:
            expected = dig(theme, keys)
            if expected is None or dig(local, keys) != expected:
                stale.append(f"{source}: {'.'.join(keys)} differs from themes/{upstream}")
    return stale


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
        if stale := stale_copies(revision, fetch):
            sys.stderr.write("".join(f"{line}\n" for line in stale))
            sys.stderr.write(f"Copy the upstream blocks from {revision}, then rerun.\n")
            return 1
        if updated != template:
            path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError, tomllib.TOMLDecodeError, yaml.YAMLError) as error:
        sys.stderr.write(f"Cannot pin fmind/theme: {error}\n")
        return 1
    sys.stdout.write(f"fmind/theme pinned to {revision}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
