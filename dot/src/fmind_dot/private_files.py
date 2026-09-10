"""Descriptor-bound private filesystem operations."""

import os
import secrets
import stat
from contextlib import suppress
from pathlib import Path

_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)


def _safe_agent_fs_available() -> bool:
    required_dir_fd = (os.open, os.stat, os.unlink, os.mkdir, os.rmdir, os.rename)
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and callable(getattr(os, "fwalk", None))
        and all(function in os.supports_dir_fd for function in required_dir_fd)
        and os.stat in os.supports_follow_symlinks
        and os.listdir in os.supports_fd
        and all(callable(getattr(os, name, None)) for name in ("fchmod", "fsync", "listdir", "write"))
    )


def _same_file_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _open_verified_directory(path: Path) -> int:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise OSError(f"unsafe directory {path}")
    descriptor = os.open(path, _DIRECTORY_FLAGS)
    try:
        opened = os.fstat(descriptor)
        after = path.lstat()
        if not _same_file_identity(opened, before) or not _same_file_identity(opened, after):
            raise OSError(f"directory changed while opening {path}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_directory_at(parent: int, name: str) -> int:
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise OSError(f"unsafe directory {name}")
    descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
    try:
        opened = os.fstat(descriptor)
        after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not _same_file_identity(opened, before) or not _same_file_identity(opened, after):
            raise OSError(f"directory changed while opening {name}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_or_create_directory_at(parent: int, name: str, mode: int, *, enforce_mode: bool = True) -> int:
    with suppress(FileExistsError):
        os.mkdir(name, mode=mode, dir_fd=parent)
    descriptor = _open_directory_at(parent, name)
    try:
        if enforce_mode:
            os.fchmod(descriptor, mode)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _publish_owner_only_at(directory: int, name: str, content: bytes) -> None:
    temporary = f".{name}.{secrets.token_hex(8)}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        os.fchmod(descriptor, 0o600)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("failed to write hook failure record")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.rename(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory)
        raise
