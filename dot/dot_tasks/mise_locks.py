"""Capture the global mise lock and its referenced native dependency files."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import tomllib
from pathlib import Path

_GRAPH_FILES = {"uv": ("pyproject.toml", "uv.lock"), "aube": ("package.json", "aube-lock.yaml")}


def bundle(lock: Path, *, verify: bool = True) -> dict[Path, bytes]:
    """Read a lock bundle; allow damaged old graphs only when repairing a destination."""
    content = lock.read_bytes()
    document = tomllib.loads(content.decode())
    if document.get("lockfile_version") not in (1, 2):
        raise ValueError("Unsupported mise lock format; regenerate with mise lock --global")
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
    """Copy referenced files, publish the lock last, then retire old references."""
    incoming = bundle(source)
    if tomllib.loads(incoming[Path(source.name)].decode())["lockfile_version"] != 2:
        raise ValueError("Upgrade the global lock first: mise lock --global --upgrade")
    previous = bundle(destination, verify=False) if destination.exists() else {}
    # Validate every write/delete location before changing anything. Personal locks
    # and files not referenced by the previously managed lock are left alone.
    for relative in incoming.keys() | previous.keys():
        if any((destination.parent / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise ValueError(f"Managed dependency files must not use symlinks: {relative}")
    staging = Path(tempfile.mkdtemp(prefix=".mise-lock-capture-", dir=destination.parent))
    retain_recovery = False
    try:
        for relative, content in incoming.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        # Graph paths can be reused when only transitive dependencies change.
        # Keep rollback copies: publishing the top-level lock last alone would
        # leave its old digests pointing at new bytes after an interrupted write.
        backups = staging / "previous"
        changed: list[Path] = []
        try:
            for relative in incoming:
                target = destination if relative == Path(source.name) else destination.parent / relative
                if target.exists():
                    backup = backups / relative
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
            order = [relative for relative in incoming if relative != Path(source.name)] + [Path(source.name)]
            for relative in order:
                target = destination if relative == Path(source.name) else destination.parent / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                changed.append(relative)
                (staging / relative).replace(target)
        except BaseException:
            try:
                for relative in reversed(changed):
                    target = destination if relative == Path(source.name) else destination.parent / relative
                    backup = backups / relative
                    if backup.exists():
                        backup.replace(target)
                    else:
                        target.unlink(missing_ok=True)
            except BaseException as error:
                retain_recovery = True
                raise OSError(
                    f"Lock publication and rollback failed; recovery files retained at {backups}. "
                    f"Restore these files into {destination.parent} before retrying."
                ) from error
            raise
    finally:
        if not retain_recovery:
            shutil.rmtree(staging)
    for relative in previous.keys() - incoming.keys():
        target = destination.parent / relative
        target.unlink()
        parent = target.parent
        while parent != destination.parent and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
