"""Folder trust edits every harness file in place and only ever adds entries."""

import io
import json
import subprocess
import threading
from pathlib import Path

import pytest

from fmind_dot.config import Config, PullConfig, TrustConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.trust import github_owner, register_agy_projects, run_trust, trust_folders

COPILOT_HEADER = "// User settings belong in settings.json.\n// This file is managed automatically.\n"


def trust_folder(folder: Path, *, dry_run: bool = False, home: Path | None = None) -> list[str]:
    return trust_folders([folder], dry_run=dry_run, home=home)[folder]


def harness_home(home: Path) -> None:
    for directory in (".claude", ".gemini/antigravity-cli", ".copilot"):
        (home / directory).mkdir(parents=True)
    claude = {"oauthAccount": {"id": "kept"}, "projects": {"/other": {"hasTrustDialogAccepted": False, "x": 1}}}
    (home / ".claude.json").write_text(json.dumps(claude))
    (home / ".gemini/antigravity-cli/settings.json").write_text(json.dumps({"editorMode": "vim"}))
    (home / ".copilot/config.json").write_text(COPILOT_HEADER + json.dumps({"banner": "never"}))
    for path in home.rglob("*"):
        if path.is_file():
            path.chmod(0o600)


def test_trust_adds_each_harness_once_and_preserves_host_state(tmp_path: Path) -> None:
    harness_home(tmp_path)
    repository = tmp_path / "work" / "repo"
    repository.mkdir(parents=True)

    assert trust_folder(repository, dry_run=True, home=tmp_path) == ["claude", "agy", "copilot"]
    assert json.loads((tmp_path / ".claude.json").read_text())["projects"].keys() == {"/other"}

    assert trust_folder(repository, home=tmp_path) == ["claude", "agy", "copilot"]
    assert trust_folder(repository, home=tmp_path) == []

    claude = json.loads((tmp_path / ".claude.json").read_text())
    assert claude["oauthAccount"] == {"id": "kept"}
    assert claude["projects"] == {
        "/other": {"hasTrustDialogAccepted": False, "x": 1},
        str(repository): {"hasTrustDialogAccepted": True},
    }
    agy = json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())
    assert agy == {"editorMode": "vim", "trustedWorkspaces": [str(repository)]}
    copilot = (tmp_path / ".copilot/config.json").read_text()
    assert copilot.startswith(COPILOT_HEADER)
    assert json.loads(copilot.removeprefix(COPILOT_HEADER)) == {"banner": "never", "trustedFolders": [str(repository)]}
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in tmp_path.rglob("*") if path.is_file())


def test_trust_reports_when_no_harness_has_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, folder = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    folder.mkdir()
    monkeypatch.setenv("HOME", str(home))
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())

    run_trust(state, [str(folder)])
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == "○ No agent harness state found; nothing to trust yet.\n"
    assert not any(home.iterdir())


def test_trust_skips_missing_harnesses(tmp_path: Path) -> None:
    (tmp_path / ".copilot").mkdir()

    assert trust_folder(tmp_path, home=tmp_path) == ["copilot"]
    assert not (tmp_path / ".claude.json").exists()
    assert not (tmp_path / ".gemini").exists()


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ('{"projects": {"/repo": {"private_key": "private value"}', "not valid JSON"),
        ('["private value"]', "must contain a JSON object"),
        ('{"projects": ["private value"]}', "projects must be a JSON object"),
        ('{"projects": {"/repo": "private value"}}', "project /repo must be a JSON object"),
    ],
    ids=["malformed", "not-object", "projects-list", "project-string"],
)
def test_trust_rejects_malformed_host_files_without_writing(tmp_path: Path, content: str, error: str) -> None:
    (tmp_path / ".claude").mkdir()
    config = tmp_path / ".claude.json"
    config.write_text(content)

    with pytest.raises(DotError, match=error) as caught:
        trust_folder(Path("/repo"), home=tmp_path)
    message = str(caught.value).replace(str(config), "")
    assert "private" not in message
    assert config.read_text() == content


@pytest.mark.parametrize("home_relative", [False, True])
def test_trust_all_covers_configured_workspaces_and_their_repositories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, home_relative: bool
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
        subprocess.run(["git", "init", "-q", str(workspace / name)], check=True, timeout=30)
        if origin:
            subprocess.run(
                ["git", "-C", str(workspace / name), "remote", "add", "origin", origin], check=True, timeout=30
            )
    (workspace / "notes").mkdir()
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(
        pull=PullConfig(directories=["~/work" if home_relative else str(workspace), str(tmp_path / "missing")])
    )

    run_trust(state, ["all"], dry_run=True)
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue().count("skipped (origin is not a github.com repository") == 3
    assert state.stdout.getvalue().count("Copilot still inherits workspace trust") == 3
    assert not (tmp_path / ".gemini/antigravity-cli/settings.json").read_text().count("trustedWorkspaces")

    state.stdout = io.StringIO()
    run_trust(state, ["all"])

    trusted = json.loads((tmp_path / ".gemini/antigravity-cli/settings.json").read_text())["trustedWorkspaces"]
    assert trusted == [str(workspace), str(workspace / "one"), str(workspace / "two")]
    output = state.stdout.getvalue()
    assert output.count("trusted in claude, agy, copilot") == 3
    for name in ("foreign", "lookalike", "local"):
        assert f"- {workspace / name}: skipped" in output

    # An explicitly named repository is trusted regardless of its origin.
    state.stdout = io.StringIO()
    run_trust(state, [str(workspace / "local")])
    assert state.stdout.getvalue() == f"+ {workspace / 'local'}: trusted in claude, agy, copilot\n"

    state.stdout = io.StringIO()
    run_trust(state, [str(workspace / "one" / ".")])
    assert state.stdout.getvalue() == f"✓ {workspace / 'one'}: already trusted\n"

    # One call merges targets: a repository named alongside "all" is trusted, not reported as skipped.
    state.stdout = io.StringIO()
    run_trust(state, ["all", str(workspace / "local")], dry_run=True)
    output = state.stdout.getvalue()
    assert f"✓ {workspace / 'local'}: already trusted" in output
    assert f"- {workspace / 'local'}: skipped" not in output
    assert f"- {workspace / 'foreign'}: skipped" in output


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


def test_trust_all_writes_each_harness_file_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fmind_dot import trust

    harness_home(tmp_path)
    workspace = tmp_path / "work"
    for name in ("one", "two"):
        subprocess.run(["git", "init", "-q", str(workspace / name)], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(workspace / name), "remote", "add", "origin", f"https://github.com/fmind/{name}"],
            check=True,
            timeout=30,
        )
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(pull=PullConfig(directories=[str(workspace)]))
    written: list[Path] = []
    write = trust.write_atomic_file

    def counting(path: Path, content: bytes, *, mode: int) -> None:
        written.append(path)
        write(path, content, mode=mode)

    monkeypatch.setattr(trust, "write_atomic_file", counting)

    run_trust(state, ["all"])

    # Three folders, one read-modify-write per harness file.
    assert sorted(path.name for path in written) == [
        ".claude.json",
        "config.json",
        "settings.json",
    ]
    projects = json.loads((tmp_path / ".claude.json").read_text())["projects"]
    assert {str(workspace), str(workspace / "one"), str(workspace / "two")} <= projects.keys()


def test_trust_rereads_a_file_the_host_changed_before_replacing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fmind_dot import trust

    harness_home(tmp_path)
    repository = tmp_path / "repo"
    repository.mkdir()
    load = trust._load_json  # noqa: SLF001 - inject a host write between read and replacement
    raced: list[Path] = []

    def concurrent_host(path: Path, text: str) -> dict:
        value = load(path, text)
        if path.name == ".claude.json" and not raced:
            # Claude Code writes its own state between this read and the replacement.
            raced.append(path)
            path.write_text(json.dumps(json.loads(path.read_text()) | {"numStartups": 7}))
        return value

    monkeypatch.setattr(trust, "_load_json", concurrent_host)

    assert "claude" in trust_folder(repository, home=tmp_path)

    claude = json.loads((tmp_path / ".claude.json").read_text())
    assert claude["numStartups"] == 7
    assert claude["projects"][str(repository)] == {"hasTrustDialogAccepted": True}


def test_trust_stops_when_a_host_keeps_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fmind_dot import trust

    harness_home(tmp_path)
    load = trust._load_json  # noqa: SLF001 - inject a host write between read and replacement
    writes = iter(range(100))

    def busy_host(path: Path, text: str) -> dict:
        value = load(path, text)
        if path.name == ".claude.json":
            path.write_text(json.dumps({"projects": {}, "host": "x" * next(writes)}))
        return value

    monkeypatch.setattr(trust, "_load_json", busy_host)

    with pytest.raises(DotError, match="kept changing"):
        trust_folder(tmp_path / "repo", home=tmp_path)
    assert "/repo" not in (tmp_path / ".claude.json").read_text()


def test_trust_dry_run_json_reports_changes_without_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, folder = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    folder.mkdir()
    harness_home(home)
    monkeypatch.setenv("HOME", str(home))
    before = {path: path.read_bytes() for path in home.rglob("*") if path.is_file()}
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())

    run_trust(state, [str(folder)], dry_run=True, as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert (document["schema"], document["dry_run"], document["skipped"]) == ("dot.trust/v1", True, [])
    assert document["folders"][0]["path"] == str(folder)
    assert set(document["folders"][0]["changed"]) == set(document["harnesses"])
    assert {path: path.read_bytes() for path in home.rglob("*") if path.is_file()} == before


def test_trust_json_without_harness_state_lists_no_changes(tmp_path: Path) -> None:
    folder = tmp_path / "work"
    folder.mkdir()
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())

    run_trust(state, [str(folder)], as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert (document["harnesses"], document["folders"][0]["changed"]) == ([], [])


@pytest.mark.parametrize(
    ("relative", "git_at"),
    # Without a repository, a subdirectory of home is an ordinary trustable folder.
    [
        (relative, git_at)
        for relative in (".", "..", "subdir")
        for git_at in (None, "home", "parent")
        if (relative, git_at) != ("subdir", None)
    ],
)
def test_trust_refuses_home_and_its_ancestors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str, git_at: str | None
) -> None:
    home = tmp_path / "home"
    (home / "subdir").mkdir(parents=True)
    if git_at == "home":
        subprocess.run(["git", "init", "-q", str(home)], check=True, timeout=30)
    elif git_at == "parent":
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
    harness_home(home)
    monkeypatch.setenv("HOME", str(home))
    before = {path: path.read_bytes() for path in home.rglob("*") if path.is_file()}
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(pull=PullConfig(directories=[str(home)]))

    with pytest.raises(DotError, match="contains the home directory"):
        run_trust(state, [str(home / relative)])
    with pytest.raises(DotError, match="contains the home directory"):
        run_trust(state, ["all"])

    assert {path: path.read_bytes() for path in home.rglob("*") if path.is_file()} == before


def test_trust_propagates_git_inspection_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, folder = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    folder.mkdir()
    monkeypatch.setenv("HOME", str(home))
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    monkeypatch.setattr(state.runner, "which", lambda _tool: None)

    with pytest.raises(DotError, match="required tools are missing: git"):
        run_trust(state, [str(folder)])


def test_trust_accepts_an_explicit_folder_outside_any_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, folder = tmp_path / "home", tmp_path / "notes"
    home.mkdir()
    folder.mkdir()
    harness_home(home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())

    run_trust(state, [str(folder)])

    assert str(folder) in json.loads((home / ".claude.json").read_text())["projects"]


def agy_registry(home: Path) -> Path:
    registry = home / ".gemini/config/projects"
    registry.mkdir(parents=True)
    # agy's default project lists no folder; it must not block or count as a listed repository.
    (registry / "default-cli-project.json").write_text(
        json.dumps({"id": "default-cli-project", "name": "Default", "projectResources": {}})
    )
    return registry


def git_repository(path: Path, origin: str) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True, timeout=30)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", origin], check=True, timeout=30)
    return path


def test_trust_adds_repositories_to_agy_projects_except_excluded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path.resolve()
    monkeypatch.setenv("HOME", str(home))
    harness_home(home)
    registry = agy_registry(home)
    workspace = home / "work"
    one = git_repository(workspace / "one", "https://github.com/fmind/one")
    excluded = git_repository(workspace / "agent-docs", "https://github.com/fmind/agent-docs")
    git_repository(workspace / "foreign", "https://github.com/someone-else/foreign")
    # An entry agy wrote with a percent-encoded URI already lists this checkout.
    listed = git_repository(workspace / "listed copy", "https://github.com/fmind/listed")
    (registry / "local-native.json").write_text(
        json.dumps({"id": "local-native", "projectResources": {"resources": [{"folderUri": listed.as_uri()}]}})
    )
    (workspace / "notes").mkdir()
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(
        pull=PullConfig(directories=[str(workspace)]), trust=TrustConfig(agy_projects_exclude=["~/work/agent-*"])
    )
    before = sorted(registry.iterdir())

    run_trust(state, ["all"], dry_run=True, as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    assert json.loads(state.stdout.getvalue())["agy_projects"] == [str(one)]
    assert sorted(registry.iterdir()) == before

    state.stdout = io.StringIO()
    run_trust(state, ["all"])

    assert f"+ {one}: added to agy Remote Control projects\n" in state.stdout.getvalue()
    added = set(registry.iterdir()) - set(before)
    assert len(added) == 1
    entry = added.pop()
    assert entry.name == "local-work-one.json"
    project = json.loads(entry.read_text())
    assert project == {
        "id": "local-work-one",
        "name": "work/one",
        "projectResources": {"resources": [{"folderUri": one.as_uri()}]},
    }
    assert entry.stat().st_mode & 0o777 == 0o600
    # Excluded repositories stay trusted; exclusion only keeps them out of the picker.
    assert (
        str(excluded) in json.loads((home / ".gemini/antigravity-cli/settings.json").read_text())["trustedWorkspaces"]
    )

    for targets in (["all"], [str(excluded)]):
        state.stdout = io.StringIO()
        run_trust(state, targets, as_json=True)
        assert json.loads(state.stdout.getvalue())["agy_projects"] == []
    assert len(list(registry.iterdir())) == len(before) + 1


def test_agy_project_exclusions_match_through_a_symlinked_home(tmp_path: Path) -> None:
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    linked_home = tmp_path / "home"
    linked_home.symlink_to(real_home)
    registry = agy_registry(real_home)
    excluded = git_repository(real_home / "work/agent-docs", "https://github.com/fmind/agent-docs")
    kept = git_repository(real_home / "work/one", "https://github.com/fmind/one")

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("HOME", str(linked_home))
        added = register_agy_projects([excluded.resolve(), kept.resolve()], ["~/work/agent-*"], home=linked_home)

    assert added == [kept.resolve()]
    assert len(list(registry.iterdir())) == 2  # agy's default project plus the kept repository


def test_agy_projects_wait_for_agy_to_create_its_registry(tmp_path: Path) -> None:
    repository = git_repository(tmp_path / "repo", "https://github.com/fmind/repo")
    (tmp_path / "home/.gemini/antigravity-cli").mkdir(parents=True)

    assert register_agy_projects([repository], [], home=tmp_path / "home") == []
    assert not (tmp_path / "home/.gemini/config").exists()


@pytest.mark.parametrize(
    "content",
    ["{", "[]", json.dumps({"projectResources": []}), json.dumps({"projectResources": {"resources": ["x"]}})],
)
def test_malformed_agy_project_stops_trust_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    home = tmp_path.resolve()
    monkeypatch.setenv("HOME", str(home))
    harness_home(home)
    registry = agy_registry(home)
    (registry / "broken.json").write_text(content)
    repository = git_repository(home / "repo", "https://github.com/fmind/repo")
    before = {path: path.read_bytes() for path in home.rglob("*") if path.is_file() and ".git" not in path.parts}
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())

    with pytest.raises(DotError, match=r"broken\.json"):
        run_trust(state, [str(repository)])

    assert {
        path: path.read_bytes() for path in home.rglob("*") if path.is_file() and ".git" not in path.parts
    } == before


def test_trust_all_checks_repository_origins_concurrently(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace = tmp_path / "work"
    for name in ("one", "two", "three"):
        (workspace / name / ".git").mkdir(parents=True)
    barrier = threading.Barrier(3, timeout=5)

    class ConcurrentOriginRunner(Runner):
        def run(self, args: object, **_: object) -> CommandResult:
            del args
            barrier.wait()
            return CommandResult("https://github.com/fmind/repo.git\n", "", 0)

    stdout = io.StringIO()
    state = State(runner=ConcurrentOriginRunner(), stdout=stdout, stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = Config(pull=PullConfig(directories=[str(workspace)]))
    run_trust(state, ["all"], dry_run=True, as_json=True)
    document = json.loads(stdout.getvalue())
    assert [item["path"] for item in document["folders"]] == [
        str(workspace),
        str(workspace / "one"),
        str(workspace / "three"),
        str(workspace / "two"),
    ]
