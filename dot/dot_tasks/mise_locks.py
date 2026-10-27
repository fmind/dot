"""Capture the global mise lock and its referenced native dependency files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path

_GRAPH_FILES = {"uv": ("pyproject.toml", "uv.lock"), "aube": ("package.json", "aube-lock.yaml")}
# Revision 3 (mise 2026.9.16) also pins forge repository IDs.
LOCK_REVISION = 3


def _bundle_path(root: Path, relative: Path) -> Path:
    if any((root / parent).is_symlink() for parent in (relative, *relative.parents)):
        raise ValueError(f"Lock bundle paths must not use symlinks: {relative}")
    return root / relative


def bundle(lock: Path, *, verify: bool = True) -> dict[Path, bytes]:
    """Read a lock bundle; allow damaged graphs only when repairing a destination."""
    content = _bundle_path(lock.parent, Path(lock.name)).read_bytes()
    document = tomllib.loads(content.decode())
    if document.get("lockfile_version") != LOCK_REVISION:
        raise ValueError(f"Unsupported mise lock format; expected revision {LOCK_REVISION}")
    files = {Path(lock.name): content}
    tools = document.get("tools")
    if not isinstance(tools, dict):
        raise ValueError("mise lock must contain a tools table")
    for entries in tools.values():
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            raise ValueError("mise lock tools must contain arrays of version tables")
        for entry in entries:
            for backend, names in _GRAPH_FILES.items():
                if backend not in entry:
                    continue
                graph = entry[backend]
                if not isinstance(graph, dict) or not all(
                    isinstance(graph.get(key), str) for key in ("path", "digest")
                ):
                    raise ValueError("Dependency references must contain string path and digest fields")
                relative = Path(graph["path"])
                if (
                    relative.is_absolute()
                    or len(relative.parts) < 2
                    or relative.parts[0] != "locks"
                    or ".." in relative.parts
                ):
                    raise ValueError(f"Dependency path must remain under locks/: {relative}")
                for name in names:
                    path = relative / name
                    target = _bundle_path(lock.parent, path)
                    if verify or target.exists():
                        files[path] = target.read_bytes()
                if not verify:
                    continue
                digest = hashlib.sha256(files[relative / names[1]].replace(b"\r\n", b"\n")).hexdigest()
                if graph["digest"] != f"sha256:{digest}":
                    raise ValueError(f"Dependency digest mismatch: {relative}; run mise lock --global")
    return files


def capture(source: Path, destination: Path) -> None:
    """Copy referenced files, write the lock last, then retire old references.

    The destination is tracked by Git, which restores an interrupted copy.
    """
    incoming = bundle(source)
    previous = bundle(destination, verify=False) if destination.exists() else {}
    lock = Path(source.name)
    # Validate every incoming destination before writing even an earlier safe graph.
    targets = {
        relative: _bundle_path(destination.parent, Path(destination.name) if relative == lock else relative)
        for relative in incoming
    }
    for relative in sorted(incoming, key=lambda path: path == lock):
        target = targets[relative]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(incoming[relative])
    for relative in previous.keys() - incoming.keys():
        target = destination.parent / relative
        target.unlink()
        parent = target.parent
        while parent != destination.parent and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def retire(lock: Path) -> list[Path]:
    """Remove deployed graph directories that the lock no longer references.

    chezmoi never deletes a target whose source was removed, so each upgrade otherwise
    leaves the previous versions' graphs behind. Only locks/** directories holding
    nothing but generated graph files are removed; anything else is kept.
    """
    referenced = {path.parent for path in bundle(lock, verify=False) if path.parts[:1] == ("locks",)}
    generated = {name for names in _GRAPH_FILES.values() for name in names}
    locks = lock.parent / "locks"
    if locks.is_symlink() or not locks.is_dir():
        return []
    retired = []
    for directory in sorted(locks.rglob("*")):
        relative = directory.relative_to(lock.parent)
        if (
            relative in referenced
            or any((lock.parent / parent).is_symlink() for parent in (relative, *relative.parents))
            or not directory.is_dir()
        ):
            continue
        entries = list(directory.iterdir())
        if not entries or any(
            entry.is_symlink() or not entry.is_file() or entry.name not in generated for entry in entries
        ):
            continue
        for entry in entries:
            entry.unlink()
        directory.rmdir()
        parent = directory.parent
        while parent != locks and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
        retired.append(relative)
    return retired


def _valid_install(candidate: Path, version: str, backend: str, allowed: set[tuple[str, str, str]]) -> bool:
    if backend == "uv":
        metadata = candidate / ".mise-uv"
        if metadata.is_symlink() or not metadata.is_dir():
            return False
        lockfile = metadata / "uv.lock"
        python_json = metadata / "python.json"
        if python_json.is_symlink() or not python_json.is_file():
            return False
        try:
            interpreter = json.loads(python_json.read_text(encoding="utf-8"))
        except OSError, UnicodeDecodeError, ValueError:
            return False
        if (
            not isinstance(interpreter, list)
            or not interpreter
            or not isinstance(interpreter[0], str)
            or not Path(interpreter[0]).exists()
        ):
            return False
    else:
        lockfile = candidate / "aube-lock.yaml"
    if lockfile.is_symlink() or not lockfile.is_file():
        return False
    digest = hashlib.sha256(lockfile.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return (version, backend, f"sha256:{digest}") in allowed


def retire_installs(lock: Path, installs: Path) -> list[Path]:
    """Remove hash-suffixed uv/aube tool installs whose graph or interpreter was retired.

    mise names revision-3 pipx and npm installs `<version>~<backend>~<hash>` and strips the
    suffix during `mise prune`, so superseded dependency graphs accumulate under installs/.
    """
    bundle(lock, verify=False)
    if installs.is_symlink() or not installs.is_dir():
        return []
    document = tomllib.loads(_bundle_path(lock.parent, Path(lock.name)).read_text(encoding="utf-8"))
    active: dict[str, set[tuple[str, str, str]]] = {}
    for entries in document["tools"].values():
        for entry in entries:
            version = entry.get("version")
            if not isinstance(version, str):
                continue
            for backend in _GRAPH_FILES:
                if backend in entry:
                    slug = Path(entry[backend]["path"]).parts[1]
                    active.setdefault(slug, set()).add((version, backend, entry[backend]["digest"]))
    retired: list[Path] = []
    for slug, allowed in sorted(active.items()):
        tool_dir = installs / slug
        if tool_dir.is_symlink() or not tool_dir.is_dir():
            continue
        removed = False
        for candidate in sorted(tool_dir.iterdir()):
            if candidate.is_symlink() or not candidate.is_dir():
                continue
            parts = candidate.name.split("~")
            if len(parts) != 3 or parts[1] not in _GRAPH_FILES or not parts[0] or not parts[2]:
                continue
            # Other versions belong to project pins; `mise prune` owns them.
            if not any(version == parts[0] for version, _, _ in allowed):
                continue
            if _valid_install(candidate, parts[0], parts[1], allowed):
                continue
            shutil.rmtree(candidate)
            retired.append(candidate)
            removed = True
        if removed:
            global_link = tool_dir / "global"
            target = global_link.readlink() if global_link.is_symlink() and global_link.exists() else None
            for entry in sorted(tool_dir.iterdir()):
                if entry.is_symlink() and not entry.exists():
                    entry.unlink()
                    if target is not None:
                        entry.symlink_to(target)
    return retired


def main() -> int:
    """Retire stale graphs and hash-suffixed installs next to a deployed global lock."""
    parser = argparse.ArgumentParser(
        description="Remove deployed dependency graphs and hash-suffixed installs that mise.lock no longer references."
    )
    parser.add_argument("lock", type=Path, help="deployed global mise.lock")
    arguments = parser.parse_args()
    installs = Path(os.environ.get("MISE_DATA_DIR", Path.home() / ".local/share/mise")) / "installs"
    try:
        retired = [
            *(arguments.lock.parent / relative for relative in retire(arguments.lock)),
            *retire_installs(arguments.lock, installs),
        ]
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Cannot retire mise dependency graphs: {error}\n")
        return 1
    for path in retired:
        sys.stdout.write(f"Retired {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
