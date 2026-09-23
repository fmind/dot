"""Capture the global mise lock and its referenced native dependency files."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import tomllib
from pathlib import Path

_GRAPH_FILES = {"uv": ("pyproject.toml", "uv.lock"), "aube": ("package.json", "aube-lock.yaml")}


def bundle(lock: Path) -> dict[Path, bytes]:
    """Read and validate a complete lock before changing the managed source."""
    content = lock.read_bytes()
    document = tomllib.loads(content.decode())
    if document.get("lockfile_version") not in (1, 2):
        raise ValueError("Unsupported mise lock format; regenerate with mise lock --global")
    files = {Path(lock.name): content}
    for entries in document["tools"].values():
        for entry in entries:
            for backend, names in _GRAPH_FILES.items():
                if backend not in entry:
                    continue
                graph = entry[backend]
                relative = Path(graph["path"])
                if relative.is_absolute() or relative.parts[:1] != ("locks",) or ".." in relative.parts:
                    raise ValueError(f"Dependency path must remain under locks/: {relative}")
                for name in names:
                    path = relative / name
                    target = lock.parent / path
                    if any((lock.parent / parent).is_symlink() for parent in (path, *path.parents)):
                        raise ValueError(f"Dependency files must not use symlinks: {path}")
                    files[path] = target.read_bytes()
                digest = hashlib.sha256(files[relative / names[1]].replace(b"\r\n", b"\n")).hexdigest()
                if graph["digest"] != f"sha256:{digest}":
                    raise ValueError(f"Dependency digest mismatch: {relative}; run mise lock --global")
    return files


def capture(source: Path, destination: Path) -> None:
    """Copy referenced files, publish the lock last, then retire old references."""
    incoming = bundle(source)
    if tomllib.loads(incoming[Path(source.name)].decode())["lockfile_version"] != 2:
        raise ValueError("Upgrade the global lock first: mise lock --global --upgrade")
    previous = bundle(destination) if destination.exists() else {}
    # Validate every write/delete location before changing anything. Personal locks
    # and files not referenced by the previously managed lock are left alone.
    for relative in incoming.keys() | previous.keys():
        if any((destination.parent / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise ValueError(f"Managed dependency files must not use symlinks: {relative}")
    with tempfile.TemporaryDirectory(prefix=".mise-lock-capture-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        for relative, content in incoming.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for relative in incoming:
            if relative == Path(source.name):
                continue
            target = destination.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            (staging / relative).replace(target)
        (staging / source.name).replace(destination)
    for relative in previous.keys() - incoming.keys():
        target = destination.parent / relative
        target.unlink()
        parent = target.parent
        while parent != destination.parent and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def main() -> int:
    """Capture the configured workstation lock into this source checkout."""
    root = Path(__file__).resolve().parents[2]
    try:
        capture(Path.home() / ".config/mise/mise.lock", root / "dot_config/mise/mise.lock")
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write(f"Cannot capture mise lockfiles: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
