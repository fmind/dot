"""Atomic file publication with explicit permissions."""

import contextlib
import os
import tempfile
from pathlib import Path


def write_atomic_file(path: Path, content: bytes, *, mode: int) -> None:
    """Replace a file atomically after writing, setting permissions, and syncing it."""
    if path.is_symlink():
        raise OSError(f"refusing to overwrite symlink: {path}")
    # mkstemp creates the file with 0600 in the target directory, so the replace stays atomic.
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        temporary.replace(path)
        with contextlib.suppress(OSError):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
