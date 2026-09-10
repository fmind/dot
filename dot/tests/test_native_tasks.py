"""Run global workstation task contracts through mise with recording native-tool fakes."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from typer import _click

ROOT = Path(__file__).resolve().parents[2]


def test_global_tasks_and_aliases_use_the_dot_namespace() -> None:
    tasks = {}
    for path in (ROOT / "dot_config/mise/conf.d").glob("*.toml"):
        definitions = tomllib.loads(path.read_text()).get("tasks", {})
        assert not tasks.keys() & definitions.keys(), "duplicate global task name"
        tasks.update(definitions)
    assert tasks
    for name, task in tasks.items():
        assert name.startswith("dot:"), name
        aliases = task.get("alias", [])
        if isinstance(aliases, str):
            aliases = [aliases]
        assert all(alias.startswith("dot:") for alias in aliases), name
    assert set(tasks["dot:prune"]["depends"]) == {
        name for name in tasks if name.startswith("dot:prune:") and name != "dot:prune:docker"
    }


@pytest.fixture(params=[False, True], ids=["outside-project", "inside-project"])
def task_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    mise = shutil.which("mise")
    assert mise is not None
    mise = str(Path(mise).resolve())
    (tmp_path / "home").mkdir()
    config_dir = tmp_path / "config"
    shutil.copytree(ROOT / "dot_config/mise/conf.d", config_dir / "conf.d")
    caller = tmp_path / "unrelated" / "nested"
    caller.mkdir(parents=True)
    if request.param:
        (caller.parent / "mise.toml").write_text(
            '[task_config]\ndir = "{{config_root}}"\n[tasks.fixture]\nrun = "echo fixture"\n'
            '[tasks.login]\nrun = "exit 91"\n[tasks.cache]\nrun = "exit 92"\n[tasks.prune]\nrun = "exit 93"\n'
        )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    log = tmp_path / "calls"
    log.mkdir()
    for name in ("dprint", "docker", "gh", "gcloud", "gws", "hf", "mise", "npm", "trivy", "uv"):
        script = binaries / name
        script.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "name = Path(sys.argv[0]).name\n"
            # mise cancels sibling tasks on failure; publish complete fake evidence atomically.
            "def publish(path, content):\n"
            "    temporary = path.with_suffix('.tmp')\n"
            "    temporary.write_text(content)\n"
            "    temporary.replace(path)\n"
            "log = Path(os.environ['TASK_TEST_LOG'])\n"
            "if name == 'gcloud' and os.environ.get('TASK_TEST_LOGIN_ORDER'):\n"
            "    assert (log / 'gws.jsonl').exists(), 'Workspace must finish before GCP starts'\n"
            "publish(log / (name + '.cwd'), str(Path.cwd()))\n"
            "calls = log / (name + '.jsonl')\n"
            "previous = calls.read_text() if calls.exists() else ''\n"
            "publish(calls, previous + json.dumps(sys.argv[1:]) + '\\n')\n"
            "if os.environ.get('TASK_TEST_FAIL') == name: sys.exit(17)\n"
            "if name == 'gh' and sys.argv[1:3] == ['auth', 'status']:\n"
            "    sys.exit(int(os.environ.get('TASK_TEST_AUTH_STATUS', '0')))\n"
        )
        script.chmod(0o755)
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("MISE_", "DOT_", "usage_"))}
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "PATH": str(binaries) + os.pathsep + environment["PATH"],
            "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path),
            "MISE_CONFIG_DIR": str(config_dir),
            "MISE_SYSTEM_CONFIG_DIR": str(tmp_path / "system"),
            "MISE_DATA_DIR": str(tmp_path / "data"),
            "MISE_CACHE_DIR": str(tmp_path / "cache"),
            "MISE_STATE_DIR": str(tmp_path / "state"),
            "TASK_TEST_LOG": str(log),
        }
    )
    for key in ("GH_HOST", "GWS_PROJECT", "TASK_TEST_AUTH_STATUS", "TASK_TEST_FAIL", "TASK_TEST_LOGIN_ORDER"):
        environment.pop(key, None)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    def run(*arguments: str, variables: dict[str, str] | None = None):
        result = subprocess.run(
            [mise, "run", *arguments],
            cwd=caller,
            env=environment | (variables or {}),
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        calls = {
            path.stem: [json.loads(line) for line in path.read_text().splitlines()] for path in log.glob("*.jsonl")
        }
        for path in log.glob("*.cwd"):
            assert path.read_text() == str(caller)
        return result, calls

    return run


def test_cache_aggregate_runs_only_local_disposable_cache_operations(task_runner) -> None:
    result, calls = task_runner("dot:prune")
    assert result.returncode == 0, result.stderr
    assert calls == {
        "dprint": [["clear-cache"]],
        "hf": [["cache", "prune"]],
        "mise": [["cache", "clear"]],
        "npm": [["cache", "verify"]],
        "trivy": [["clean", "--scan-cache"]],
        "uv": [["cache", "prune"]],
    }


@pytest.mark.parametrize(
    "arguments",
    [
        ("dot:prune",),
        ("dot:cache",),
        ("dot:setup:workspace", "fixture-project"),
        ("dot:login:workspace",),
        ("dot:login",),
    ],
)
def test_workstation_preview_invokes_no_native_commands(task_runner, arguments: tuple[str, ...]) -> None:
    result, calls = task_runner("--dry-run", *arguments)
    assert result.returncode == 0, result.stderr
    assert calls == {}


def test_cache_failure_is_not_reported_as_success(task_runner) -> None:
    result, calls = task_runner("dot:prune", variables={"TASK_TEST_FAIL": "uv"})
    assert result.returncode != 0
    assert calls["uv"] == [["cache", "prune"]]


@pytest.mark.parametrize(("status", "action"), [("0", "refresh"), ("1", "login")])
def test_github_setup_keeps_scopes_and_selects_the_correct_authentication_action(
    task_runner, status: str, action: str
) -> None:
    result, calls = task_runner(
        "dot:setup:github", "--host", "github.example.test", variables={"TASK_TEST_AUTH_STATUS": status}
    )
    assert result.returncode == 0, result.stderr
    assert calls["gh"][0] == ["auth", "status", "--hostname", "github.example.test"]
    selected = calls["gh"][1]
    assert selected[:5] == ["auth", action, "--hostname", "github.example.test", "--scopes"]
    assert set(selected[5].split(",")) == {
        "gist",
        "notifications",
        "project",
        "read:org",
        "read:packages",
        "read:user",
        "repo",
        "user:email",
        "workflow",
        "write:packages",
        "write:public_key",
    }
    if action == "refresh":
        assert selected[6] == "--remove-scopes"
        assert set(selected[7].split(",")) == {"admin:public_key", "delete:packages", "delete_repo", "user"}
    else:
        assert len(selected) == 6


def test_workspace_login_preserves_editing_and_adds_mail_settings_and_chat_read_state(task_runner) -> None:
    result, calls = task_runner("dot:login:workspace")
    assert result.returncode == 0, result.stderr
    assert calls["gws"][0][:3] == ["auth", "login", "--scopes"]
    scopes = calls["gws"][0][3].split(",")
    assert len(scopes) == 25
    assert "openid" in scopes
    assert "https://www.googleapis.com/auth/gmail.modify" in scopes
    assert "https://www.googleapis.com/auth/gmail.settings.basic" in scopes
    assert "https://www.googleapis.com/auth/chat.messages" in scopes
    assert "https://www.googleapis.com/auth/chat.users.readstate" in scopes
    assert "https://www.googleapis.com/auth/script.deployments" in scopes
    assert "https://www.googleapis.com/auth/drive" in scopes
    assert not set(scopes) & {
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.settings.sharing",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/user.emails.read",
    }


def test_workspace_setup_rejects_missing_project_before_side_effects(task_runner) -> None:
    result, calls = task_runner("dot:setup:workspace")
    assert result.returncode != 0
    assert calls == {}


def test_workspace_setup_preserves_project_argument_boundaries_and_environment_precedence(task_runner) -> None:
    project = "literal project; $(touch unexpected)"
    result, calls = task_runner("dot:setup:workspace", project, variables={"GWS_PROJECT": "ignored-project"})
    assert result.returncode == 0, result.stderr
    assert calls["gcloud"][0][-3:] == ["--project", project, "--quiet"]
    assert calls["gcloud"][0][:2] == ["services", "enable"]
    assert len(calls["gcloud"][0][2:-3]) == 12
    assert "keep.googleapis.com" not in calls["gcloud"][0]
    assert calls["gws"] == [["auth", "setup", "--project", project]]


def test_workspace_setup_stops_if_api_enablement_fails(task_runner) -> None:
    result, calls = task_runner(
        "dot:setup:workspace", variables={"GWS_PROJECT": "fixture-project", "TASK_TEST_FAIL": "gcloud"}
    )
    assert result.returncode != 0
    assert calls["gcloud"][0][-3:] == ["--project", "fixture-project", "--quiet"]
    assert "gws" not in calls


def test_global_gcp_login_runs_from_an_unrelated_directory(task_runner) -> None:
    result, calls = task_runner("dot:login:gcp")
    assert result.returncode == 0, result.stderr
    assert calls == {"gcloud": [["auth", "login", "--update-adc"]]}


def test_default_login_runs_workspace_then_gcp_without_github(task_runner) -> None:
    result, calls = task_runner("dot:login", variables={"TASK_TEST_LOGIN_ORDER": "1"})
    assert result.returncode == 0, result.stderr
    assert set(calls) == {"gws", "gcloud"}
    assert calls["gws"][0][:3] == ["auth", "login", "--scopes"]
    assert calls["gcloud"] == [["auth", "login", "--update-adc"]]


@pytest.mark.parametrize("tool", ["gws", "gcloud"])
def test_default_login_propagates_failure_and_stops_before_next_provider(task_runner, tool: str) -> None:
    result, calls = task_runner("dot:login", variables={"TASK_TEST_FAIL": tool})
    assert result.returncode != 0
    assert set(calls) == ({"gws"} if tool == "gws" else {"gws", "gcloud"})


def test_cache_inspection_reports_usage_without_pruning(task_runner) -> None:
    result, calls = task_runner("dot:cache")
    assert result.returncode == 0, result.stderr
    assert calls == {
        "uv": [["cache", "size", "--preview-features", "cache-size"]],
        "hf": [["cache", "ls"]],
        "docker": [["system", "df"]],
    }


def test_docker_cache_inspection_is_explicit(task_runner) -> None:
    result, calls = task_runner("dot:cache:docker")
    assert result.returncode == 0, result.stderr
    assert calls == {"docker": [["system", "df"]]}


def test_chezmoi_installs_global_tasks_without_removing_existing_config(tmp_path: Path) -> None:
    source = tmp_path / "source"
    shutil.copytree(ROOT / "dot_config/mise/conf.d", source / "dot_config/mise/conf.d")
    destination = tmp_path / "home"
    conf = destination / ".config/mise/conf.d"
    conf.mkdir(parents=True)
    (conf / "maintenance.toml").write_text('[tasks.legacy]\nrun = "echo legacy"\n')
    (conf / "personal.toml").write_text('[tasks.personal]\nrun = "echo personal"\n')
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    environment = dict(os.environ, HOME=str(destination), XDG_CONFIG_HOME=str(destination / ".config"))
    environment["XDG_DATA_HOME"] = str(destination / ".local/share")
    command = [
        "chezmoi",
        "apply",
        "--force",
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--config",
        str(config),
    ]
    first = subprocess.run(command, env=environment, capture_output=True, text=True, check=False, timeout=20)
    assert first.returncode == 0, first.stderr
    before = {path.name: path.read_bytes() for path in conf.iterdir()}
    assert set(before) == {"login.toml", "setup.toml", "cache.toml", "prune.toml", "personal.toml", "maintenance.toml"}
    assert before["maintenance.toml"] == b'[tasks.legacy]\nrun = "echo legacy"\n'
    assert before["personal.toml"] == b'[tasks.personal]\nrun = "echo personal"\n'
    second = subprocess.run(command, env=environment, capture_output=True, text=True, check=False, timeout=20)
    assert second.returncode == 0, second.stderr
    assert {path.name: path.read_bytes() for path in conf.iterdir()} == before


@pytest.mark.parametrize("name", ["release", "build", "prune:sessions"])
def test_global_tasks_do_not_expose_repository_operations(task_runner, name: str) -> None:
    result, calls = task_runner(name)
    assert result.returncode != 0
    assert f"no task {name} found" in _click.utils.strip_ansi(result.stderr)
    assert calls == {}
