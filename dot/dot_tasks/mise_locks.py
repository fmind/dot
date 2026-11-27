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

from fmind_dot.config import expand_path
from fmind_dot.private_files import write_atomic_file

_GRAPH_FILES = {"uv": ("pyproject.toml", "uv.lock"), "aube": ("package.json", "aube-lock.yaml")}
# Revision 4 (mise 2026.11.1) adds npm provenance repositories; mise refuses newer revisions.
LOCK_REVISION = 4


def _sha256(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()}"


def _has_symlink(root: Path, relative: Path) -> bool:
    return any((root / parent).is_symlink() for parent in (relative, *relative.parents))


def _bundle_path(root: Path, relative: Path) -> Path:
    if _has_symlink(root, relative):
        raise ValueError(f"Lock bundle paths must not use symlinks: {relative}")
    return root / relative


def bundle(lock: Path, *, verify: bool = True) -> dict[Path, bytes]:
    """Read a lock bundle; allow damaged graphs only when repairing a destination."""
    content = _bundle_path(lock.parent, Path(lock.name)).read_bytes()
    doc = tomllib.loads(content.decode())
    if doc.get("lockfile_version") != LOCK_REVISION:
        raise ValueError(f"Unsupported mise lock format; expected revision {LOCK_REVISION}")
    files = {Path(lock.name): content}
    if not isinstance(tools := doc.get("tools"), dict):
        raise ValueError("mise lock must contain a tools table")
    for entries in tools.values():
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            raise ValueError("mise lock tools must contain arrays of version tables")
        for entry in entries:
            for bk, names in _GRAPH_FILES.items():
                if bk not in entry:
                    continue
                if not isinstance(g := entry[bk], dict) or any(
                    not isinstance(g.get(k), str) for k in ("path", "digest")
                ):
                    raise ValueError("Dependency references must contain string path and digest fields")
                rel = Path(g["path"])
                if rel.is_absolute() or len(rel.parts) < 2 or rel.parts[0] != "locks" or ".." in rel.parts:
                    raise ValueError(f"Dependency path must remain under locks/: {rel}")
                for name in names:
                    target = _bundle_path(lock.parent, path := rel / name)
                    if verify or target.exists():
                        files[path] = target.read_bytes()
                if verify and g["digest"] != _sha256(files[rel / names[1]]):
                    raise ValueError(f"Dependency digest mismatch: {rel}; run mise lock --global")
    return files


def _rmdir_empty(parent: Path, stop: Path) -> None:
    while parent != stop and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def capture(source: Path, destination: Path) -> None:
    """Copy referenced files, write the lock last, then retire old references."""
    lock = Path(destination.name)
    incoming = {lock if p == Path(source.name) else p: c for p, c in bundle(source).items()}
    previous = bundle(destination, verify=False) if destination.exists() else {}
    targets = {rel: _bundle_path(destination.parent, rel) for rel in incoming}
    for rel in sorted(incoming, key=lambda path: path == lock):
        targets[rel].parent.mkdir(parents=True, exist_ok=True)
        write_atomic_file(targets[rel], incoming[rel], mode=0o644)
    for rel in previous.keys() - incoming.keys():
        (target := destination.parent / rel).unlink()
        _rmdir_empty(target.parent, destination.parent)


def retire(lock: Path) -> list[Path]:
    """Remove deployed graph directories that the lock no longer references."""
    referenced = {p.parent for p in bundle(lock, verify=False) if p.parts[:1] == ("locks",)}
    generated = {name for names in _GRAPH_FILES.values() for name in names}
    if (locks := lock.parent / "locks").is_symlink() or not locks.is_dir():
        return []
    retired = []
    for d in sorted(locks.rglob("*")):
        rel = d.relative_to(lock.parent)
        if rel not in referenced and not _has_symlink(lock.parent, rel) and d.is_dir():
            entries = list(d.iterdir())
            if entries and all(not e.is_symlink() and e.is_file() and e.name in generated for e in entries):
                for entry in entries:
                    entry.unlink()
                d.rmdir()
                _rmdir_empty(d.parent, locks)
                retired.append(rel)
    return retired


def _valid_install(candidate: Path, version: str, backend: str, allowed: set[tuple[str, str, str]]) -> bool:
    lockfile = candidate / (".mise-uv/uv.lock" if backend == "uv" else "aube-lock.yaml")
    if backend == "uv":
        meta = candidate / ".mise-uv"
        if meta.is_symlink() or not meta.is_dir() or (pj := meta / "python.json").is_symlink() or not pj.is_file():
            return False
        try:
            interp = json.loads(pj.read_text(encoding="utf-8"))
        except OSError, UnicodeDecodeError, ValueError:
            return False
        if not (isinstance(interp, list) and interp and isinstance(interp[0], str) and Path(interp[0]).exists()):
            return False
    ok = not lockfile.is_symlink() and lockfile.is_file()
    return ok and (version, backend, _sha256(lockfile.read_bytes())) in allowed


def retire_installs(lock: Path, installs: Path) -> list[Path]:
    """Remove hash-suffixed uv/aube tool installs whose graph or interpreter was retired."""
    raw_lock = bundle(lock, verify=False)[Path(lock.name)]
    if installs.is_symlink() or not installs.is_dir():
        return []
    active: dict[str, set[tuple[str, str, str]]] = {}
    for entries in tomllib.loads(raw_lock.decode("utf-8"))["tools"].values():
        for e in entries:
            if isinstance(ver := e.get("version"), str):
                for bk in (k for k in _GRAPH_FILES if k in e):
                    active.setdefault(Path(e[bk]["path"]).parts[1], set()).add((ver, bk, e[bk]["digest"]))
    retired: list[Path] = []
    for slug, allowed in sorted(active.items()):
        if (tool_dir := installs / slug).is_symlink() or not tool_dir.is_dir():
            continue
        dead: set[str] = set()
        for c in (x for x in sorted(tool_dir.iterdir()) if not x.is_symlink() and x.is_dir()):
            p = c.name.split("~")
            hashed = len(p) == 3 and p[1] in _GRAPH_FILES and p[2]
            stale = hashed and not _valid_install(c, p[0], p[1], allowed)
            if any(v == p[0] for v, _, _ in allowed) and (len(p) == 1 or stale):
                shutil.rmtree(c)
                retired.append(c)
                dead.add(c.name)
        if dead:
            target = gl.readlink() if (gl := tool_dir / "global").is_symlink() and gl.exists() else None
            for entry in sorted(tool_dir.iterdir()):
                if entry.is_symlink() and not entry.exists() and entry.readlink().name in dead:
                    entry.unlink()
                    if target is not None:
                        entry.symlink_to(target)
    return retired


def _xdg_dir(name: str, default: str) -> Path:
    if (raw := os.environ.get(name)) and (candidate := expand_path(os.path.expandvars(raw))).is_absolute():
        return candidate
    return Path.home() / default


def _mise_data_dir() -> Path:
    if (raw := os.environ.get("MISE_DATA_DIR")) and (candidate := expand_path(os.path.expandvars(raw))).is_absolute():
        return candidate
    return _xdg_dir("XDG_DATA_HOME", ".local/share") / "mise"


def main() -> int:
    """Retire stale graphs and hash-suffixed installs next to a deployed global lock."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("lock", type=Path, help="deployed global mise.lock")
    lock, installs = parser.parse_args().lock, _mise_data_dir() / "installs"
    try:
        for path in [*(lock.parent / rel for rel in retire(lock)), *retire_installs(lock, installs)]:
            sys.stdout.write(f"Retired {path}\n")
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Cannot retire mise dependency graphs: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
