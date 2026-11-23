from __future__ import annotations

import json
from pathlib import Path

import pytest

from fmind_dot.config import Config, PullConfig, TrustConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult
from fmind_dot.trust import (
    agy_installed,
    github_owner,
    register_agy_projects,
    run_trust,
    trust_folders,
)
from tests.fakes import ScriptedRunner, buf, make_state


def _harness_home(home: Path) -> None:
    (home / ".gemini/antigravity-cli").mkdir(parents=True)
    (home / ".gemini/antigravity-cli/settings.json").write_text(json.dumps({"editorMode": "vim"}))
    for p in home.rglob("*"):
        if p.is_file():
            p.chmod(0o600)


def test_trust_folders_agy_and_idempotency(tmp_path: Path) -> None:
    _harness_home(tmp_path)
    repo, notes = tmp_path / "work/repo", tmp_path / "work/notes"
    (repo / ".git").mkdir(parents=True)
    notes.mkdir()

    changed = trust_folders([repo, notes], home=tmp_path)
    assert changed == [repo, notes]
    assert trust_folders([repo, notes], home=tmp_path) == []

    assert json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())["trustedWorkspaces"] == [
        str(repo),
        str(notes),
    ]
    assert (tmp_path / ".gemini/antigravity-cli/settings.json").stat().st_mode & 0o777 == 0o600


def test_register_agy_projects(tmp_path: Path) -> None:
    home = tmp_path.resolve()
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

    # Distinct repos whose normalized slugs collide both register with deterministic disambiguation.
    dash, under = home / "work/my-repo", home / "work/my_repo"
    (dash / ".git").mkdir(parents=True)
    (under / ".git").mkdir(parents=True)
    assert register_agy_projects([dash, under], ["~/work/*"], home=home) == [dash, under]
    assert (reg / "local-work-my-repo.json").is_file()
    extra = list(reg.glob("local-work-my-repo-*.json"))
    assert len(extra) == 1
    assert json.loads(extra[0].read_text())["projectResources"]["resources"][0]["folderUri"] == under.as_uri()
    assert register_agy_projects([dash, under], ["~/work/*"], home=home) == []


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://github.com/fmind/dot/", "fmind"),
        ("https://user@github.com:443/Fmind/dot", "Fmind"),
        ("ssh://git@github.com:22/fmind/dot", "fmind"),
        ("git@github.com:fmind/dot", "fmind"),
        ("https://gitlab.com/fmind/dot", None),
        ("https://evil.example?@github.com/fmind/dot", None),
        ("https://evil.example#@github.com/fmind/dot", None),
        ("https://evil.example\\@github.com/fmind/dot", None),
        ("ssh://evil.example?@github.com/fmind/dot", None),
        ("https://user:" + "fixture@github.com/fmind/dot", None),
        ("https://github.com:8443/fmind/dot", None),
        ("https://github.com:bad/fmind/dot", None),
        ("https://[bad/fmind/dot", None),
        ("https://github.com/fmind/dot?ref=main", None),
        ("evil?@github.com:fmind/dot", None),
        ("https://attacker.example@extra@github.com/fmind/dot", None),
        ("ssh://user@attacker.example@github.com/fmind/dot", None),
        ("https://@github.com/fmind/dot", None),
        ("https://github.com:/fmind/dot", None),
        ("https://github.com:0443/fmind/dot", None),
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
    assert f"+ {plain}: trusted in" in out
    assert f"+ {ws}: trusted in" not in out
    assert f"+ {owned}: trusted in" in out
    assert f"- {foreign}: skipped" in out
    agy = json.loads((home / ".gemini/antigravity-cli/settings.json").read_text())
    assert str(ws) not in agy["trustedWorkspaces"]
    assert str(owned) in agy["trustedWorkspaces"]
    assert str(foreign) not in agy["trustedWorkspaces"]

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

    (home / ".gemini").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DotError, match="refusing symlinked"):
        agy_installed(home)
    (home / ".gemini").unlink()

    agy_dir = home / ".gemini/antigravity-cli"
    agy_dir.mkdir(parents=True)
    agy_settings = agy_dir / "settings.json"
    agy_settings.symlink_to(outside / "s.json")
    with pytest.raises(DotError, match="refusing symlinked trust file"):
        trust_folders([tmp_path], home=home)
    agy_settings.unlink()

    agy_settings.write_bytes(b"\xff")
    with pytest.raises(DotError, match="not valid UTF-8"):
        trust_folders([tmp_path], home=home)

    agy_settings.write_text("[]")
    with pytest.raises(DotError, match="must contain a JSON object"):
        trust_folders([tmp_path], home=home)

    agy_settings.write_text('{"trustedWorkspaces": {}}')
    with pytest.raises(DotError, match="trustedWorkspaces must be a JSON array"):
        trust_folders([tmp_path], home=home)

    # Corrupt settings.json must fail before creating Remote Control project entries.
    reg = home / ".gemini/config/projects"
    reg.mkdir(parents=True)
    repo = home / "work/repo"
    (repo / ".git").mkdir(parents=True)
    cfg = Config(trust=TrustConfig(github_owners=["fmind"], agy_projects=["~/work/*"]))
    with pytest.raises(DotError, match="trustedWorkspaces must be a JSON array"):
        run_trust(make_state(config=cfg), [str(repo)])
    assert list(reg.glob("*.json")) == []
