"""Safe cleanup and release workflows for the Python CLI."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import tomllib
import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, BinaryIO

import typer
from typer import _click
from typer.core import TyperCommand

from fmind_dot.commands import add_group, aliased_command, state_from
from fmind_dot.config import ChezmoiCleanConfig, PruneTargetConfig, SessionStoreConfig, expand_path
from fmind_dot.errors import DotError
from fmind_dot.session_store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SESSION_STORE_VERSION,
    SessionManifest,
    read_session_manifest,
    session_digest,
    session_generation_id,
    validate_session_generation,
)
from fmind_dot.state import State

_GROK_TRANSCRIPT = "updates.jsonl"
_GROK_SIBLING = "chat_history.jsonl"
_RELEASE_VERSION_FILE = Path("dot/pyproject.toml")
_RELEASE_CHANGELOG_FILE = Path("CHANGELOG.md")
_RELEASE_LOCK_FILE = Path("dot/uv.lock")
_RELEASE_GENERATED_FILES = (_RELEASE_CHANGELOG_FILE, _RELEASE_VERSION_FILE, _RELEASE_LOCK_FILE)
_RELEASE_CLIFF_CONFIG = Path("dot_config/git-cliff/cliff.toml")
_REMOTE_TAG_OUTPUT_LIMIT = 4 * 1024
_SEMVER_TAG = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_PROJECT_SECTION = re.compile(r"(?m)^\[project\]\s*$")
_SECTION = re.compile(r"(?m)^\[[^\n]+\]\s*$")
_VERSION_ASSIGNMENT = re.compile(r'(?m)^version\s*=\s*"([^"\r\n]+)"\s*$')
_LEVELS: dict[str, tuple[str, ...]] = {
    "agents": ("sessions",),
    "docker": ("build", "system"),
    "python": ("cache", "all"),
    "mise": ("cache", "configs"),
    "tools": ("cache",),
}
_ALL_LEVELS = ("shallow", "deep")
_PRUNE_LEVEL_BARE = "__fmind_dot_bare_prune_level__"
_BARE_PRUNE_OPTIONS = {
    "--agents": f"--agents={_PRUNE_LEVEL_BARE}",
    "-a": f"-a{_PRUNE_LEVEL_BARE}",
    "--docker": f"--docker={_PRUNE_LEVEL_BARE}",
    "-d": f"-d{_PRUNE_LEVEL_BARE}",
    "--python": f"--python={_PRUNE_LEVEL_BARE}",
    "-p": f"-p{_PRUNE_LEVEL_BARE}",
    "--mise": f"--mise={_PRUNE_LEVEL_BARE}",
    "-m": f"-m{_PRUNE_LEVEL_BARE}",
    "--tools": f"--tools={_PRUNE_LEVEL_BARE}",
    "-t": f"-t{_PRUNE_LEVEL_BARE}",
    "--all": f"--all={_PRUNE_LEVEL_BARE}",
    "-A": f"-A{_PRUNE_LEVEL_BARE}",
}
_REGISTERED: weakref.WeakSet[typer.Typer] = weakref.WeakSet()


class _PruneCommand(TyperCommand):
    """Let prune's level options use their configured value when bare."""

    def parse_args(self, ctx: _click.Context, args: list[str]) -> list[str]:
        # Click has no optional-value option, so only exact bare tokens need adaptation.
        return super().parse_args(ctx, [_BARE_PRUNE_OPTIONS.get(argument, argument) for argument in args])


@dataclass(frozen=True)
class PruneOptions:
    """Resolved prune targets and non-destructive modifiers."""

    targets: dict[str, str]
    days: int | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class _SuccessorEvidence:
    reason: str
    evidence: str
    verified: bool = False


@dataclass
class _PruneRun:
    state: State
    options: PruneOptions
    reclaimed: int = 0

    def report(self, target: str, message: str) -> None:
        self.state.stdout.write(f"{'○' if self.options.dry_run else '✓'} {target}: {message}\n")


@dataclass(frozen=True)
class _ReleaseSnapshot:
    version: bytes
    changelog: bytes
    lock: bytes
    version_mode: int
    changelog_mode: int
    lock_mode: int


@dataclass(frozen=True)
class _CreatedDirectory:
    parent_fd: int
    name: str
    device: int
    inode: int


@dataclass(frozen=True)
class _BoundSource:
    path: Path
    parent_parts: tuple[str, ...]
    name: str
    parent_fd: int
    parent_device: int
    parent_inode: int
    source_device: int
    source_inode: int


def _require_tool(state: State, command: str, guidance: str | None = None) -> None:
    if state.runner.which(command) is None:
        suffix = f"; {guidance}" if guidance else ""
        raise DotError(f"{command} is not installed{suffix}")


def _expand(value: str | Path) -> Path:
    return expand_path(value).absolute()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _reject_symlinked_ancestors(path: Path, boundary: Path) -> None:
    """Reject existing linked parents while leaving the final entry movable as a link."""
    try:
        relative = path.relative_to(boundary)
    except ValueError as error:
        raise DotError(f"path {path} escaped its boundary {boundary}") from error
    current = boundary
    for part in relative.parts[:-1]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            raise DotError(f"failed to inspect path ancestor {current}: {error}") from error
        if stat.S_ISLNK(info.st_mode):
            raise DotError(f"refusing path with symbolic-link ancestor: {path}")


def validate_prune_path(value: str | Path) -> Path:
    """Resolve a configured deletion path and reject broad or escaping targets."""
    path = expand_path(value)
    if not path.is_absolute():
        raise DotError(f"refusing to prune non-absolute path: {path}")
    # Lexical containment and descriptor-relative traversal must agree on the target.
    if ".." in path.parts:
        raise DotError(f"refusing to prune path with parent traversal: {path}")
    path = path.absolute()
    home = Path.home().absolute()
    if path == Path(path.anchor):
        raise DotError(f"refusing to prune filesystem root {path}")
    if path == home:
        raise DotError(f"refusing to prune home directory {path}")
    if not _is_relative_to(path, home):
        raise DotError(f"refusing to prune path outside home directory: {path}")

    current = home
    for part in path.relative_to(home).parts:
        current /= part
        if current.is_symlink():
            raise DotError(f"refusing to prune path with symbolic-link component: {path}")
    return path


def _raise_walk_error(error: OSError) -> None:
    raise error


def _remove_tree(run: _PruneRun, target: str, value: str | Path, label: str) -> None:
    path = validate_prune_path(value)
    size = 0
    target_found = False
    try:
        with _open_confined_directory(path.parent) as parent_fd:
            info = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            target_found = True
            if stat.S_ISLNK(info.st_mode):
                raise DotError(f"refusing to prune symbolic link: {path}")
            if stat.S_ISDIR(info.st_mode):
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
                directory_fd = os.open(path.name, flags, dir_fd=parent_fd)
                try:
                    opened_info = os.fstat(directory_fd)
                    size = _directory_bytes_confined(directory_fd)
                    run.reclaimed += size
                    if run.options.dry_run:
                        run.report(target, f"would remove {label} ({human_bytes(size)})")
                        return
                    _clear_directory_confined(directory_fd)
                    current_info = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
                    if (current_info.st_dev, current_info.st_ino) != (opened_info.st_dev, opened_info.st_ino):
                        raise DotError(f"prune path changed during deletion: {path}")
                    os.rmdir(path.name, dir_fd=parent_fd)
                finally:
                    os.close(directory_fd)
            else:
                size = info.st_size if stat.S_ISREG(info.st_mode) else 0
                run.reclaimed += size
                if run.options.dry_run:
                    run.report(target, f"would remove {label} ({human_bytes(size)})")
                    return
                current_info = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
                if (current_info.st_dev, current_info.st_ino) != (info.st_dev, info.st_ino):
                    raise DotError(f"prune path changed during deletion: {path}")
                os.unlink(path.name, dir_fd=parent_fd)
    except FileNotFoundError:
        if target_found:
            raise DotError(f"prune path changed during deletion: {path}") from None
        run.report(target, f"nothing to remove in {label}")
        return
    except NotADirectoryError as error:
        raise DotError(f"expected prune path ancestors to be directories: {path}") from error
    run.report(target, f"removed {label} ({human_bytes(size)})")


def _remove_contents(run: _PruneRun, target: str, value: str | Path, label: str) -> None:
    path = validate_prune_path(value)
    try:
        with _open_confined_directory(path) as directory_fd:
            size = _directory_bytes_confined(directory_fd)
            run.reclaimed += size
            if run.options.dry_run:
                run.report(target, f"would clear {label} ({human_bytes(size)})")
                return
            _clear_directory_confined(directory_fd)
    except FileNotFoundError:
        run.report(target, f"nothing to remove in {label}")
        return
    except NotADirectoryError as error:
        raise DotError(f"expected prune path to be a directory: {path}") from error
    run.report(target, f"cleared {label} ({human_bytes(size)})")


def _execute(run: _PruneRun, target: str, summary: str, args: Sequence[str]) -> None:
    if run.state.runner.which(args[0]) is None:
        run.report(target, f"{args[0]} is not installed")
        return
    if run.options.dry_run:
        run.report(target, f"would {summary}")
        return
    run.state.runner.run(args)
    run.report(target, summary)


def _prune_docker(run: _PruneRun, level: str) -> None:
    if run.state.runner.which("docker") is None:
        run.report("docker", "docker is not installed")
        return
    if run.options.dry_run:
        run.report("docker", "would prune the Docker build cache")
        if level == "system":
            run.report("docker", "would prune stopped containers, networks, and dangling images")
        return
    if run.state.runner.run(["docker", "info"], check=False).returncode != 0:
        run.report("docker", "docker daemon is not running")
        return
    _execute(run, "docker", "pruned the build cache", ["docker", "builder", "prune", "-af"])
    if level == "system":
        _execute(
            run,
            "docker",
            "pruned stopped containers, networks, and dangling images",
            ["docker", "system", "prune", "-f"],
        )


def _prune_python(run: _PruneRun, level: str) -> None:
    if level == "cache":
        _execute(run, "python", "pruned unused uv cache entries", ["uv", "cache", "prune"])
        return
    _execute(run, "python", "cleaned the uv cache", ["uv", "cache", "clean"])
    _execute(run, "python", "purged the pip cache", ["pip", "cache", "purge"])


def _prune_mise(run: _PruneRun, level: str) -> None:
    _execute(run, "mise", "pruned unused tool versions", ["mise", "prune", "-y"])
    _execute(run, "mise", "cleared the cache", ["mise", "cache", "clear"])
    for value in run.state.config.prune.mise.paths:
        _remove_contents(run, "mise", value, value)
    if level == "configs":
        _execute(run, "mise", "pruned untracked config links", ["mise", "prune", "--configs", "-y"])


def _prune_tools(run: _PruneRun) -> None:
    for value in run.state.config.prune.tools.paths:
        _remove_tree(run, "tools", value, value)
    _execute(run, "tools", "cleared the dprint cache", ["dprint", "clear-cache"])


def _fingerprint(path: Path) -> str:
    with path.open("rb") as stream:
        return _fingerprint_stream(stream)


def _fingerprint_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _require_fd_confinement() -> None:
    required = (os.open, os.stat, os.unlink, os.rmdir)
    if (
        getattr(os, "O_DIRECTORY", 0) == 0
        or getattr(os, "O_NOFOLLOW", 0) == 0
        or not hasattr(os, "fwalk")
        or any(function not in os.supports_dir_fd for function in required)
    ):
        raise DotError("this platform cannot safely confine filesystem deletion")


@contextmanager
def _open_confined_directory(path: Path) -> Iterator[int]:
    """Open each absolute path component without following symbolic links."""
    _require_fd_confinement()
    if not path.is_absolute():
        raise DotError(f"session-store root must be absolute: {path}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _require_mutation_confinement() -> None:
    _require_fd_confinement()
    if any(function not in os.supports_dir_fd for function in (os.mkdir, os.rename)):
        raise DotError("this platform cannot safely confine filesystem mutation")


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _file_metadata(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    """Capture the fields that must stay stable before deleting a file."""
    return info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns, info.st_size


def _open_relative_directory(
    root_fd: int,
    parts: Sequence[str],
    *,
    create_mode: int | None = None,
    created: list[_CreatedDirectory] | None = None,
) -> int:
    """Open a relative directory chain without re-resolving an earlier component."""
    descriptor = os.dup(root_fd)
    try:
        for component in parts:
            if not component or component in {".", ".."} or Path(component).name != component:
                raise DotError(f"unsafe relative directory component {component!r}")
            made = False
            try:
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if create_mode is None:
                    raise
                try:
                    os.mkdir(component, mode=create_mode, dir_fd=descriptor)
                    made = True
                except FileExistsError:
                    pass
                child = os.open(component, _directory_flags(), dir_fd=descriptor)
            if made:
                if create_mode is None:
                    raise DotError("directory creation mode is unavailable")
                os.fchmod(child, create_mode)
                if created is not None:
                    info = os.fstat(child)
                    created.append(_CreatedDirectory(os.dup(descriptor), component, info.st_dev, info.st_ino))
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _verify_absolute_directory(path: Path, expected_fd: int, label: str) -> None:
    expected = _identity(os.fstat(expected_fd))
    try:
        with _open_confined_directory(path) as current_fd:
            current = _identity(os.fstat(current_fd))
    except (DotError, OSError) as error:
        raise DotError(f"{label} changed during operation: {path}") from error
    if current != expected:
        raise DotError(f"{label} changed during operation: {path}")


def _verify_relative_directory(root_fd: int, parts: Sequence[str], expected_fd: int, label: str) -> None:
    expected = _identity(os.fstat(expected_fd))
    try:
        current_fd = _open_relative_directory(root_fd, parts)
    except (DotError, OSError) as error:
        raise DotError(f"{label} changed during operation") from error
    try:
        current = _identity(os.fstat(current_fd))
    finally:
        os.close(current_fd)
    if current != expected:
        raise DotError(f"{label} changed during operation")


def _fingerprint_at(directory_fd: int, name: str) -> str:
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise OSError(errno.EINVAL, "session source is no longer a regular file", name)
        return _fingerprint_stream(stream)


def _stat_at(directory_fd: int, name: str) -> os.stat_result:
    return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)


def _directory_bytes_confined(root_fd: int) -> int:
    """Measure regular files below an already-open directory without path re-resolution."""
    _require_fd_confinement()
    total = 0
    for _walk_root, _directories, names, directory_fd in os.fwalk(
        ".", follow_symlinks=False, onerror=_raise_walk_error, dir_fd=root_fd
    ):
        for name in names:
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def _clear_directory_confined(root_fd: int) -> None:
    """Clear an already-open directory tree using only descriptor-relative removal."""
    _require_fd_confinement()
    for _walk_root, directories, names, directory_fd in os.fwalk(
        ".", topdown=False, follow_symlinks=False, onerror=_raise_walk_error, dir_fd=root_fd
    ):
        for name in names:
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(info.st_mode):
                raise DotError(f"prune entry changed into a directory during deletion: {name}")
            with suppress(FileNotFoundError):
                os.unlink(name, dir_fd=directory_fd)
        for name in directories:
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            try:
                if stat.S_ISDIR(info.st_mode):
                    os.rmdir(name, dir_fd=directory_fd)
                else:
                    os.unlink(name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def _session_source(store: SessionStoreConfig) -> str:
    if store.source:
        return store.source
    path = store.path.replace("\\", "/").rstrip("/")
    suffixes = {
        "/.agents/sessions": "archive",
        "/.claude/projects": "claude",
        "/.codex/sessions": "codex",
        "/.copilot/session-store.db": "copilot",
        "/.gemini/antigravity-cli/brain": "agy",
        "/.grok/sessions": "grok",
    }
    return next((source for suffix, source in suffixes.items() if path.endswith(suffix)), "")


def _valid_session_id(value: str) -> bool:
    return bool(value) and all(
        character.isascii() and (character.isalnum() or character in "-_") for character in value
    )


def _raw_session_identity(root: Path, path: Path, source: str) -> str | None:
    name = path.name
    if source == "claude" and name.endswith(".jsonl") and name != "memory.jsonl":
        candidate = name.removesuffix(".jsonl")
    elif source == "codex" and name.endswith(".jsonl"):
        parts = name.removesuffix(".jsonl").split("-", 6)
        candidate = parts[6] if len(parts) == 7 and parts[0] == "rollout" else ""
    elif source == "grok" and name == _GROK_TRANSCRIPT:
        candidate = path.parent.name
    elif source == "agy" and name in {"transcript.jsonl", "transcript_full.jsonl"}:
        relative = path.relative_to(root)
        candidate = relative.parts[0] if len(relative.parts) >= 2 else ""
    else:
        return None
    return candidate if _valid_session_id(candidate) else None


def _validate_generation(path: Path, manifest: SessionManifest) -> bool:
    try:
        validate_session_generation(path, manifest)
    except OSError, TypeError, ValueError, json.JSONDecodeError:
        return False
    return True


def _find_successor(source: str, session_id: str, fingerprint: str) -> _SuccessorEvidence:
    lineage = session_digest(source, session_id)
    lineage_dir = Path.home() / ".agents" / "sessions" / SESSION_STORE_VERSION / source / lineage
    try:
        entries = list(lineage_dir.iterdir())
    except FileNotFoundError:
        return _SuccessorEvidence("unnormalized", "none")
    except OSError:
        return _SuccessorEvidence("unreadable-successor", f"lineage={lineage[:12]}")

    matches: list[str] = []
    interrupted = partial = stale = unreadable = False
    for entry in entries:
        if entry.name.startswith(".ingest-"):
            interrupted = True
            continue
        if entry.is_symlink() or not entry.is_dir():
            unreadable = True
            continue
        try:
            manifest = read_session_manifest(entry)
        except OSError, TypeError, ValueError, json.JSONDecodeError:
            unreadable = True
            continue
        identity = manifest.agent == source and manifest.session_id == session_id and manifest.lineage_id == lineage
        if not identity:
            unreadable = True
            continue
        if (
            manifest.source_fingerprint != fingerprint
            or manifest.schema_version != SESSION_SCHEMA_VERSION
            or manifest.parser_version != SESSION_PARSER_VERSION
        ):
            stale = True
            continue
        if entry.name != session_generation_id(fingerprint):
            unreadable = True
            continue
        if manifest.completeness != "complete":
            partial = True
            continue
        if not _validate_generation(entry, manifest):
            unreadable = True
            continue
        matches.append(entry.name)
    if len(matches) == 1:
        return _SuccessorEvidence(
            "verified-successor",
            f"generation={matches[0][:12]} fingerprint={fingerprint[:12]} completeness=complete",
            True,
        )
    if len(matches) > 1:
        return _SuccessorEvidence("ambiguous-successor", f"matches={len(matches)} fingerprint={fingerprint[:12]}")
    if partial:
        return _SuccessorEvidence("partial-successor", f"fingerprint={fingerprint[:12]}")
    if unreadable:
        return _SuccessorEvidence("unreadable-successor", f"lineage={lineage[:12]}")
    if interrupted:
        return _SuccessorEvidence("interrupted-ingestion", f"lineage={lineage[:12]}")
    if stale:
        return _SuccessorEvidence("stale-successor", f"fingerprint={fingerprint[:12]}")
    return _SuccessorEvidence("unnormalized", "none")


def _report_session_decision(
    run: _PruneRun,
    decision: str,
    source: str,
    lineage: str,
    age: timedelta,
    size: int,
    reason: str,
    successor: str,
) -> None:
    if not run.options.dry_run and (
        decision == "delete" or reason in {"within-retention", "protected-tree", "protected-name"}
    ):
        return
    run.report(
        "agents",
        f"decision={decision} source={source} lineage={lineage} age={str(age).split('.')[0]} "
        f"size={human_bytes(size)} reason={reason} successor={successor}",
    )


def _remove_empty_directories_confined(root_fd: int, keep: set[str]) -> None:
    """Remove empty descendants through fwalk's race-safe directory handles."""
    _require_fd_confinement()
    for walk_root, directories, _names, directory_fd in os.fwalk(
        ".", topdown=False, follow_symlinks=False, onerror=_raise_walk_error, dir_fd=root_fd
    ):
        relative = Path(walk_root)
        if any(part in keep for part in relative.parts):
            continue
        for name in directories:
            if name in keep:
                continue
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(info.st_mode):
                continue
            try:
                os.rmdir(name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            except OSError as error:
                if error.errno not in {errno.ENOTEMPTY, errno.EEXIST}:
                    raise


def _prune_raw_sessions(
    run: _PruneRun, root: Path, source: str, cutoff: datetime, now: datetime, keep: set[str]
) -> tuple[int, int]:
    root_info = root.lstat()
    if stat.S_ISLNK(root_info.st_mode):
        raise DotError(f"refusing to traverse linked session store {root}")
    # Shared SQLite stores need source-native pruning; deleting the whole file
    # cannot provide per-session successor proof.
    if source == "copilot":
        age = max(timedelta(), now - datetime.fromtimestamp(root_info.st_mtime, UTC))
        _report_session_decision(
            run,
            "retain",
            source,
            session_digest(str(root))[:12],
            age,
            root_info.st_size,
            "ambiguous-shared-store",
            "none",
        )
        return 0, 0
    files = total = 0
    with _open_confined_directory(root) as root_fd:
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            raise DotError(f"session store must be a real directory: {root}")
        for walk_root, directories, names, directory_fd in os.fwalk(
            ".", follow_symlinks=False, onerror=_raise_walk_error, dir_fd=root_fd
        ):
            relative = Path(walk_root)
            current = root if relative == Path() else root / relative
            kept_directories: list[str] = []
            for name in directories:
                directory = current / name
                try:
                    info = _stat_at(directory_fd, name)
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(info.st_mode):
                    age = max(timedelta(), now - datetime.fromtimestamp(info.st_mtime, UTC))
                    _report_session_decision(
                        run,
                        "retain",
                        source,
                        session_digest(str(directory))[:12],
                        age,
                        0,
                        "link-or-special-file",
                        "none",
                    )
                elif name in keep:
                    if run.options.dry_run:
                        age = max(timedelta(), now - datetime.fromtimestamp(info.st_mtime, UTC))
                        _report_session_decision(
                            run,
                            "retain",
                            source,
                            session_digest(str(directory))[:12],
                            age,
                            info.st_size,
                            "protected-tree",
                            "not-required",
                        )
                else:
                    kept_directories.append(name)
            directories[:] = kept_directories

            for name in names:
                path = current / name
                if source == "grok" and name == _GROK_SIBLING:
                    continue
                try:
                    info = _stat_at(directory_fd, name)
                except FileNotFoundError:
                    continue
                age = max(timedelta(), now - datetime.fromtimestamp(info.st_mtime, UTC))
                fallback_lineage = session_digest(str(path))[:12]
                if stat.S_IFMT(info.st_mode) != stat.S_IFREG:
                    _report_session_decision(
                        run, "retain", source, fallback_lineage, age, info.st_size, "link-or-special-file", "none"
                    )
                    continue
                if name in keep:
                    _report_session_decision(
                        run, "retain", source, fallback_lineage, age, info.st_size, "protected-name", "not-required"
                    )
                    continue
                if datetime.fromtimestamp(info.st_mtime, UTC) >= cutoff:
                    _report_session_decision(
                        run, "retain", source, fallback_lineage, age, info.st_size, "within-retention", "not-required"
                    )
                    continue
                session_id = _raw_session_identity(root, path, source)
                if session_id is None:
                    _report_session_decision(
                        run, "retain", source, fallback_lineage, age, info.st_size, "unrecognized-source", "none"
                    )
                    continue
                lineage = session_digest(source, session_id)
                try:
                    fingerprint = _fingerprint_at(directory_fd, name)
                except OSError:
                    _report_session_decision(
                        run, "retain", source, lineage[:12], age, info.st_size, "unreadable-source", "none"
                    )
                    continue
                evidence = _find_successor(source, session_id, fingerprint)
                if not evidence.verified:
                    _report_session_decision(
                        run, "retain", source, lineage[:12], age, info.st_size, evidence.reason, evidence.evidence
                    )
                    continue
                sibling_info: os.stat_result | None = None
                sibling_fingerprint = ""
                sibling_size = 0
                if source == "grok":
                    try:
                        candidate_sibling_info = _stat_at(directory_fd, _GROK_SIBLING)
                    except FileNotFoundError:
                        pass
                    else:
                        if stat.S_ISREG(candidate_sibling_info.st_mode):
                            sibling_info = candidate_sibling_info
                            sibling_size = candidate_sibling_info.st_size
                            sibling_modified = datetime.fromtimestamp(candidate_sibling_info.st_mtime, UTC)
                            sibling_age = max(timedelta(), now - sibling_modified)
                            # Grok writes both files for one session, so either recent snapshot retains the pair.
                            if sibling_modified >= cutoff:
                                _report_session_decision(
                                    run,
                                    "retain",
                                    source,
                                    lineage[:12],
                                    sibling_age,
                                    info.st_size + sibling_size,
                                    "within-retention",
                                    "not-required",
                                )
                                continue
                            try:
                                sibling_fingerprint = _fingerprint_at(directory_fd, _GROK_SIBLING)
                            except OSError:
                                _report_session_decision(
                                    run,
                                    "retain",
                                    source,
                                    lineage[:12],
                                    age,
                                    info.st_size + sibling_size,
                                    "unreadable-source",
                                    "none",
                                )
                                continue
                _report_session_decision(
                    run,
                    "delete",
                    source,
                    lineage[:12],
                    age,
                    info.st_size + sibling_size,
                    evidence.reason,
                    evidence.evidence,
                )
                if run.options.dry_run:
                    files += 1 + int(sibling_info is not None)
                    total += info.st_size + sibling_size
                    continue

                # Re-hash and then re-stat through the still-open parent. The
                # name must still identify the exact metadata snapshot that
                # produced the verified successor before descriptor-relative unlink.
                try:
                    current_fingerprint = _fingerprint_at(directory_fd, name)
                    current_info = _stat_at(directory_fd, name)
                except OSError:
                    current_fingerprint = ""
                    current_info = None
                if (
                    current_fingerprint != fingerprint
                    or current_info is None
                    or _file_metadata(current_info) != _file_metadata(info)
                ):
                    _report_session_decision(
                        run, "retain", source, lineage[:12], age, info.st_size, "changed-during-prune", "none"
                    )
                    continue
                if sibling_info is not None:
                    try:
                        current_sibling_fingerprint = _fingerprint_at(directory_fd, _GROK_SIBLING)
                        current_sibling_info = _stat_at(directory_fd, _GROK_SIBLING)
                    except OSError:
                        current_sibling_fingerprint = ""
                        current_sibling_info = None
                    if (
                        current_sibling_fingerprint != sibling_fingerprint
                        or current_sibling_info is None
                        or _file_metadata(current_sibling_info) != _file_metadata(sibling_info)
                    ):
                        _report_session_decision(
                            run,
                            "retain",
                            source,
                            lineage[:12],
                            age,
                            sibling_size,
                            "changed-during-prune",
                            "none",
                        )
                        continue

                try:
                    os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    _report_session_decision(
                        run, "retain", source, lineage[:12], age, info.st_size, "changed-during-prune", "none"
                    )
                    continue
                files += 1
                total += info.st_size

                if sibling_info is not None:
                    try:
                        os.unlink(_GROK_SIBLING, dir_fd=directory_fd)
                    except FileNotFoundError:
                        _report_session_decision(
                            run,
                            "retain",
                            source,
                            lineage[:12],
                            age,
                            sibling_size,
                            "changed-during-prune",
                            "none",
                        )
                    else:
                        files += 1
                        total += sibling_size
        if not run.options.dry_run:
            _remove_empty_directories_confined(root_fd, keep)
    run.reclaimed += total
    return files, total


def _prune_archive_sessions(run: _PruneRun, root: Path, cutoff: datetime, keep: set[str]) -> tuple[int, int]:
    files = total = 0
    with _open_confined_directory(root) as root_fd:
        for _walk_root, directories, names, directory_fd in os.fwalk(
            ".", follow_symlinks=False, onerror=_raise_walk_error, dir_fd=root_fd
        ):
            kept_directories: list[str] = []
            for name in directories:
                try:
                    info = _stat_at(directory_fd, name)
                except FileNotFoundError:
                    continue
                if name not in keep and stat.S_ISDIR(info.st_mode):
                    kept_directories.append(name)
            directories[:] = kept_directories
            for name in names:
                if name in keep:
                    continue
                try:
                    info = _stat_at(directory_fd, name)
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode) or datetime.fromtimestamp(info.st_mtime, UTC) >= cutoff:
                    continue
                if run.options.dry_run:
                    files += 1
                    total += info.st_size
                    continue
                try:
                    current_info = _stat_at(directory_fd, name)
                except FileNotFoundError:
                    continue
                if (
                    not stat.S_ISREG(current_info.st_mode)
                    or datetime.fromtimestamp(current_info.st_mtime, UTC) >= cutoff
                    or _file_metadata(current_info) != _file_metadata(info)
                ):
                    continue
                try:
                    os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    continue
                files += 1
                total += info.st_size
        run.reclaimed += total
        if not run.options.dry_run:
            _remove_empty_directories_confined(root_fd, keep)
    return files, total


def _prune_agents(run: _PruneRun) -> None:
    config = run.state.config.prune.agents
    keep = set(config.keep)
    now = datetime.now(UTC)
    stores = 0
    known = {"archive", "agy", "claude", "codex", "copilot", "grok"}
    errors: list[str] = []
    for store in config.sessions:
        source = _session_source(store)
        if store.source and source not in known:
            errors.append(f"invalid session source {store.source!r} for {store.path}")
            continue
        try:
            path = validate_prune_path(store.path)
        except DotError as error:
            errors.append(f"invalid agent session path {store.path}: {error}")
            continue
        if not path.exists():
            continue
        days = store.keep_days if run.options.days is None else run.options.days
        if days < 0:
            errors.append(f"retention days cannot be negative for {store.path}")
            continue
        cutoff = now - timedelta(days=days)
        try:
            if source in {"agy", "claude", "codex", "copilot", "grok"}:
                files, size = _prune_raw_sessions(run, path, source, cutoff, now, keep)
            else:
                files, size = _prune_archive_sessions(run, path, cutoff, keep)
        except (DotError, OSError) as error:
            errors.append(str(error))
            continue
        stores += 1
        verb = "would delete" if run.options.dry_run else "deleted"
        run.report("agents", f"{verb} {files} file(s) older than {days} days in {store.path} ({human_bytes(size)})")
    if stores == 0 and not errors:
        run.report("agents", "no session stores found")
    if errors:
        raise DotError("; ".join(errors))


def _configured_level(name: str, config: PruneTargetConfig | None) -> str:
    levels = _LEVELS[name]
    value = config.level if config is not None and config.level else levels[0]
    if value not in levels:
        raise DotError(f"invalid prune.{name}.level {value!r} (expected one of: {', '.join(levels)})")
    return value


def resolve_prune_targets(
    state: State,
    selected: Mapping[str, str | None],
    *,
    all_targets: bool,
    deep: bool,
    all_level: str | None = None,
) -> dict[str, str]:
    """Resolve target-specific and aggregate levels before any prune action runs."""
    unknown = set(selected) - set(_LEVELS)
    if unknown:
        name = min(unknown)
        raise DotError(f"unknown prune target {name!r}")
    for name, level in selected.items():
        if level is not None and level not in _LEVELS[name]:
            raise DotError(f"invalid level {level!r} for --{name} (expected one of: {', '.join(_LEVELS[name])})")
    if all_level is not None and all_level not in _ALL_LEVELS:
        raise DotError(f"invalid level {all_level!r} for --all (expected one of: {', '.join(_ALL_LEVELS)})")

    targets: dict[str, str] = {}
    config = state.config.prune
    settings: dict[str, PruneTargetConfig | None] = {
        "agents": None,
        "docker": config.docker,
        "python": config.python,
        "mise": config.mise,
        "tools": config.tools,
    }
    for name in _LEVELS:
        if name in selected:
            explicit_level = selected[name]
            if explicit_level is not None:
                targets[name] = explicit_level
            elif deep:
                targets[name] = _LEVELS[name][-1]
            else:
                targets[name] = _configured_level(name, settings[name])
        elif all_targets:
            targets[name] = (
                _LEVELS[name][-1] if deep or all_level == "deep" else _configured_level(name, settings[name])
            )
    return targets


def run_prune(state: State, options: PruneOptions) -> int:
    """Execute selected prune targets and return bytes deleted or eligible."""
    if options.days is not None and options.days < 0:
        raise DotError("retention days cannot be negative")
    if not options.targets:
        state.stdout.write("No target selected. Choose --agents, --docker, --python, --mise, --tools, or --all.\n")
        return 0
    for name, level in options.targets.items():
        if name not in _LEVELS:
            raise DotError(f"unknown prune target {name!r}")
        if level not in _LEVELS[name]:
            raise DotError(f"invalid level {level!r} for {name} (expected one of: {', '.join(_LEVELS[name])})")

    run = _PruneRun(state, options)
    state.stdout.write("Prune (dry run)\n" if options.dry_run else "Prune\n")
    failures: list[str] = []
    handlers: dict[str, Callable[[str], None]] = {
        "agents": lambda _level: _prune_agents(run),
        "docker": lambda level: _prune_docker(run, level),
        "python": lambda level: _prune_python(run, level),
        "mise": lambda level: _prune_mise(run, level),
        "tools": lambda _level: _prune_tools(run),
    }
    for name in _LEVELS:
        if name not in options.targets:
            continue
        try:
            handlers[name](options.targets[name])
        except (DotError, OSError) as error:
            message = f"{name}: {error}"
            failures.append(message)
            state.stdout.write(f"✗ {message}\n")
    verb = "Would reclaim" if options.dry_run else "Reclaimed"
    state.stdout.write(f"{verb} {human_bytes(run.reclaimed)}.\n")
    if failures:
        raise DotError("prune completed with errors: " + "; ".join(failures))
    return run.reclaimed


def human_bytes(size: int) -> str:
    """Render an apparent byte count without hiding small changes."""
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        value /= 1024
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def should_ignore_chezmoi(config: ChezmoiCleanConfig, value: str) -> bool:
    path = Path(value)
    if not path.parts:
        return True
    return (
        path.parts[0] in config.ignored_prefixes
        or path.name in config.ignored_files
        or path.name.startswith(("run_once_", "run_onchange_", "run_before_"))
    )


def _cleanup_created_directories(created: list[_CreatedDirectory], label: str) -> list[str]:
    errors: list[str] = []
    for directory in reversed(created):
        try:
            current = os.stat(directory.name, dir_fd=directory.parent_fd, follow_symlinks=False)
            if _identity(current) != (directory.device, directory.inode):
                errors.append(f"{label} directory changed during cleanup: {directory.name}")
                continue
            os.rmdir(directory.name, dir_fd=directory.parent_fd)
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(f"failed to remove {label} directory {directory.name}: {error}")
        finally:
            os.close(directory.parent_fd)
    return errors


def _cleanup_probe(
    probe: Path,
    parent_fd: int,
    probe_fd: int,
    probe_metadata: tuple[int, int, int, int, int, int] | None,
    created: list[_CreatedDirectory],
) -> None:
    errors: list[str] = []
    if probe_fd >= 0 and probe_metadata is not None:
        try:
            opened = _file_metadata(os.fstat(probe_fd))
            current = _file_metadata(os.stat(probe.name, dir_fd=parent_fd, follow_symlinks=False))
            if opened != probe_metadata or current != probe_metadata:
                errors.append(f"chezmoi probe changed during cleanup: {probe}")
            else:
                os.unlink(probe.name, dir_fd=parent_fd)
        except FileNotFoundError:
            errors.append(f"chezmoi probe changed during cleanup: {probe}")
        except OSError as error:
            errors.append(f"failed to remove chezmoi probe {probe}: {error}")
    errors.extend(_cleanup_created_directories(created, "chezmoi probe"))
    if errors:
        raise DotError("; ".join(errors))


def get_chezmoi_target_path(state: State, source: Path, relative: str) -> str:
    """Map a removed source path with an exclusive, always-cleaned probe."""
    _require_mutation_confinement()
    relative_path = Path(relative)
    if relative_path.is_absolute() or not relative_path.name or ".." in relative_path.parts:
        raise DotError(f"refusing unsafe chezmoi source path {relative!r}")
    source = source.absolute()
    probe = source / relative_path
    if not _is_relative_to(probe.absolute(), source):
        raise DotError(f"chezmoi source path escaped its root: {relative!r}")
    parent_parts = relative_path.parent.parts if relative_path.parent != Path() else ()
    created: list[_CreatedDirectory] = []
    parent_fd = -1
    probe_fd = -1
    probe_metadata: tuple[int, int, int, int, int, int] | None = None
    result: str | None = None
    failures: list[BaseException] = []
    with _open_confined_directory(source) as source_fd:
        try:
            try:
                try:
                    parent_fd = _open_relative_directory(source_fd, parent_parts, create_mode=0o755, created=created)
                except OSError as error:
                    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                        raise DotError(
                            f"refusing path with symbolic-link ancestor or non-directory component: {probe}"
                        ) from error
                    raise
                probe_fd = os.open(
                    probe.name,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=parent_fd,
                )
                probe_metadata = _file_metadata(os.fstat(probe_fd))
                result = state.runner.run(["chezmoi", "target-path", str(probe)]).stdout.strip()
            except (DotError, OSError, KeyboardInterrupt) as error:
                failures.append(error)

            if parent_fd >= 0:
                try:
                    _verify_absolute_directory(source, source_fd, "chezmoi source directory")
                    _verify_relative_directory(source_fd, parent_parts, parent_fd, "chezmoi probe parent")
                except DotError as error:
                    failures.append(error)
                try:
                    _cleanup_probe(probe, parent_fd, probe_fd, probe_metadata, created)
                except DotError as error:
                    failures.append(error)
                finally:
                    created = []
            else:
                cleanup_errors = _cleanup_created_directories(created, "chezmoi probe")
                created = []
                if cleanup_errors:
                    failures.append(DotError("; ".join(cleanup_errors)))
        finally:
            if parent_fd >= 0:
                os.close(parent_fd)
            if probe_fd >= 0:
                os.close(probe_fd)
            if created:
                _cleanup_created_directories(created, "chezmoi probe")

    if failures:
        if len(failures) == 1:
            raise failures[0]
        message = "; ".join(str(error) for error in failures)
        if any(isinstance(error, KeyboardInterrupt) for error in failures):
            state.stderr.write(f"Chezmoi probe cleanup failed: {message}\n")
            raise KeyboardInterrupt
        raise DotError(message) from failures[0]
    return result or ""


def _home_target(home: Path, value: str) -> Path:
    target = _expand(value) if value.startswith("~") or Path(value).is_absolute() else (home / value).absolute()
    if target == home or not _is_relative_to(target, home):
        raise DotError(f"refusing chezmoi target outside the home directory: {target}")
    return target


def _allocate_backup_directory(home: Path, home_fd: int) -> tuple[Path, int]:
    base_parts = (".cache", "dot", "chezmoi-clean")
    base_fd = _open_relative_directory(home_fd, base_parts, create_mode=0o700)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        for index in range(1_000_000):
            name = timestamp if index == 0 else f"{timestamp}.{index}"
            try:
                os.mkdir(name, mode=0o700, dir_fd=base_fd)
            except FileExistsError:
                continue
            backup_fd = os.open(name, _directory_flags(), dir_fd=base_fd)
            os.fchmod(backup_fd, 0o700)
            return home.joinpath(*base_parts, name), backup_fd
    finally:
        os.close(base_fd)
    raise DotError(f"unable to allocate a private backup directory for {timestamp}")


def _bind_source(home_fd: int, home: Path, source: Path) -> _BoundSource:
    relative = source.relative_to(home)
    parent_parts = relative.parent.parts if relative.parent != Path() else ()
    parent_fd = _open_relative_directory(home_fd, parent_parts)
    try:
        parent_info = os.fstat(parent_fd)
        source_info = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
    except BaseException:
        os.close(parent_fd)
        raise
    return _BoundSource(
        path=source,
        parent_parts=parent_parts,
        name=relative.name,
        parent_fd=parent_fd,
        parent_device=parent_info.st_dev,
        parent_inode=parent_info.st_ino,
        source_device=source_info.st_dev,
        source_inode=source_info.st_ino,
    )


def _verify_bound_source(home: Path, home_fd: int, source: _BoundSource) -> None:
    _verify_absolute_directory(home, home_fd, "home directory")
    _verify_relative_directory(
        home_fd, source.parent_parts, source.parent_fd, f"source parent changed for {source.path}"
    )
    current = os.stat(source.name, dir_fd=source.parent_fd, follow_symlinks=False)
    if _identity(current) != (source.source_device, source.source_inode):
        raise DotError(f"orphan source changed during backup: {source.path}")


def backup_orphans(state: State, orphans: Iterable[Path]) -> Path:
    """Move orphaned targets into a private, timestamped recovery directory."""
    _require_mutation_confinement()
    home = Path.home().absolute()
    orphan_list = [orphan.absolute() for orphan in orphans]
    if len(set(orphan_list)) != len(orphan_list):
        raise DotError("refusing duplicate orphan paths")
    for source in orphan_list:
        if not _is_relative_to(source, home) or source == home:
            raise DotError(f"refusing to back up path outside home: {source}")
        _reject_symlinked_ancestors(source, home)

    bindings: list[_BoundSource] = []
    failures: list[str] = []
    backup: Path | None = None
    backup_fd = -1
    with _open_confined_directory(home) as home_fd:
        try:
            for source in orphan_list:
                # Append incrementally so a later bind failure cannot leak earlier descriptors.
                bindings.append(_bind_source(home_fd, home, source))  # noqa: PERF401
            backup, backup_fd = _allocate_backup_directory(home, home_fd)
            for source in bindings:
                destination_parent_fd = -1
                try:
                    _verify_bound_source(home, home_fd, source)
                    destination_parent_fd = _open_relative_directory(
                        backup_fd,
                        source.parent_parts,
                        create_mode=0o700,
                    )
                    try:
                        os.stat(source.name, dir_fd=destination_parent_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise DotError(f"refusing to overwrite existing backup entry for {source.path}")
                    os.rename(
                        source.name,
                        source.name,
                        src_dir_fd=source.parent_fd,
                        dst_dir_fd=destination_parent_fd,
                    )
                except (DotError, OSError) as error:
                    detail = f"{source.path}: {error}"
                    state.stderr.write(f"Error backing up {detail}\n")
                    failures.append(detail)
                    continue
                finally:
                    if destination_parent_fd >= 0:
                        os.close(destination_parent_fd)
                state.stdout.write(f"Backed up: {source.path}\n")
        finally:
            if backup_fd >= 0:
                os.close(backup_fd)
            for source in bindings:
                os.close(source.parent_fd)
    if failures:
        raise DotError(
            f"failed to back up {len(failures)} of {len(orphan_list)} orphaned file(s): {'; '.join(failures)}"
        )
    if backup is None:
        raise DotError("failed to allocate orphan backup directory")
    state.stdout.write(f"✓ Clean up complete. Backups saved to {backup}\n")
    return backup


def _confirm(state: State, prompt: str) -> bool:
    state.stdout.write(prompt)
    answer = state.stdin.readline().strip().lower()
    return answer in {"y", "yes"}


def run_chezmoi_clean(state: State, *, yes: bool = False, interactive: bool = False) -> list[Path]:
    """Find removed chezmoi targets and optionally move them to a backup."""
    if yes and interactive:
        raise DotError("--yes and --interactive are mutually exclusive")
    _require_tool(state, "git")
    _require_tool(state, "chezmoi")
    source_text = state.runner.run(["chezmoi", "source-path"]).stdout.strip()
    if not source_text:
        raise DotError("chezmoi source path is empty")
    source = Path(source_text).absolute()
    if not source.is_dir():
        raise DotError(f"chezmoi source path is not a directory: {source}")
    home = Path.home().absolute()
    state.stdout.write(f"Found chezmoi source directory: {source}\n")
    managed_output = state.runner.run(["chezmoi", "managed"]).stdout
    managed = {_home_target(home, line.strip()) for line in managed_output.splitlines() if line.strip()}
    commands = (
        ["git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"],
        ["git", "diff", "--no-renames", "--name-only", "--diff-filter=D"],
        ["git", "diff", "--cached", "--no-renames", "--name-only", "--diff-filter=D"],
    )
    deleted: set[str] = set()
    for command in commands:
        deleted.update(
            line.strip() for line in state.runner.run(command, cwd=source).stdout.splitlines() if line.strip()
        )

    orphans: list[Path] = []
    mapping_failures: list[str] = []
    for relative in sorted(deleted):
        if should_ignore_chezmoi(state.config.chezmoi_clean, relative):
            continue
        source_path = source / relative
        if source_path.exists() or source_path.is_symlink():
            continue
        try:
            mapped = get_chezmoi_target_path(state, source, relative)
            if not mapped:
                continue
            target = _home_target(home, mapped)
        except (DotError, OSError) as error:
            mapping_failures.append(f"{relative}: {error}")
            continue
        if (not target.exists() and not target.is_symlink()) or target in managed:
            continue
        orphans.append(target)
    if mapping_failures:
        raise DotError("failed to map deleted chezmoi source path(s): " + "; ".join(mapping_failures))
    if not orphans:
        state.stdout.write("✓ No orphaned files found in your home directory.\n")
        return []
    state.stdout.write(f"Detected {len(orphans)} orphaned file(s) in home directory:\n")
    for orphan in orphans:
        state.stdout.write(f"  ▶ {orphan}\n")
    approved = yes or (interactive and _confirm(state, "Move all orphaned files to a backup directory? [y/N]: "))
    if approved:
        backup_orphans(state, orphans)
    elif interactive:
        state.stdout.write("Clean up canceled. No files were modified.\n")
    else:
        state.stdout.write("Re-run with --yes to back up and remove all, or --interactive to confirm.\n")
    return orphans


def _project_version_match(content: str) -> re.Match[str]:
    project = _PROJECT_SECTION.search(content)
    if project is None:
        raise DotError(f"{_RELEASE_VERSION_FILE} must contain a [project] table")
    next_section = _SECTION.search(content, project.end())
    section = content[project.end() : next_section.start() if next_section else len(content)]
    matches = list(_VERSION_ASSIGNMENT.finditer(section))
    if len(matches) != 1:
        raise DotError(
            f"{_RELEASE_VERSION_FILE} [project] must contain exactly one string version; found {len(matches)}"
        )
    match = matches[0]
    return _VERSION_ASSIGNMENT.match(content, project.end() + match.start(), project.end() + match.end()) or match


def read_release_version(root: Path) -> str:
    """Read the sole PEP 621 project version used by release preparation."""
    path = root / _RELEASE_VERSION_FILE
    try:
        content = path.read_text()
        parsed = tomllib.loads(content)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise DotError(f"failed to read {_RELEASE_VERSION_FILE}: {error}") from error
    match = _project_version_match(content)
    value = parsed.get("project", {}).get("version")
    if not isinstance(value, str) or value != match.group(1):
        raise DotError(f"{_RELEASE_VERSION_FILE} has an ambiguous project version")
    return value


def write_release_version(root: Path, tag: str) -> None:
    """Replace only the PEP 621 project version assignment."""
    if not _SEMVER_TAG.fullmatch(tag):
        raise DotError(f"invalid semantic version tag {tag!r}")
    path = root / _RELEASE_VERSION_FILE
    content = path.read_text()
    match = _project_version_match(content)
    start, end = match.span(1)
    updated = content[:start] + tag.removeprefix("v") + content[end:]
    path.write_text(updated)


def validate_release_status(status_output: str) -> None:
    """Reject validation changes outside the generated release files."""
    allowed = {str(path) for path in _RELEASE_GENERATED_FILES}
    unexpected: list[str] = []
    for record in status_output.split("\0"):
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise DotError(f"malformed git status record {record!r}")
        if "R" in record[:2] or "C" in record[:2]:
            raise DotError(f"release validation does not allow renamed or copied paths: {record[3:]!r}")
        path = record[3:]
        if path not in allowed:
            unexpected.append(path)
        elif record[:2] != " M":
            raise DotError(
                f"release validation allows only ordinary worktree modifications, got {record[:2]!r} for {path}"
            )
    if unexpected:
        raise DotError(f"release validation changed unrelated paths: {', '.join(unexpected)}")


def _snapshot_release(root: Path) -> _ReleaseSnapshot:
    version_path = root / _RELEASE_VERSION_FILE
    changelog_path = root / _RELEASE_CHANGELOG_FILE
    lock_path = root / _RELEASE_LOCK_FILE
    return _ReleaseSnapshot(
        version=version_path.read_bytes(),
        changelog=changelog_path.read_bytes(),
        lock=lock_path.read_bytes(),
        version_mode=stat.S_IMODE(version_path.stat().st_mode),
        changelog_mode=stat.S_IMODE(changelog_path.stat().st_mode),
        lock_mode=stat.S_IMODE(lock_path.stat().st_mode),
    )


def _restore_release(root: Path, snapshot: _ReleaseSnapshot) -> None:
    version_path = root / _RELEASE_VERSION_FILE
    changelog_path = root / _RELEASE_CHANGELOG_FILE
    lock_path = root / _RELEASE_LOCK_FILE
    version_path.write_bytes(snapshot.version)
    version_path.chmod(snapshot.version_mode)
    changelog_path.write_bytes(snapshot.changelog)
    changelog_path.chmod(snapshot.changelog_mode)
    lock_path.write_bytes(snapshot.lock)
    lock_path.chmod(snapshot.lock_mode)


def _git_output(state: State, *args: str, cwd: Path | None = None, check: bool = True) -> str:
    return state.runner.run(["git", *args], cwd=cwd, check=check).stdout.strip()


def push_prepared_commit(state: State, remote: str, branch: str, commit: str) -> None:
    """Push a prepared commit, reconciling an uncertain command result."""
    refspec = f"{commit}:refs/heads/{branch}"
    state.runner.interactive(
        ["git", "push", remote, refspec], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    try:
        _git_output(state, "fetch", remote, branch)
        accepted = _git_output(state, "rev-parse", f"{remote}/{branch}")
    except DotError:
        accepted = ""
    if accepted != commit:
        raise DotError(f"failed to push prepared commit {commit} to {refspec}")


def _remote_release_tag_objects(state: State, remote: str, refspec: str) -> tuple[str, str]:
    """Resolve the exact direct tag object and its peeled commit."""
    peeled_ref = f"{refspec}^{{}}"
    result = state.runner.run_bounded(
        ["git", "ls-remote", "--tags", remote, refspec, peeled_ref],
        max_output_bytes=_REMOTE_TAG_OUTPUT_LIMIT,
    )
    if result.output_truncated:
        raise DotError(f"remote tag query for {refspec} exceeded {_REMOTE_TAG_OUTPUT_LIMIT} bytes")
    output = result.stdout.strip()
    direct = peeled = ""
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2:
            raise DotError(f"invalid ls-remote record for {refspec}: {line!r}")
        value, reference = fields
        if reference == refspec:
            if direct and direct != value:
                raise DotError(f"conflicting remote values for {refspec}")
            direct = value
        elif reference == peeled_ref:
            if peeled and peeled != value:
                raise DotError(f"conflicting remote values for {peeled_ref}")
            peeled = value
        else:
            raise DotError(f"unexpected remote tag ref {reference!r} while resolving {refspec}")
    if peeled and not direct:
        raise DotError(f"remote returned {peeled_ref} without its tag object {refspec}")
    return direct, peeled


def remote_release_tag_commit(state: State, remote: str, refspec: str) -> str:
    """Resolve the peeled commit only when the exact remote tag is annotated."""
    direct, peeled = _remote_release_tag_objects(state, remote, refspec)
    return peeled if direct and peeled else ""


def push_release_tag(state: State, remote: str, tag: str, commit: str) -> None:
    """Create and push an annotated tag, reconciling uncertain remote success."""
    refspec = f"refs/tags/{tag}"
    try:
        object_type = _git_output(state, "cat-file", "-t", refspec)
    except DotError:
        _git_output(state, "tag", "-a", tag, "-m", tag, commit)
    else:
        if object_type != "tag":
            raise DotError(f"local tag {tag} must be annotated, found Git object type {object_type!r}")
    tag_object = _git_output(state, "rev-parse", refspec)
    captured_type = _git_output(state, "cat-file", "-t", tag_object)
    if captured_type != "tag":
        raise DotError(f"local tag {tag} must be annotated, found Git object type {captured_type!r}")
    local = _git_output(state, "rev-parse", f"{tag_object}^{{}}")
    if local != commit:
        raise DotError(f"local tag {tag} resolves to {local}, expected release commit {commit}")
    exact_refspec = f"{tag_object}:{refspec}"
    state.runner.interactive(
        ["git", "push", remote, exact_refspec], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    try:
        accepted_object, accepted_commit = _remote_release_tag_objects(state, remote, refspec)
    except DotError:
        accepted_object = accepted_commit = ""
    if accepted_object != tag_object or accepted_commit != commit:
        raise DotError(f"failed to push tag {tag} to {remote}")


def _prepared_release_tag(state: State, root: Path) -> str | None:
    try:
        subject = _git_output(state, "log", "-1", "--pretty=%s")
    except DotError:
        return None
    tag = subject.removeprefix("chore(release): ")
    if not _SEMVER_TAG.fullmatch(tag) or subject != f"chore(release): {tag}":
        return None
    try:
        version = read_release_version(root)
    except DotError:
        return None
    return tag if tag == f"v{version}" else None


def _calculate_release_version(state: State, root: Path) -> tuple[str, str]:
    config = str(_RELEASE_CLIFF_CONFIG)
    bumped = state.runner.run(["git-cliff", "--config", config, "--bumped-version"], cwd=root).stdout.strip()
    if not _SEMVER_TAG.fullmatch(bumped):
        raise DotError(f"git-cliff returned invalid semantic version tag {bumped!r}")
    try:
        current = _git_output(state, "describe", "--tags", "--abbrev=0")
    except DotError:
        current = "v0.0.0"
    return bumped, current


def _validate_prepared_release(state: State, root: Path, expected_tag: str, *, require_clean: bool = False) -> None:
    for task in ("format", "check", "test", "build"):
        state.stdout.write(f"Running {task}...\n")
        code = state.runner.interactive(
            ["mise", "run", task], cwd=root, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
        )
        if code != 0:
            raise DotError(f"project {task} failed")
    status_output = state.runner.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root
    ).stdout
    if require_clean:
        if status_output:
            raise DotError("prepared release validation changed the working tree")
    else:
        validate_release_status(status_output)
    actual_version = read_release_version(root)
    expected_version = expected_tag.removeprefix("v")
    if actual_version != expected_version:
        raise DotError(
            f"release validation changed the package version to {actual_version!r}, expected {expected_version!r}"
        )


def _rollback_staged_release(state: State, root: Path, snapshot: _ReleaseSnapshot, cause: Exception) -> None:
    errors = [str(cause)]
    try:
        state.runner.run(["git", "reset", "--mixed", "HEAD"], cwd=root, timeout=10)
    except DotError as error:
        errors.append(f"failed to restore release index: {error}")
    try:
        _restore_release(root, snapshot)
    except OSError as error:
        errors.append(f"failed to restore release files: {error}")
    raise DotError("; ".join(errors)) from cause


def _recover_interrupted_release(state: State, root: Path, snapshot: _ReleaseSnapshot, *, staged: bool) -> None:
    """Best-effort rollback that preserves KeyboardInterrupt for the CLI's exit 130."""
    errors: list[str] = []
    if staged:
        try:
            state.runner.run(["git", "reset", "--mixed", "HEAD"], cwd=root, timeout=10)
        except (DotError, OSError) as error:
            errors.append(f"failed to restore release index: {error}")
    try:
        _restore_release(root, snapshot)
    except OSError as error:
        errors.append(f"failed to restore release files: {error}")
    for error in errors:
        state.stderr.write(f"Release interruption recovery failed: {error}\n")


def _refresh_installed_cli(state: State, root: Path) -> None:
    # The release commit changes package metadata, so refresh the workstation
    # entrypoint before reporting success. A retry is safe after a remote push.
    state.runner.run(["mise", "run", "--force", "deploy"], cwd=root)


def run_release(state: State, *, yes: bool = False) -> str | None:
    """Prepare, validate, commit, and push one release and its exact tag."""
    _require_tool(state, "git")
    if _git_output(state, "status", "--porcelain"):
        raise DotError("working directory has uncommitted or staged changes; commit or stash them first")
    _require_tool(state, "gh")
    state.runner.run(["gh", "auth", "status"])
    _require_tool(state, "git-cliff", "run 'mise run tools' or install it via mise")
    _require_tool(state, "mise", "release validation cannot run")
    _require_tool(state, "uv", "release lock regeneration cannot run")
    root_text = _git_output(state, "rev-parse", "--show-toplevel")
    if not root_text:
        raise DotError("git returned an empty repository root")
    root = Path(root_text).absolute()
    config = state.config.release
    branch = _git_output(state, "branch", "--show-current")
    if not branch:
        raise DotError("cannot prepare a release from a detached HEAD")
    if branch != config.default_branch:
        raise DotError(f"release preparation requires branch {config.default_branch!r}, current branch is {branch!r}")
    _git_output(state, "fetch", "--prune", "--tags", config.remote)
    head = _git_output(state, "rev-parse", "HEAD")
    upstream = _git_output(state, "rev-parse", f"{config.remote}/{config.default_branch}")
    prepared = _prepared_release_tag(state, root)
    if head != upstream:
        if prepared is None:
            raise DotError(
                f"release branch diverged: HEAD {head} does not equal {config.remote}/{config.default_branch} {upstream}"
            )
        if _git_output(state, "rev-parse", "HEAD^") != upstream:
            raise DotError(f"prepared release commit is not directly ahead of {config.remote}/{config.default_branch}")
    if prepared is not None:
        # A retry can start from a manually created lookalike commit. Re-run the
        # complete gate and require a clean result before any remote mutation.
        _validate_prepared_release(state, root, prepared, require_clean=True)
        if head != upstream:
            push_prepared_commit(state, config.remote, config.default_branch, head)
        push_release_tag(state, config.remote, prepared, head)
        _refresh_installed_cli(state, root)
        state.stdout.write(f"✓ Prepared and tagged {prepared} at {head}.\n")
        return prepared

    bumped, current = _calculate_release_version(state, root)
    if bumped == current:
        state.stdout.write(f"No new conventional commits since {current}. Nothing to release.\n")
        return None
    state.stdout.write(f"Current version: {current}\nNext version:    {bumped}\n")
    if not yes and not _confirm(state, f"Prepare and tag {bumped} for publication? [y/N]: "):
        state.stdout.write("Release canceled.\n")
        return None
    try:
        snapshot = _snapshot_release(root)
    except OSError as error:
        raise DotError(f"failed to snapshot release files: {error}") from error
    try:
        write_release_version(root, bumped)
        state.runner.run(
            ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--bump", "-o", str(_RELEASE_CHANGELOG_FILE)],
            cwd=root,
        )
        state.runner.run(["uv", "lock", "--project", str(_RELEASE_VERSION_FILE.parent)], cwd=root)
        _validate_prepared_release(state, root, bumped)
    except KeyboardInterrupt:
        _recover_interrupted_release(state, root, snapshot, staged=False)
        raise
    except (DotError, OSError) as error:
        try:
            _restore_release(root, snapshot)
        except OSError as restore_error:
            raise DotError(f"{error}; failed to restore release files: {restore_error}") from error
        raise
    try:
        state.runner.run(["git", "add", *(str(path) for path in _RELEASE_GENERATED_FILES)], cwd=root)
        state.runner.run(["git", "commit", "-m", f"chore(release): {bumped}"], cwd=root)
    except KeyboardInterrupt:
        _recover_interrupted_release(state, root, snapshot, staged=True)
        raise
    except (DotError, OSError) as error:
        _rollback_staged_release(state, root, snapshot, DotError(f"git commit preparation failed: {error}"))
    head = _git_output(state, "rev-parse", "HEAD")
    push_prepared_commit(state, config.remote, config.default_branch, head)
    push_release_tag(state, config.remote, bumped, head)
    _refresh_installed_cli(state, root)
    state.stdout.write(f"✓ Released and tagged {bumped} at {head}.\n")
    return bumped


def _prune_command(
    context: typer.Context,
    agents: Annotated[
        str | None,
        typer.Option(
            "--agents", "-a", metavar="[=sessions]", help="Delete expired agent sessions with successor proof"
        ),
    ] = None,
    docker: Annotated[
        str | None,
        typer.Option("--docker", "-d", metavar="[=build|system]", help="Prune the Docker build cache"),
    ] = None,
    python: Annotated[
        str | None,
        typer.Option("--python", "-p", metavar="[=cache|all]", help="Prune Python package caches"),
    ] = None,
    mise: Annotated[
        str | None,
        typer.Option("--mise", "-m", metavar="[=cache|configs]", help="Prune unused mise tools, cache, and downloads"),
    ] = None,
    tools: Annotated[
        str | None,
        typer.Option("--tools", "-t", metavar="[=cache]", help="Clear configured scanner and formatter caches"),
    ] = None,
    all_targets: Annotated[
        str | None,
        typer.Option("--all", "-A", metavar="[=shallow|deep]", help="Select every target"),
    ] = None,
    deep: Annotated[bool, typer.Option("--deep", help="Use each selected target's deepest cleanup level")] = False,
    days: Annotated[int | None, typer.Option("--days", "-D", min=0, help="Override session retention days")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-N", help="Report actions without deleting or running tools")
    ] = False,
) -> None:
    state = state_from(context)
    selected = {
        name: None if level == _PRUNE_LEVEL_BARE else level
        for name, level in {
            "agents": agents,
            "docker": docker,
            "python": python,
            "mise": mise,
            "tools": tools,
        }.items()
        if level is not None
    }
    select_all = all_targets is not None
    all_level = None if all_targets == _PRUNE_LEVEL_BARE else all_targets
    targets = resolve_prune_targets(
        state,
        selected,
        all_targets=select_all,
        deep=deep,
        all_level=all_level,
    )
    run_prune(state, PruneOptions(targets=targets, days=days, dry_run=dry_run))


def _release_command(
    context: typer.Context,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Approve release preparation without prompting")] = False,
) -> None:
    run_release(state_from(context), yes=yes)


_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
chezmoi_app = typer.Typer(
    help="Manage chezmoi configuration and recoverable orphan cleanup", context_settings=_CONTEXT_SETTINGS
)


@aliased_command(chezmoi_app, "clean", "c", help_text="Move previously managed orphaned files to a recoverable backup")
def chezmoi_clean_command(
    context: typer.Context,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Back up every orphan without prompting")] = False,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Prompt before backing up orphans")] = False,
) -> None:
    run_chezmoi_clean(state_from(context), yes=yes, interactive=interactive)


def register(parent: typer.Typer) -> None:
    """Register maintenance commands on a root Typer application."""
    if parent in _REGISTERED:
        return
    aliased_command(
        parent,
        "prune",
        "x",
        cls=_PruneCommand,
        help_text="Reclaim disk space from agent sessions and development caches",
    )(_prune_command)
    aliased_command(parent, "release", "r", help_text="Prepare, tag, and push a release commit")(_release_command)
    add_group(parent, chezmoi_app, "chezmoi", "m")
    _REGISTERED.add(parent)
