"""Run maintenance task contracts through mise with recording native-tool fakes."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer import _click

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(params=[False, True], ids=["outside-project", "inside-project"])
def task_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    mise = shutil.which("mise")
    assert mise is not None
    mise = str(Path(mise).resolve())
    (tmp_path / "home").mkdir()
    config_dir = tmp_path / "config"
    global_tasks = config_dir / "conf.d" / "maintenance.toml"
    global_tasks.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_config/mise/conf.d/maintenance.toml", global_tasks)
    caller = tmp_path / "unrelated" / "nested"
    caller.mkdir(parents=True)
    if request.param:
        (caller.parent / "mise.toml").write_text(
            '[task_config]\ndir = "{{config_root}}"\n[tasks.fixture]\nrun = "echo fixture"\n'
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
    for key in ("GH_HOST", "GWS_PROJECT", "TASK_TEST_AUTH_STATUS", "TASK_TEST_FAIL"):
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
    result, calls = task_runner("prune")
    assert result.returncode == 0, result.stderr
    assert calls == {
        "dprint": [["clear-cache"]],
        "mise": [["cache", "clear"]],
        "npm": [["cache", "verify"]],
        "trivy": [["clean", "--scan-cache"]],
        "uv": [["cache", "prune"]],
    }


@pytest.mark.parametrize("arguments", [("prune",), ("setup:workspace", "fixture-project"), ("login:workspace",)])
def test_maintenance_preview_invokes_no_native_commands(task_runner, arguments: tuple[str, ...]) -> None:
    result, calls = task_runner("--dry-run", *arguments)
    assert result.returncode == 0, result.stderr
    assert calls == {}


def test_cache_failure_is_not_reported_as_success(task_runner) -> None:
    result, calls = task_runner("prune", variables={"TASK_TEST_FAIL": "uv"})
    assert result.returncode != 0
    assert calls["uv"] == [["cache", "prune"]]


@pytest.mark.parametrize(("status", "action"), [("0", "refresh"), ("1", "login")])
def test_github_setup_keeps_scopes_and_selects_the_correct_authentication_action(
    task_runner, status: str, action: str
) -> None:
    result, calls = task_runner(
        "setup:github", "--host", "github.example.test", variables={"TASK_TEST_AUTH_STATUS": status}
    )
    assert result.returncode == 0, result.stderr
    assert calls["gh"][0] == ["auth", "status", "--hostname", "github.example.test"]
    selected = calls["gh"][1]
    assert selected[:5] == ["auth", action, "--hostname", "github.example.test", "--scopes"]
    assert set(selected[5].split(",")) == {
        "admin:public_key",
        "delete:packages",
        "gist",
        "notifications",
        "project",
        "read:org",
        "read:packages",
        "repo",
        "user",
        "workflow",
        "write:packages",
    }


def test_workspace_login_requests_the_retained_scope_policy(task_runner) -> None:
    result, calls = task_runner("login:workspace")
    assert result.returncode == 0, result.stderr
    assert calls["gws"][0][:3] == ["auth", "login", "--scopes"]
    scopes = calls["gws"][0][3].split(",")
    assert len(scopes) == 25
    assert "openid" in scopes
    assert "https://www.googleapis.com/auth/gmail.modify" in scopes
    assert "https://www.googleapis.com/auth/chat.messages" in scopes
    assert "https://www.googleapis.com/auth/script.deployments" in scopes


def test_workspace_setup_rejects_missing_project_before_side_effects(task_runner) -> None:
    result, calls = task_runner("setup:workspace")
    assert result.returncode != 0
    assert calls == {}


def test_workspace_setup_preserves_project_argument_boundaries_and_environment_precedence(task_runner) -> None:
    project = "literal project; $(touch unexpected)"
    result, calls = task_runner("setup:workspace", project, variables={"GWS_PROJECT": "ignored-project"})
    assert result.returncode == 0, result.stderr
    assert calls["gcloud"][0][-3:] == ["--project", project, "--quiet"]
    assert calls["gcloud"][0][:2] == ["services", "enable"]
    assert len(calls["gcloud"][0][2:-3]) == 13
    assert calls["gws"] == [["auth", "setup", "--project", project]]


def test_workspace_setup_stops_if_api_enablement_fails(task_runner) -> None:
    result, calls = task_runner(
        "setup:workspace", variables={"GWS_PROJECT": "fixture-project", "TASK_TEST_FAIL": "gcloud"}
    )
    assert result.returncode != 0
    assert calls["gcloud"][0][-3:] == ["--project", "fixture-project", "--quiet"]
    assert "gws" not in calls


def test_global_gcp_login_runs_from_an_unrelated_directory(task_runner) -> None:
    result, calls = task_runner("login:gcp")
    assert result.returncode == 0, result.stderr
    assert calls == {"gcloud": [["auth", "login", "--update-adc"]]}


@pytest.mark.parametrize("name", ["release", "build", "prune:sessions"])
def test_global_tasks_do_not_expose_repository_operations(task_runner, name: str) -> None:
    result, calls = task_runner(name)
    assert result.returncode != 0
    assert f"no task {name} found" in _click.utils.strip_ansi(result.stderr)
    assert calls == {}
