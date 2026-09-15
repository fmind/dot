"""Exercise local project registration without touching the real home or daemon."""

import json
import runpy
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
indexer = runpy.run_path(str(ROOT / "skills/agy/scripts/index-repositories.py"))
refresh = indexer["refresh"]


def repository(path: Path, remote: str) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", remote], check=True)


def test_index_is_local_additive_and_repeatable(tmp_path: Path) -> None:
    home = tmp_path / "home"
    repository(home / "owner/one", "git@github.com:owner/one.git")
    repository(home / "owner/two", "https://github.com/owner/two.git")
    repository(home / "elsewhere", "https://gitlab.com/owner/repo.git")
    repository(home / ".cache/hidden", "https://github.com/owner/cache.git")
    repository(home / "node_modules/dependency", "https://github.com/owner/dependency.git")
    repository(home / "owner/project/modules/nested", "https://github.com/owner/nested.git")
    (home / "alias").symlink_to(home / "owner", target_is_directory=True)
    registry = tmp_path / "projects"
    registry.mkdir()
    existing = registry / "custom.json"
    original = json.dumps(
        {
            "id": "custom",
            "name": "My name",
            "settings": {"sandboxMode": True},
            "projectResources": {"resources": [{"gitFolder": {"folderUri": (home / "owner/one").as_uri()}}]},
        }
    )
    existing.write_text(original)
    assert refresh([home], registry, False) == (2, 1)
    assert list(registry.iterdir()) == [existing]
    assert refresh([home, home / "owner"], registry, True) == (2, 1)
    assert refresh([home], registry, True) == (2, 0)
    assert existing.read_text() == original
    added = next(registry.glob("local-*.json"))
    assert added.stat().st_mode & 0o777 == 0o600
    assert json.loads(added.read_text())["projectResources"]["resources"] == [
        {"folderUri": (home / "owner/two").as_uri()}
    ]


def test_invalid_registry_fails_before_writing(tmp_path: Path) -> None:
    repository(tmp_path / "repo", "git@github.com:owner/repo.git")
    registry = tmp_path / "projects"
    registry.mkdir()
    (registry / "broken.json").write_text("{")
    with pytest.raises(indexer["IndexingError"], match="Invalid project JSON") as failure:
        refresh([tmp_path / "repo"], registry, True)
    assert isinstance(failure.value.__cause__, json.JSONDecodeError)
    assert len(list(registry.iterdir())) == 1


@pytest.mark.parametrize(
    ("failure", "diagnostic"),
    [
        ("root", "Cannot resolve scan roots"),
        ("json", "Invalid project JSON"),
        ("scan", "Cannot scan repositories"),
        ("git", "Git remote lookup timed out after 10 seconds"),
        ("write", "Cannot write the project registry"),
    ],
)
def test_cli_errors_are_actionable_and_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str, diagnostic: str
) -> None:
    repo = tmp_path / "private-repository"
    repository(repo, "https://github.com/private-owner/private-repository.git")
    registry = tmp_path / ".gemini/config/projects"
    registry.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr("sys.argv", ["index-repositories.py", str(repo), "--apply"])
    if failure == "root":
        monkeypatch.setattr("sys.argv", ["index-repositories.py", str(repo / "missing")])
    elif failure == "json":
        (registry / "private-project.json").write_text("{private-content")
    elif failure == "scan":

        def fail_walk(_self: Path, *, on_error: Callable[[OSError], None]) -> None:
            on_error(PermissionError("private-path"))

        monkeypatch.setattr(Path, "walk", fail_walk)
    elif failure == "git":

        def fail_git(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired("private-command", 10, stderr="private-output")

        monkeypatch.setattr(subprocess, "run", fail_git)
    elif failure == "write":

        def fail_open(*_args: object, **_kwargs: object) -> None:
            raise PermissionError("private-path")

        monkeypatch.setattr("os.open", fail_open)
    assert indexer["main"]() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert diagnostic in output.err
    assert "private" not in output.err
    assert str(tmp_path) not in output.err
    assert "Traceback" not in output.err
