from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dot_tasks.mise_locks import bundle, capture, retire, retire_installs


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
    "linked", ["locks", "locks/example", "locks/example/2.0", "locks/example/2.0/uv.lock", "mise.lock"]
)
def test_capture_rejects_destination_symlinks_before_any_writes(tmp_path: Path, linked: str) -> None:
    source = _lock(tmp_path / "live", "2.0")
    # Capture writes graphs in lock order: this valid graph precedes the unsafe one; neither may be written.
    early = source.parent / "locks/aaa/1.0"
    early.mkdir(parents=True)
    (early / "pyproject.toml").write_text("# Generated manifest\n")
    content = b"# Generated lock\n"
    (early / "uv.lock").write_bytes(content)
    aaa = f'[[tools.aaa]]\nuv = {{ path = "locks/aaa/1.0", digest = "sha256:{hashlib.sha256(content).hexdigest()}" }}\n'
    source.write_text(source.read_text().replace("[[tools.example]]", aaa + "[[tools.example]]", 1))
    assert list(bundle(source))[1] == Path("locks/aaa/1.0/pyproject.toml")  # mise.lock is written last.
    destination = tmp_path / "managed/mise.lock"
    destination.parent.mkdir()
    previous = b"lockfile_version = 3\n[tools]\n"
    destination.write_bytes(previous)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "uv.lock").write_text("preserve personal graph\n")
    (outside / "mise.lock").write_bytes(previous)
    before = {path.name: path.read_bytes() for path in outside.iterdir()}
    target = destination.parent / linked
    target.parent.mkdir(parents=True, exist_ok=True)
    if linked == "mise.lock":
        target.unlink()
    target.symlink_to(outside / target.name if target.suffix == ".lock" else outside)

    with pytest.raises(ValueError, match="symlinks"):
        capture(source, destination)

    assert destination.read_bytes() == previous
    assert {path.name: path.read_bytes() for path in outside.iterdir()} == before
    assert not (destination.parent / "locks/aaa/1.0").exists()


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
    nested = tmp_path / "locks/mise.local/pipx-example/1.0"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text("# Generated manifest\n")
    (nested / "uv.lock").write_text("old")
    personal = tmp_path / "locks/personal/0.1"
    personal.mkdir(parents=True)
    (personal / "notes.txt").write_text("keep")
    (tmp_path / "locks/personal.txt").write_text("keep")

    assert retire(lock) == [
        Path("locks/example/1.0"),
        Path("locks/mise.local/pipx-example/1.0"),
        Path("locks/removed/0.1"),
    ]
    assert not stale.exists()
    assert not (tmp_path / "locks/mise.local").exists()
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


def _uv_install(tool_dir: Path, name: str, lock_bytes: bytes, python_path: Path) -> Path:
    install = tool_dir / name
    metadata = install / ".mise-uv"
    metadata.mkdir(parents=True)
    (metadata / "uv.lock").write_bytes(lock_bytes)
    (metadata / "python.json").write_text(json.dumps([str(python_path), f"core:python:{python_path}"]))
    return install


def test_retire_installs_removes_superseded_graphs_and_repoints_dangling_symlinks(tmp_path: Path) -> None:
    lock = _lock(tmp_path, "1.0")
    current_bytes = (tmp_path / "locks/example/1.0/uv.lock").read_bytes()
    aube_dir = tmp_path / "locks/npm-cli/2.0"
    aube_dir.mkdir(parents=True)
    aube_bytes = b"lockfileVersion: 9\n"
    (aube_dir / "package.json").write_text("{}\n")
    (aube_dir / "aube-lock.yaml").write_bytes(aube_bytes)
    aube_digest = hashlib.sha256(aube_bytes).hexdigest()
    lock.write_text(
        lock.read_text()
        + '[[tools."npm:cli"]]\nversion = "2.0"\n'
        + f'aube = {{ path = "locks/npm-cli/2.0", digest = "sha256:{aube_digest}" }}\n'
    )

    py_current = tmp_path / "python-3.14.9"
    py_current.write_text("binary")
    py_project = tmp_path / "python-3.14.8"
    py_project.write_text("binary")
    py_removed = tmp_path / "python-3.14.7"

    installs = tmp_path / "installs"
    uv_tool = installs / "example"
    keep_global = _uv_install(uv_tool, "1.0~uv~globalhash", current_bytes, py_current)
    keep_project = _uv_install(uv_tool, "1.0~uv~projecthash", current_bytes, py_project)
    stale_graph = _uv_install(uv_tool, "1.0~uv~oldgraph", b"old lock\n", py_current)
    stale_python = _uv_install(uv_tool, "1.0~uv~oldpython", current_bytes, py_removed)
    project_version = _uv_install(uv_tool, "0.8.0~uv~projectpin", b"project lock\n", py_current)
    plain_version = uv_tool / "0.9.0"
    plain_version.mkdir()
    (uv_tool / "global").symlink_to("./1.0~uv~globalhash")
    (uv_tool / "latest").symlink_to("./1.0~uv~oldgraph")
    (uv_tool / "1").symlink_to("./1.0~uv~oldpython")
    (uv_tool / "0.9").symlink_to("./0.9.0")

    aube_tool = installs / "npm-cli"
    keep_aube = aube_tool / "2.0~aube~currenthash"
    keep_aube.mkdir(parents=True)
    (keep_aube / "aube-lock.yaml").write_bytes(aube_bytes)
    stale_aube = aube_tool / "2.0~aube~oldhash"
    stale_aube.mkdir(parents=True)
    (stale_aube / "aube-lock.yaml").write_bytes(b"old aube\n")

    assert retire_installs(lock, installs) == [stale_graph, stale_python, stale_aube]
    assert keep_global.is_dir()
    assert keep_project.is_dir()
    assert plain_version.is_dir()
    assert project_version.is_dir()
    assert keep_aube.is_dir()
    assert not stale_graph.exists()
    assert not stale_python.exists()
    assert not stale_aube.exists()
    assert (uv_tool / "latest").readlink() == Path("./1.0~uv~globalhash")
    assert (uv_tool / "1").readlink() == Path("./1.0~uv~globalhash")
    assert (uv_tool / "0.9").readlink() == Path("./0.9.0")
    assert retire_installs(lock, installs) == []
