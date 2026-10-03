"""Exercise Remote Control project sync without touching the real home or daemon."""

import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/agy/scripts/sync-projects.py"
sync = runpy.run_path(str(SCRIPT))


def entry(registry: Path, name: str, *folders: Path) -> Path:
    path = registry / f"{name}.json"
    resources = [{"folderUri": folder.as_uri()} for folder in folders]
    path.write_text(json.dumps({"id": name, "name": name, "projectResources": {"resources": resources}}))
    return path


def run(home: Path, monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.setattr("sys.argv", ["sync-projects.py", *argv])
    return sync["main"]()


def test_registry_matches_glob_and_is_repeatable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    for path in ["owner/one", "owner/two", "owner/two/nested", ".cache/hidden", "shallow", "a/b/c"]:
        (home / path / ".git").mkdir(parents=True)
    (home / "alias").mkdir()
    (home / "alias/one").symlink_to(home / "owner/one", target_is_directory=True)
    registry = home / ".gemini/config/projects"
    registry.mkdir(parents=True)
    kept = entry(registry, "kept", home / "owner/one")
    native = entry(registry, "default")
    original = kept.read_text()
    stale = [
        entry(registry, "z-duplicate", home / "owner/one"),
        entry(registry, "deep", home / "a/b/c"),
        entry(registry, "gone", home / "gone"),
    ]

    assert run(home, monkeypatch) == 0
    assert all(path.exists() for path in stale)
    assert run(home, monkeypatch, "--apply") == 0
    assert run(home, monkeypatch, "--apply") == 0

    assert kept.read_text() == original
    assert native.exists()
    assert not any(path.exists() for path in stale)
    added = [json.loads(path.read_text()) for path in registry.glob("local-*.json")]
    assert [project["name"] for project in added] == ["owner/two"]
    assert added[0]["projectResources"]["resources"] == [{"folderUri": (home / "owner/two").as_uri()}]
    assert sorted(path.name for path in registry.iterdir()) == sorted(
        ["kept.json", "default.json", f"{added[0]['id']}.json"]
    )


def test_invalid_registry_fails_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "owner/repo/.git").mkdir(parents=True)
    registry = tmp_path / ".gemini/config/projects"
    registry.mkdir(parents=True)
    (registry / "broken.json").write_text("{private")
    assert run(tmp_path, monkeypatch, "--apply") == 1
    assert "private" not in capsys.readouterr().err
    assert [path.name for path in registry.iterdir()] == ["broken.json"]


def test_preview_leaves_a_missing_registry_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "owner/repo/.git").mkdir(parents=True)
    registry = tmp_path / ".gemini/config/projects"
    assert run(tmp_path, monkeypatch) == 0
    assert not registry.exists()
    assert run(tmp_path, monkeypatch, "--apply") == 0
    assert [project.name for project in registry.glob("local-*.json")]
