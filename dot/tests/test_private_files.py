"""Publication failures preserve the previous file and leave no temporary data."""

import os
import stat
from pathlib import Path

import pytest

from fmind_dot.private_files import write_atomic_file, write_private_file


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
