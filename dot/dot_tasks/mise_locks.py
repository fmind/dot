"""Capture the global mise lock and its referenced native dependency files."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

_GRAPH_FILES = {"uv": ("pyproject.toml", "uv.lock"), "aube": ("package.json", "aube-lock.yaml")}
# Revision 3 (mise 2026.9.16) also pins forge repository IDs.
LOCK_REVISION = 3


def bundle(lock: Path, *, verify: bool = True) -> dict[Path, bytes]:
    """Read a lock bundle; allow damaged graphs only when repairing a destination."""
    content = lock.read_bytes()
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
                if relative.is_absolute() or relative.parts[:1] != ("locks",) or ".." in relative.parts:
                    raise ValueError(f"Dependency path must remain under locks/: {relative}")
                for name in names:
                    path = relative / name
                    target = lock.parent / path
                    if any((lock.parent / parent).is_symlink() for parent in (path, *path.parents)):
                        raise ValueError(f"Dependency files must not use symlinks: {path}")
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
    for relative in sorted(incoming, key=lambda path: path == lock):
        target = destination if relative == lock else destination.parent / relative
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
    leaves the previous versions' graphs behind. Only locks/<tool>/<version> directories
    holding nothing but generated graph files are removed; anything else is kept.
    """
    referenced = {path.parent for path in bundle(lock, verify=False) if path.parts[:1] == ("locks",)}
    generated = {name for names in _GRAPH_FILES.values() for name in names}
    retired = []
    for directory in sorted((lock.parent / "locks").glob("*/*")):
        relative = directory.relative_to(lock.parent)
        if (
            relative in referenced
            or any((lock.parent / parent).is_symlink() for parent in (relative, *relative.parents))
            or not directory.is_dir()
        ):
            continue
        entries = list(directory.iterdir())
        if any(entry.is_symlink() or not entry.is_file() or entry.name not in generated for entry in entries):
            continue
        for entry in entries:
            entry.unlink()
        directory.rmdir()
        if not any(directory.parent.iterdir()):
            directory.parent.rmdir()
        retired.append(relative)
    return retired


def main() -> int:
    """Retire stale graphs next to a deployed global lock."""
    parser = argparse.ArgumentParser(
        description="Remove deployed dependency graphs that mise.lock no longer references."
    )
    parser.add_argument("lock", type=Path, help="deployed global mise.lock")
    arguments = parser.parse_args()
    try:
        retired = retire(arguments.lock)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Cannot retire mise dependency graphs: {error}\n")
        return 1
    for relative in retired:
        sys.stdout.write(f"Retired {arguments.lock.parent / relative}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
