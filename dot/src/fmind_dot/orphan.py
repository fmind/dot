"""Report targets chezmoi once wrote but no longer manages; never deletes them."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import typer

from fmind_dot.command_group import JsonOption
from fmind_dot.errors import DotError
from fmind_dot.state import State, require_tools, state_from

# chezmoi also records scripts and remove_ markers; only written targets can be orphaned.
_TARGET_TYPES = {"dir", "file", "symlink"}


@dataclass(frozen=True)
class Orphan:
    """A previously deployed target and how it compares with chezmoi's last write."""

    path: str
    type: str
    status: str


def _entry_state(state: State) -> dict[str, Any]:
    result = state.runner.run(["chezmoi", "state", "dump", "--format=json"], timeout=60)
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise DotError(f"chezmoi state dump returned invalid JSON: {error}") from error
    entries = document.get("entryState") if isinstance(document, dict) else None
    if not isinstance(entries, dict):
        raise DotError("chezmoi state dump has no entryState bucket")
    return entries


def _managed(state: State) -> set[str]:
    result = state.runner.run(
        ["chezmoi", "managed", "--include=all", "--path-style=absolute", "--nul-path-separator"], timeout=60
    )
    return {path for path in result.stdout.split("\0") if path}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _status(path: Path, kind: str, recorded: object) -> str | None:
    """Compare the target with chezmoi's recorded write without reading it into output; None if gone."""
    try:
        if kind == "dir":
            if not path.is_dir() or path.is_symlink():
                return "replaced"
            return "not-empty" if any(path.iterdir()) else "empty"
        if kind == "symlink":
            if not path.is_symlink():
                return "replaced"
            current = hashlib.sha256(str(path.readlink()).encode()).hexdigest()
        else:
            if path.is_symlink() or not path.is_file():
                return "replaced"
            current = _sha256(path)
    except FileNotFoundError:
        return None  # Removed while scanning: no longer an orphan.
    except OSError:
        return "unreadable"
    return "unchanged" if current == recorded else "modified"


def find_orphans(state: State) -> list[Orphan]:
    """List existing targets in chezmoi's entry state that the source no longer manages."""
    require_tools(state, [["chezmoi"]])
    entries = _entry_state(state)
    managed = _managed(state)
    orphans = []
    for raw, entry in sorted(entries.items()):
        kind = entry.get("type") if isinstance(entry, dict) else None
        if kind not in _TARGET_TYPES or raw in managed:
            continue
        path = Path(raw)
        if not path.is_absolute() or not os.path.lexists(path):
            continue
        if (status := _status(path, kind, entry.get("contentsSHA256"))) is not None:
            orphans.append(Orphan(raw, kind, status))
    return orphans


def _display(path: str) -> str:
    home = str(Path.home())
    return "~" + path[len(home) :] if path == home or path.startswith(home + os.sep) else path


def run_orphan(state: State, *, as_json: bool = False) -> list[Orphan]:
    orphans = find_orphans(state)
    if as_json:
        state.stdout.write(json.dumps([asdict(orphan) for orphan in orphans], indent=2) + "\n")
        return orphans
    if not orphans:
        state.stdout.write("✓ No orphaned chezmoi targets.\n")
        return orphans
    state.stdout.write(f"{len(orphans)} target(s) chezmoi wrote but no longer manages:\n")
    for orphan in orphans:
        state.stdout.write(f"  {orphan.status:<10} {orphan.type:<8} {_display(orphan.path)}\n")
    state.stdout.write(
        "unchanged: still chezmoi's last write; modified/replaced: changed since, possibly by a new owner.\n"
        "Nothing was deleted. Remove a leftover, or forget a kept path with:\n"
        "  chezmoi state delete --bucket=entryState --key=PATH\n"
    )
    return orphans


def register(app: typer.Typer) -> None:
    @app.command("orphan", help="List files chezmoi deployed but no longer manages (read-only; never deletes)")
    def orphan(context: typer.Context, as_json: JsonOption = False) -> None:
        run_orphan(state_from(context, require_config=False), as_json=as_json)
