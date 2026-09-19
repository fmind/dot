"""Owner-only directories and atomically replaced files."""

import os
import tempfile
from pathlib import Path


def private_directory(path: Path) -> Path:
    """Create a directory if needed and restrict it to its owner."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def write_private_file(path: Path, content: bytes) -> None:
    """Replace a file atomically: readers see the previous or the new content, never a mix."""
    # mkstemp creates the file with 0600 in the target directory, so the replace stays atomic.
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
