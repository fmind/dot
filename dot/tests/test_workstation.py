"""Public workstation workflows use recorded providers, never real credentials or caches."""

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO, Any

import pytest
from typer.testing import CliRunner

from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner


@pytest.mark.parametrize("command", ["login", "setup"])
def test_provider_groups_without_arguments_show_help(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = CliRunner().invoke(app, [command])
    assert result.exit_code == 0, result.output
    assert "workspace" in result.stdout
    assert "github" in result.stdout


class RecordingRunner(Runner):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[list[str]] = []
        self.actions: list[list[str]] = []
        self.responses: list[CommandResult | Exception] = []
        self.action_code = 0
        self.missing: set[str] = set()

    def which(self, command: str) -> Path | None:
        return None if command in self.missing else Path("/bin") / command

    def run_bounded(
        self,
        args: Sequence[str],
        *,
        max_output_bytes: int,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        assert max_output_bytes == 64 * 1024
        assert timeout is not None
        assert not check
        assert cwd is input_text is env is None
        self.calls.append(list(args))
        assert self.responses, f"unexpected probe: {args}"
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stdout_line: Callable[[str], None] | None = None,
    ) -> int:
        assert cwd is env is on_stdout_line is None
        assert stdin is not None
        assert stdout is not None
        assert stderr is not None
        self.calls.append(list(args))
        self.actions.append(list(args))
        return self.action_code


def response(value: Any) -> CommandResult:
    return CommandResult(json.dumps(value), "", 0)


def workspace_status(*, scopes: list[str] | None = None, **kwargs: Any) -> CommandResult:
    return response(
        {
            "auth_method": "oauth2",
            "token_valid": True,
            "scopes": Config().auth.workspace.scopes if scopes is None else scopes,
            **kwargs,
        }
    )


def github_status(*, scopes: list[str] | None = None, **kwargs: Any) -> CommandResult:
    return response(
        {
            "hosts": {
                "github.com": [
                    {
                        "active": True,
                        "state": "success",
                        "scopes": ", ".join(Config().auth.github.scopes if scopes is None else scopes),
                        **kwargs,
                    }
                ]
            }
        }
    )


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> RecordingRunner:
    fake = RecordingRunner()
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in (
        "GH_HOST",
        "GWS_PROJECT",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GOOGLE_WORKSPACE_CLI_TOKEN",
        "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "DOT_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Runner, "which", fake.which)
    monkeypatch.setattr(Runner, "run_bounded", fake.run_bounded)
    monkeypatch.setattr(Runner, "interactive", fake.interactive)
    return fake


@pytest.mark.parametrize(
    "arguments",
    [
        ["login"],
        ["setup"],
        ["login", "all", "--dry-run"],
        ["login", "github", "--dry-run"],
        ["setup", "github", "--dry-run"],
        ["setup", "workspace", "fixture-project", "--dry-run"],
        ["cache", "--dry-run"],
        ["prune", "all", "--dry-run"],
    ],
)
def test_help_and_preview_never_call_providers(provider: RecordingRunner, arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
    assert provider.calls == []


def test_workspace_satisfied_scope_superset_skips_login(provider: RecordingRunner) -> None:
    provider.responses = [workspace_status(scopes=[*Config().auth.workspace.scopes, "extra"])]
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code == 0, result.exception
    assert "already authenticated" in result.stderr
    assert not provider.actions


@pytest.mark.parametrize(
    "initial",
    [response({"auth_method": "none"}), workspace_status(scopes=["openid"]), workspace_status(token_valid=False)],
)
def test_workspace_missing_auth_or_scopes_logs_in_and_verifies(
    provider: RecordingRunner, initial: CommandResult
) -> None:
    provider.responses = [initial, workspace_status()]
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gws", "auth", "login", "--scopes", ",".join(Config().auth.workspace.scopes)]]
    assert len(provider.calls) == 3


@pytest.mark.parametrize(
    "initial",
    [
        response({}),
        response([]),
        response({"auth_method": "oauth2"}),
        CommandResult("secret", "secret", 2),
        CommandResult("{", "", 0),
        CommandResult("{}", "", 0, stdout_truncated=True),
        DotError("command timed out: gws"),
    ],
)
def test_unknown_workspace_state_does_not_authenticate_or_leak(
    provider: RecordingRunner, initial: CommandResult | Exception
) -> None:
    provider.responses = [initial]
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "secret" not in result.output + str(result.exception)


def test_workspace_force_bypasses_probe_but_verifies_result(provider: RecordingRunner) -> None:
    provider.responses = [workspace_status(scopes=["openid"])]
    result = CliRunner().invoke(app, ["login", "workspace", "--force"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1
    assert "configured scopes" in str(result.exception)


@pytest.mark.parametrize("override", ["GOOGLE_WORKSPACE_CLI_TOKEN", "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"])
def test_workspace_override_does_not_prove_stored_credentials(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, override: str
) -> None:
    monkeypatch.setenv(override, "private")
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code != 0
    assert not provider.calls
    assert "private" not in result.output + str(result.exception)


def test_github_normalized_grants_skip_login(provider: RecordingRunner) -> None:
    scopes = [scope for scope in Config().auth.github.scopes if scope != "read:packages"]
    provider.responses = [github_status(scopes=scopes)]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions


def test_github_missing_scopes_refreshes_instead_of_login(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=["repo"]), github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert [args[:3] for args in provider.actions] == [["gh", "auth", "refresh"]]


def test_github_setup_reconciles_excluded_scopes_once(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=[*Config().auth.github.scopes, "delete_repo"]), github_status()]
    result = CliRunner().invoke(app, ["setup", "github"])
    assert result.exit_code == 0, result.exception
    assert len(provider.actions) == 1
    assert "--remove-scopes" in provider.actions[0]


def test_github_setup_already_satisfied_skips_refresh(provider: RecordingRunner) -> None:
    provider.responses = [github_status()]
    result = CliRunner().invoke(app, ["setup", "github"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions


def test_github_no_accounts_logs_in(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][:3] == ["gh", "auth", "login"]


@pytest.mark.parametrize(
    "entry",
    [
        github_status(state="timeout"),
        github_status(state="error", error="network private"),
        github_status(scopes=[]),
        response({"hosts": []}),
        response({"hosts": {"github.com": [42]}}),
    ],
)
def test_github_unknown_status_is_not_success_or_new_login(provider: RecordingRunner, entry: CommandResult) -> None:
    provider.responses = [entry]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "private" not in result.output + str(result.exception)


def test_github_environment_token_requires_external_scope_repair(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "private")
    provider.responses = [github_status(scopes=["repo"])]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "environment token" in str(result.exception)


def test_gcp_skip_requires_cli_and_adc(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("private-cli", "", 0), CommandResult("private-adc", "", 0)]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions
    assert len(provider.calls) == 2
    assert "private" not in result.output


def test_missing_adc_triggers_login_and_both_postchecks(provider: RecordingRunner) -> None:
    token = CommandResult("private", "", 0)
    provider.responses = [token, CommandResult("", "Your default credentials were not found", 1), token, token]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gcloud", "auth", "login", "--update-adc"]]
    assert "private" not in result.output


def test_gcp_network_failure_does_not_trigger_login(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("", "network private", 1)]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "private" not in str(result.exception)


def test_login_all_orders_workspace_before_gcp_and_excludes_github(provider: RecordingRunner) -> None:
    token = CommandResult("private", "", 0)
    provider.responses = [workspace_status(), token, token]
    result = CliRunner().invoke(app, ["login", "all", "--force"])
    assert result.exit_code == 0, result.exception
    assert [args[:3] for args in provider.actions] == [["gws", "auth", "login"], ["gcloud", "auth", "login"]]


def test_login_all_stops_on_workspace_failure(provider: RecordingRunner) -> None:
    provider.action_code = 17
    result = CliRunner().invoke(app, ["login", "all", "--force"])
    assert result.exit_code != 0
    assert len(provider.calls) == 1
    assert provider.calls[0][0] == "gws"


def test_setup_workspace_already_configured_does_nothing(provider: RecordingRunner) -> None:
    provider.responses = [
        response([{"config": {"name": api}} for api in Config().auth.workspace.apis]),
        response({"client_config_exists": True, "project_id": "fixture-project"}),
    ]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions


def test_workspace_setup_enables_only_missing_apis_and_stops_on_failure(provider: RecordingRunner) -> None:
    apis = Config().auth.workspace.apis
    provider.responses = [
        response([{"config": {"name": api}} for api in apis[1:]]),
        response({"client_config_exists": False}),
    ]
    provider.action_code = 1
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code != 0
    assert provider.actions == [["gcloud", "services", "enable", apis[0], "--project", "fixture-project", "--quiet"]]


@pytest.mark.parametrize("args", [[], ["literal project; $(touch injected)"], ["--bad"]])
def test_workspace_setup_rejects_missing_or_invalid_project_before_probes(
    provider: RecordingRunner, args: list[str]
) -> None:
    result = CliRunner().invoke(app, ["setup", "workspace", *args])
    assert result.exit_code == 2
    assert not provider.calls


def test_host_project_and_scope_override_precedence(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        "auth:\n  github:\n    host: config.test\n    scopes: [repo]\n  workspace:\n    project: config-project\n    scopes: [openid]\n"
    )
    monkeypatch.setenv("GH_HOST", "env.test")
    monkeypatch.setenv("GWS_PROJECT", "env-project")
    runner = CliRunner()
    assert "env.test" in runner.invoke(app, ["--config", str(path), "login", "github", "--dry-run"]).stdout
    result = runner.invoke(app, ["--config", str(path), "login", "github", "--host", "cli.test", "--dry-run"])
    assert result.exit_code == 0, result.exception
    assert "--hostname cli.test --scopes repo" in result.stdout
    result = runner.invoke(app, ["--config", str(path), "setup", "workspace", "cli-project", "--dry-run"])
    assert "--project cli-project" in result.stdout
    result = runner.invoke(app, ["--config", str(path), "login", "workspace", "--dry-run"])
    assert "--scopes openid" in result.stdout
    assert not provider.calls


def test_cache_default_inspects_all_and_preserves_native_output(provider: RecordingRunner) -> None:
    result = CliRunner().invoke(app, ["cache"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [
        ["docker", "system", "df"],
        ["hf", "cache", "ls"],
        ["uv", "cache", "size", "--preview-features", "cache-size"],
    ]


def test_prune_requires_confirmation_and_default_excludes_docker(provider: RecordingRunner) -> None:
    result = CliRunner().invoke(app, ["prune", "all"])
    assert result.exit_code != 0
    assert not provider.actions
    result = CliRunner().invoke(app, ["prune", "all", "--yes"])
    assert result.exit_code == 0, result.exception
    assert {args[0] for args in provider.actions} == {"dprint", "hf", "mise", "npm", "trivy", "uv"}
    assert ["hf", "cache", "prune", "--yes"] in provider.actions


def test_docker_prune_requires_explicit_selection(provider: RecordingRunner) -> None:
    result = CliRunner().invoke(app, ["prune", "docker", "--yes"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["docker", "builder", "prune", "--force"]]


def test_prune_missing_tools_fails_before_any_cleanup(provider: RecordingRunner) -> None:
    provider.missing.add("uv")
    result = CliRunner().invoke(app, ["prune", "all", "--yes"])
    assert result.exit_code != 0
    assert not provider.actions


def test_native_failure_stops_aggregate(provider: RecordingRunner) -> None:
    provider.action_code = 17
    result = CliRunner().invoke(app, ["prune", "all", "--yes"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1


def test_workspace_setup_verifies_changes_and_second_run_is_noop(provider: RecordingRunner) -> None:
    enabled = response([{"config": {"name": api}} for api in Config().auth.workspace.apis])
    configured = response({"client_config_exists": True, "project_id": "fixture-project"})
    provider.responses = [
        response([]),
        response({"client_config_exists": False}),
        enabled,
        configured,
        enabled,
        configured,
    ]
    runner = CliRunner()
    first = runner.invoke(app, ["setup", "workspace", "fixture-project"])
    assert first.exit_code == 0, first.exception
    assert [args[:3] for args in provider.actions] == [["gcloud", "services", "enable"], ["gws", "auth", "setup"]]
    provider.actions.clear()
    second = runner.invoke(app, ["setup", "workspace", "fixture-project"])
    assert second.exit_code == 0, second.exception
    assert not provider.actions


def test_workspace_incomplete_enablement_stops_before_oauth(provider: RecordingRunner) -> None:
    provider.responses = [response([]), response({"client_config_exists": False}), response([])]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1
    assert "remain missing" in str(result.exception)


def test_github_rejected_token_reauthenticates(provider: RecordingRunner) -> None:
    provider.responses = [github_status(state="error", error="HTTP 401: Bad credentials (HTTP 401)"), github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][:3] == ["gh", "auth", "login"]


def test_new_github_setup_logs_in_then_reconciles_old_grants(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), github_status()]
    result = CliRunner().invoke(app, ["setup", "github"])
    assert result.exit_code == 0, result.exception
    assert [args[:3] for args in provider.actions] == [["gh", "auth", "login"], ["gh", "auth", "refresh"]]
    assert "--remove-scopes" in provider.actions[1]


def test_custom_cache_and_prune_selections_replace_defaults(provider: RecordingRunner, tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("cache:\n  providers: [uv, uv]\nprune:\n  providers: [npm]\n")
    runner = CliRunner()
    result = runner.invoke(app, ["--config", str(path), "cache"])
    assert result.exit_code == 0, result.exception
    result = runner.invoke(app, ["--config", str(path), "prune", "all", "--yes"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["uv", "cache", "size", "--preview-features", "cache-size"], ["npm", "cache", "verify"]]
