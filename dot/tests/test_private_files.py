"""Publication failures preserve the previous file and leave no temporary data."""

import os
import stat
from pathlib import Path

import pytest

from fmind_dot.private_files import private_directory, write_atomic_file, write_private_file


def test_private_directory_and_atomic_write_refuse_symlinks(tmp_path: Path) -> None:
    real_dir = tmp_path / "real-dir"
    real_dir.mkdir()
    real_dir.chmod(0o755)
    linked_dir = tmp_path / "linked-dir"
    linked_dir.symlink_to(real_dir)
    with pytest.raises(OSError, match="refusing symlinked private directory"):
        private_directory(linked_dir)
    assert stat.S_IMODE(real_dir.stat().st_mode) == 0o755

    real_file = tmp_path / "real-file"
    real_file.write_bytes(b"keep")
    linked_file = tmp_path / "linked-file"
    linked_file.symlink_to(real_file)
    with pytest.raises(OSError, match="refusing to overwrite symlink"):
        write_atomic_file(linked_file, b"clobber", mode=0o600)
    assert real_file.read_bytes() == b"keep"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["linked-dir", "linked-file", "real-dir", "real-file"]


@pytest.mark.parametrize("mode", [0o600, 0o640, 0o644])
def test_atomic_write_publishes_complete_content_with_explicit_permissions(tmp_path: Path, mode: int) -> None:
    target = tmp_path / "settings"
    target.write_bytes(b"old")
    write_atomic_file(target, "new: café\n".encode(), mode=mode)
    assert target.read_bytes() == "new: café\n".encode()
    assert stat.S_IMODE(target.stat().st_mode) == mode
    assert list(tmp_path.iterdir()) == [target]
    write_private_file(target, b"private")
    assert target.read_bytes() == b"private"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


@pytest.mark.parametrize("stage", ["permissions", "sync", "replace"])
def test_atomic_write_failure_preserves_existing_file_and_removes_temporary_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    target = tmp_path / "settings"
    target.write_bytes(b"old")
    target.chmod(0o640)

    def fail(*_args: object) -> None:
        raise OSError("publication failed")

    if stage == "replace":
        monkeypatch.setattr(Path, "replace", fail)
    else:
        monkeypatch.setattr(os, "fchmod" if stage == "permissions" else "fsync", fail)
    with pytest.raises(OSError, match="publication failed"):
        write_private_file(target, b"new")
    assert target.read_bytes() == b"old"
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_syncs_parent_directory_with_nofollow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "secret"
    real_open = os.open
    seen_flags: list[int] = []

    def tracking_open(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], flags: int, *args: int) -> int:
        if path == tmp_path:
            seen_flags.append(flags)
        return real_open(path, flags, *args)

    monkeypatch.setattr(os, "open", tracking_open)
    write_private_file(target, b"ok")
    required = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    assert seen_flags
    assert all((flags & required) == required for flags in seen_flags)
    assert target.read_bytes() == b"ok"

    # Directory sync failure must not prevent publication once replace() succeeded.
    def deny_dir_open(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], flags: int, *args: int) -> int:
        if path == tmp_path:
            raise OSError("symlinked parent dir")
        return real_open(path, flags, *args)

    monkeypatch.setattr(os, "open", deny_dir_open)
    write_private_file(target, b"updated")
    assert target.read_bytes() == b"updated"
