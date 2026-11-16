from __future__ import annotations

import json
from pathlib import Path

import pytest

from fmind_dot.config import Config, PullConfig, TrustConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult
from fmind_dot.trust import (
    github_owner,
    installed_harnesses,
    register_agy_projects,
    register_claude_directories,
    run_trust,
    trust_folders,
)
from tests.fakes import ScriptedRunner, buf, make_state


def _harness_home(home: Path) -> None:
    for d in (".claude", ".gemini/antigravity-cli", ".pi/agent"):
        (home / d).mkdir(parents=True)
    (home / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"id": "k"}, "projects": {"/other": {"hasTrustDialogAccepted": False}}})
    )
    (home / ".gemini/antigravity-cli/settings.json").write_text(json.dumps({"editorMode": "vim"}))
    for p in home.rglob("*"):
        if p.is_file():
            p.chmod(0o600)


def test_trust_folders_all_harnesses_and_pi_git_only(tmp_path: Path) -> None:
    _harness_home(tmp_path)
    repo, notes = tmp_path / "work/repo", tmp_path / "work/notes"
    (repo / ".git").mkdir(parents=True)
    notes.mkdir()
    pi_store = tmp_path / ".pi/agent/trust.json"
    pi_store.write_text(json.dumps({"/else": False, str(repo): False}))

    changed = trust_folders([repo, notes], home=tmp_path)
    assert changed == {repo: ["claude", "agy", "pi"], notes: ["claude", "agy"]}
    assert trust_folders([repo, notes], home=tmp_path) == {repo: [], notes: []}

    assert json.loads((tmp_path / ".claude.json").read_text())["oauthAccount"] == {"id": "k"}
    assert json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())["trustedWorkspaces"] == [
        str(repo),
        str(notes),
    ]
    assert json.loads(pi_store.read_text()) == {"/else": False, str(repo): True}
    assert (tmp_path / ".gemini/antigravity-cli/settings.json").stat().st_mode & 0o777 == 0o600


def test_register_claude_directories_and_agy_projects(tmp_path: Path) -> None:
    home = tmp_path.resolve()
    (home / ".claude").mkdir()
    (home / ".agents").mkdir()
    ws = home / "work"
    sub = ws / "proj"
    (sub / ".git").mkdir(parents=True)
    added = register_claude_directories([ws, sub], home=home)
    assert added == [home / ".agents", ws]
    assert register_claude_directories([ws, sub], home=home) == []

    for bad, match in (
        ('{"permissions": "x"}', "permissions must"),
        ('{"permissions": {"additionalDirectories": [1]}}', "array of strings"),
    ):
        (home / ".claude/settings.json").write_text(bad)
        with pytest.raises(DotError, match=match):
            register_claude_directories([ws], home=home)

    reg = home / ".gemini/config/projects"
    reg.mkdir(parents=True)
    chezmoi, existing = home / ".local/share/chezmoi", home / "work/existing"
    (chezmoi / ".git").mkdir(parents=True)
    (existing / ".git").mkdir(parents=True)
    (reg / "other.json").write_text(
        json.dumps({"projectResources": {"resources": [{"gitFolder": {"folderUri": existing.as_uri()}}]}})
    )
    assert register_agy_projects([chezmoi, existing], ["~/.local/share/chezmoi", "~/work/*"], home=home) == [chezmoi]
    payload = json.loads((reg / "local-fmind-dot.json").read_text())
    assert payload["name"] == "fmind/dot"
    assert payload["projectResources"]["resources"][0]["folderUri"] == chezmoi.as_uri()
    assert register_agy_projects([chezmoi], ["~/.local/share/chezmoi"], home=home) == []


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://github.com/fmind/dot/", "fmind"),
        ("https://user@github.com:443/Fmind/dot", "Fmind"),
        ("ssh://git@github.com:22/fmind/dot", "fmind"),
        ("git@github.com:fmind/dot", "fmind"),
        ("https://gitlab.com/fmind/dot", None),
    ],
)
def test_github_owner_parses_urls(origin: str, expected: str | None) -> None:
    assert github_owner(origin) == expected


def test_run_trust_explicit_all_and_empty_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, plain = tmp_path / "home", tmp_path / "plain"
    home.mkdir()
    plain.mkdir()
    monkeypatch.setenv("HOME", str(home))
    state = make_state()
    run_trust(state, [str(plain)])
    assert "No agent harness state found" in buf(state.stdout)

    _harness_home(home)
    ws = home / "work"
    owned, foreign = ws / "owned", ws / "foreign"
    (owned / ".git").mkdir(parents=True)
    (foreign / ".git").mkdir(parents=True)
    (home / ".local/share/chezmoi/.git").mkdir(parents=True)
    runner = ScriptedRunner(
        {"git"},
        run=lambda cmd, cwd, _i, _c: (
            CommandResult("https://github.com/fmind/r\n" if cwd == owned else "https://github.com/other/r\n", "", 0)
            if cmd[:3] == ["git", "remote", "get-url"]
            else CommandResult(str(cwd or ws) + "\n", "", 0)
        ),
    )
    cfg = Config(
        pull=PullConfig(directories=[str(ws)]),
        trust=TrustConfig(github_owners=["fmind"], agy_projects=["~/.local/share/chezmoi"]),
    )
    st = make_state(runner, cfg)
    run_trust(st, [str(plain), "all"])
    out = buf(st.stdout)
    assert f"+ {ws}: trusted in" in out
    assert f"+ {owned}: trusted in" in out
    assert f"- {foreign}: skipped" in out
    assert "Copilot" not in out

    st2 = make_state(runner, cfg)
    run_trust(st2, ["all"])
    assert "✓ " in buf(st2.stdout)


def test_trust_rejects_home_ancestors_symlinks_and_corrupt_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, outside = tmp_path / "home", tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    monkeypatch.setenv("HOME", str(home))
    for bad in (home, home.parent):
        with pytest.raises(DotError, match="contains the home directory"):
            run_trust(make_state(), [str(bad)])
    with pytest.raises(DotError, match="not a directory"):
        run_trust(make_state(), [str(tmp_path / "missing")])

    (home / ".claude").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DotError, match="refusing symlinked"):
        installed_harnesses(home)
    (home / ".claude").unlink()

    (home / ".claude").mkdir()
    (home / ".claude.json").symlink_to(outside / "s.json")
    with pytest.raises(DotError, match="refusing symlinked trust file"):
        trust_folders([tmp_path], home=home)
    (home / ".claude.json").unlink()

    (home / ".claude.json").write_bytes(b"\xff")
    with pytest.raises(DotError, match="not valid UTF-8"):
        trust_folders([tmp_path], home=home)

    (home / ".claude.json").write_text("[]")
    with pytest.raises(DotError, match="must contain a JSON object"):
        trust_folders([tmp_path], home=home)

    (home / ".claude.json").write_text('{"projects": []}')
    with pytest.raises(DotError, match="projects must be a JSON object"):
        trust_folders([tmp_path], home=home)
