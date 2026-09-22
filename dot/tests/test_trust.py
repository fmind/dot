"""Folder trust edits every harness file in place and only ever adds entries."""

import io
import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from fmind_dot.config import Config, PullConfig
from fmind_dot.errors import DotError
from fmind_dot.state import State
from fmind_dot.trust import github_owner, run_trust, trust_folder

COPILOT_HEADER = "// User settings belong in settings.json.\n// This file is managed automatically.\n"


def harness_home(home: Path) -> None:
    for directory in (".claude", ".codex", ".grok", ".gemini/antigravity-cli", ".copilot"):
        (home / directory).mkdir(parents=True)
    claude = {"oauthAccount": {"id": "kept"}, "projects": {"/other": {"hasTrustDialogAccepted": False, "x": 1}}}
    (home / ".claude.json").write_text(json.dumps(claude))
    (home / ".codex/config.toml").write_text(
        'model = "kept"\n\n[projects]\n  [projects."/other"]\n    trust_level = "trusted"\n\n[features]\nmemories = true\n'
    )
    (home / ".grok/trusted_folders.toml").write_text('[folders."/other"]\ntrusted = true\ndecided_at = 1\n')
    (home / ".gemini/antigravity-cli/settings.json").write_text(json.dumps({"editorMode": "vim"}))
    (home / ".copilot/config.json").write_text(COPILOT_HEADER + json.dumps({"banner": "never"}))
    for path in home.rglob("*"):
        if path.is_file():
            path.chmod(0o600)


def test_trust_adds_each_harness_once_and_preserves_host_state(tmp_path: Path) -> None:
    harness_home(tmp_path)
    repository = tmp_path / "work" / "repo"
    repository.mkdir(parents=True)

    assert trust_folder(repository, dry_run=True, home=tmp_path) == ["claude", "codex", "grok", "agy", "copilot"]
    assert json.loads((tmp_path / ".claude.json").read_text())["projects"].keys() == {"/other"}

    assert trust_folder(repository, home=tmp_path) == ["claude", "codex", "grok", "agy", "copilot"]
    assert trust_folder(repository, home=tmp_path) == []

    claude = json.loads((tmp_path / ".claude.json").read_text())
    assert claude["oauthAccount"] == {"id": "kept"}
    assert claude["projects"] == {
        "/other": {"hasTrustDialogAccepted": False, "x": 1},
        str(repository): {"hasTrustDialogAccepted": True},
    }
    codex = tomllib.loads((tmp_path / ".codex/config.toml").read_text())
    assert codex["model"] == "kept"
    assert codex["features"] == {"memories": True}
    assert codex["projects"] == {"/other": {"trust_level": "trusted"}, str(repository): {"trust_level": "trusted"}}
    grok = tomllib.loads((tmp_path / ".grok/trusted_folders.toml").read_text())
    assert grok["folders"]["/other"] == {"trusted": True, "decided_at": 1}
    assert grok["folders"][str(repository)] == {"trusted": True}
    agy = json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())
    assert agy == {"editorMode": "vim", "trustedWorkspaces": [str(repository)]}
    copilot = (tmp_path / ".copilot/config.json").read_text()
    assert copilot.startswith(COPILOT_HEADER)
    assert json.loads(copilot.removeprefix(COPILOT_HEADER)) == {"banner": "never", "trustedFolders": [str(repository)]}
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in tmp_path.rglob("*") if path.is_file())


def test_trust_replaces_an_explicit_codex_refusal_in_place(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    config = tmp_path / ".codex/config.toml"
    config.write_text('[projects."/repo"]\ntrust_level = "untrusted"\n\n[features]\nmemories = true\n')

    assert trust_folder(Path("/repo"), home=tmp_path) == ["codex"]
    assert tomllib.loads(config.read_text()) == {
        "projects": {"/repo": {"trust_level": "trusted"}},
        "features": {"memories": True},
    }


def test_trust_skips_missing_harnesses_and_home_for_grok(tmp_path: Path) -> None:
    (tmp_path / ".grok").mkdir()
    (tmp_path / ".copilot").mkdir()

    assert trust_folder(tmp_path, home=tmp_path) == ["copilot"]
    assert not (tmp_path / ".grok/trusted_folders.toml").exists()
    assert not (tmp_path / ".claude.json").exists()


def test_trust_rejects_malformed_host_files_without_writing(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    config = tmp_path / ".codex/config.toml"
    config.write_text("[projects\n")

    with pytest.raises(DotError, match="not valid TOML"):
        trust_folder(Path("/repo"), home=tmp_path)
    assert config.read_text() == "[projects\n"


def test_trust_all_covers_configured_workspaces_and_their_repositories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    harness_home(tmp_path)
    workspace = tmp_path / "work"
    origins = {
        "one": "https://github.com/fmind/one.git",
        "two": "git@github.com:MLOps-Courses/two.git",
        "foreign": "https://github.com/someone-else/foreign",
        "lookalike": "https://github.com.evil.example/fmind/lookalike",
        "local": "",
    }
    for name, origin in origins.items():
        subprocess.run(["git", "init", "-q", str(workspace / name)], check=True)
        if origin:
            subprocess.run(["git", "-C", str(workspace / name), "remote", "add", "origin", origin], check=True)
    (workspace / "notes").mkdir()
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(pull=PullConfig(directories=[str(workspace), str(tmp_path / "missing")]))

    run_trust(state, "all", dry_run=True)
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue().count("skipped (origin is not a github.com repository") == 3
    assert not (tmp_path / ".gemini/antigravity-cli/settings.json").read_text().count("trustedWorkspaces")

    state.stdout = io.StringIO()
    run_trust(state, "all")

    trusted = json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())["trustedWorkspaces"]
    assert trusted == [str(workspace), str(workspace / "one"), str(workspace / "two")]
    output = state.stdout.getvalue()
    assert output.count("trusted in claude, codex, grok, agy, copilot") == 3
    for name in ("foreign", "lookalike", "local"):
        assert f"- {workspace / name}: skipped" in output

    # An explicitly named repository is trusted regardless of its origin.
    state.stdout = io.StringIO()
    run_trust(state, str(workspace / "local"))
    assert state.stdout.getvalue() == f"+ {workspace / 'local'}: trusted in claude, codex, grok, agy, copilot\n"

    state.stdout = io.StringIO()
    run_trust(state, str(workspace / "one" / "."))
    assert state.stdout.getvalue() == f"✓ {workspace / 'one'}: already trusted\n"


@pytest.mark.parametrize(
    ("origin", "owner"),
    [
        ("https://github.com/fmind/dot.git", "fmind"),
        ("https://token@GitHub.com/fmind-ai/repo", "fmind-ai"),
        ("git@github.com:MLOps-Courses/course.git", "MLOps-Courses"),
        ("ssh://git@github.com:22/fmind/dot.git\n", "fmind"),
        ("https://gitlab.com/fmind/dot.git", None),
        ("https://github.com/fmind", None),
        ("https://github.com/fmind/dot/extra", None),
        ("git@github.com.example:fmind/dot.git", None),
    ],
)
def test_github_owner_accepts_only_github_origins(origin: str, owner: str | None) -> None:
    assert github_owner(origin) == owner
