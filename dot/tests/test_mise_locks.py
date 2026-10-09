from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dot_tasks.mise_locks import bundle, capture, retire


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
        f'lockfile_version = 3\n[[tools.example]]\nversion = "{version}"\n'
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
    lock.write_text("lockfile_version = 3\n" + body)
    with pytest.raises(ValueError, match=r"table|references"):
        bundle(lock)


def test_capture_rejects_another_lock_revision(tmp_path: Path) -> None:
    source = _lock(tmp_path / "live")
    destination = _lock(tmp_path / "managed")
    before = bundle(destination)
    source.write_bytes(b"lockfile_version = 2\n[tools]\n")
    with pytest.raises(ValueError, match="expected revision 3"):
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


def test_retire_removes_only_unreferenced_generated_graphs(tmp_path: Path) -> None:
    lock = _lock(tmp_path, "2.0")
    stale = tmp_path / "locks/example/1.0"
    stale.mkdir()
    (stale / "uv.lock").write_text("old")
    retired_tool = tmp_path / "locks/removed/0.1"
    retired_tool.mkdir(parents=True)
    (retired_tool / "package.json").write_text("{}")
    personal = tmp_path / "locks/personal/0.1"
    personal.mkdir(parents=True)
    (personal / "notes.txt").write_text("keep")
    (tmp_path / "locks/personal.txt").write_text("keep")

    assert retire(lock) == [Path("locks/example/1.0"), Path("locks/removed/0.1")]
    assert not stale.exists()
    assert not retired_tool.parent.exists()
    assert (personal / "notes.txt").read_text() == "keep"
    assert (tmp_path / "locks/personal.txt").read_text() == "keep"
    assert bundle(lock)
    assert retire(lock) == []


@pytest.mark.parametrize("linked", ["locks", "locks/personal", "locks/personal/1.0"])
def test_retire_preserves_graphs_under_symlinked_directories(tmp_path: Path, linked: str) -> None:
    deployed = tmp_path / "deployed"
    deployed.mkdir()
    lock = deployed / "mise.lock"
    lock.write_text("lockfile_version = 3\n[tools]\n")
    target = deployed / linked
    target.parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    target.symlink_to(outside, target_is_directory=True)
    graph = deployed / "locks/personal/1.0/uv.lock"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text("keep")

    assert retire(lock) == []
    assert target.is_symlink()
    assert graph.read_text() == "keep"
