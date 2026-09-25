from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dot_tasks.mise_locks import bundle, capture


def _lock(root: Path, version: str = "1.0", backend: str = "uv") -> Path:
    directory = root / "locks" / "example" / version
    directory.mkdir(parents=True)
    manifest, lockfile = ("pyproject.toml", "uv.lock") if backend == "uv" else ("package.json", "aube-lock.yaml")
    (directory / manifest).write_text("# Generated manifest\n")
    content = b"# Generated lock\n"
    (directory / lockfile).write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    lock = root / "mise.lock"
    lock.write_text(
        f'lockfile_version = 2\n[[tools.example]]\nversion = "{version}"\n'
        f'{backend} = {{ path = "locks/example/{version}", digest = "sha256:{digest}" }}\n'
    )
    return lock


def test_capture_updates_graphs_and_retires_only_previous_references(tmp_path: Path) -> None:
    source = _lock(tmp_path / "live", "2.0", "aube")
    destination = _lock(tmp_path / "managed")
    personal = destination.parent / "locks/personal.txt"
    personal.write_text("keep")

    capture(source, destination)
    assert bundle(destination) == bundle(source)
    assert not list(destination.parent.glob(".mise-lock-capture-*"))
    assert not (destination.parent / "locks/example/1.0").exists()
    assert personal.read_text() == "keep"
    capture(source, destination)
    assert bundle(destination) == bundle(source)


@pytest.mark.parametrize("failure", ["missing", "digest", "escape", "symlink"])
def test_capture_rejects_invalid_graph_before_writing(tmp_path: Path, failure: str) -> None:
    source = _lock(tmp_path / "live")
    destination = _lock(tmp_path / "managed", "0.9")
    before = bundle(destination)
    graph = source.parent / "locks/example/1.0/uv.lock"
    if failure == "missing":
        graph.unlink()
    elif failure == "digest":
        graph.write_text("corrupted")
    elif failure == "escape":
        source.write_text(source.read_text().replace("locks/example/1.0", "../outside"))
    else:
        graph.rename(tmp_path / "outside")
        graph.symlink_to(tmp_path / "outside")

    with pytest.raises((OSError, ValueError)):
        capture(source, destination)
    assert bundle(destination) == before


def test_capture_refuses_destination_symlinks(tmp_path: Path) -> None:
    source = _lock(tmp_path / "live")
    managed = tmp_path / "managed"
    managed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (managed / "locks").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        capture(source, managed / "mise.lock")
    assert not list(outside.iterdir())


def test_capture_accepts_crlf_hash_normalization(tmp_path: Path) -> None:
    source = _lock(tmp_path / "live")
    graph = source.parent / "locks/example/1.0/uv.lock"
    graph.write_bytes(graph.read_bytes().replace(b"\n", b"\r\n"))
    destination = _lock(tmp_path / "managed", "0.9")
    capture(source, destination)
    assert bundle(destination) == bundle(source)


@pytest.mark.parametrize(
    "body",
    ["tools = []", '[tools]\nexample = "invalid"', '[[tools.example]]\nuv = "invalid"'],
)
def test_bundle_rejects_malformed_structure(tmp_path: Path, body: str) -> None:
    lock = tmp_path / "mise.lock"
    lock.write_text("lockfile_version = 2\n" + body)
    with pytest.raises(ValueError, match=r"table|references"):
        bundle(lock)


def test_capture_migrates_legacy_destination_but_rejects_downgrade(tmp_path: Path) -> None:
    source = _lock(tmp_path / "live")
    destination = tmp_path / "mise.lock"
    legacy = b"lockfile_version = 1\n[tools]\n"
    destination.write_bytes(legacy)
    capture(source, destination)
    before = bundle(destination)
    source.write_bytes(legacy)
    with pytest.raises(ValueError, match="Upgrade"):
        capture(source, destination)
    assert bundle(destination) == before


@pytest.mark.parametrize("damage", ["missing", "digest"])
def test_capture_repairs_damaged_destination(tmp_path: Path, damage: str) -> None:
    source = _lock(tmp_path / "live")
    destination = _lock(tmp_path / "managed")
    graph = destination.parent / "locks/example/1.0/uv.lock"
    if damage == "missing":
        graph.unlink()
    else:
        graph.write_text("damaged\n")
    capture(source, destination)
    assert bundle(destination) == bundle(source)


@pytest.mark.parametrize("new_version", ["1.0", "2.0"])
@pytest.mark.parametrize("interrupt", [False, True])
def test_capture_rolls_back_if_publication_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, new_version: str, interrupt: bool
) -> None:
    source = _lock(tmp_path / "live", new_version)
    destination = _lock(tmp_path / "managed")
    graph = source.parent / f"locks/example/{new_version}/uv.lock"
    graph.write_bytes(b"# Updated dependency graph\n")
    source.write_text(
        source.read_text().replace(
            hashlib.sha256(b"# Generated lock\n").hexdigest(), hashlib.sha256(graph.read_bytes()).hexdigest()
        )
    )
    before = bundle(destination)
    replace = Path.replace

    def fail_publication(path: Path, target: Path) -> Path:
        if interrupt and path.name == "uv.lock" and "previous" not in path.parts:
            replace(path, target)
            raise KeyboardInterrupt
        if not interrupt and target == destination and "previous" not in path.parts:
            raise OSError("simulated publication failure")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_publication)
    with pytest.raises(KeyboardInterrupt if interrupt else OSError):
        capture(source, destination)
    assert bundle(destination) == before
    if new_version != "1.0":
        assert not (destination.parent / graph.relative_to(source.parent)).exists()
    assert not list(destination.parent.glob(".mise-lock-capture-*"))


def test_capture_preserves_recovery_files_when_rollback_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _lock(tmp_path / "live")
    destination = _lock(tmp_path / "managed")
    relative = Path("locks/example/1.0/uv.lock")
    graph = source.parent / relative
    graph.write_bytes(b"# Updated dependency graph\n")
    source.write_text(
        source.read_text().replace(
            hashlib.sha256(b"# Generated lock\n").hexdigest(), hashlib.sha256(graph.read_bytes()).hexdigest()
        )
    )
    before = bundle(destination)
    replace = Path.replace

    def fail_publication_and_rollback(path: Path, target: Path) -> Path:
        if "previous" in path.parts and path.name == "uv.lock":
            raise PermissionError("simulated rollback failure")
        if "previous" not in path.parts and target == destination:
            raise OSError("simulated publication failure")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_publication_and_rollback)
    with pytest.raises(OSError, match="recovery files retained") as failure:
        capture(source, destination)

    (recovery,) = destination.parent.glob(".mise-lock-capture-*")
    backups = recovery / "previous"
    assert str(backups) in str(failure.value)
    assert str(destination.parent) in str(failure.value)
    assert (backups / relative).read_bytes() == before[relative]
    # The reported recovery location contains the bytes needed to repair the bundle.
    for backup in backups.rglob("*"):
        if backup.is_file():
            replace(backup, destination.parent / backup.relative_to(backups))
    assert bundle(destination) == before
