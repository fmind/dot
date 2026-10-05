"""Public workstation workflows use recorded providers, never real credentials or caches."""

import json
from collections.abc import Callable, Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import IO, Any

import pytest
from typer.testing import CliRunner

from fmind_dot import auth
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
        self.envs: list[Mapping[str, str] | None] = []
        self.relays: list[Callable[[str], None] | None] = []

    def which(self, command: str) -> Path | None:
        return None if command in self.missing else Path("/bin") / command

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
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
        on_stderr_line: Callable[[str], None] | None = None,
    ) -> int:
        assert cwd is None
        assert stdin is not None
        assert stdout is not None
        assert stderr is not None
        self.calls.append(list(args))
        self.actions.append(list(args))
        self.envs.append(env)
        self.relays.append(on_stderr_line)
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


PROTOCOL = CommandResult("ssh\n", "", 0)
TOKEN = CommandResult("private", "", 0)
SCOPE_GAP = CommandResult("", "ERROR: Invalid value for [--scopes]: Invalid scopes value. private", 1)
ADC_SCOPES = ",".join(Config().auth.gcp.adc_scopes)
ADC_PROBE = ["gcloud", "auth", "application-default", "print-access-token", f"--scopes={ADC_SCOPES}"]
ADC_LOGIN = ["gcloud", "auth", "application-default", "login", f"--scopes={ADC_SCOPES}"]


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
        "GWS_PROJECT",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GOOGLE_WORKSPACE_CLI_TOKEN",
        "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "DOT_CONFIG_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Runner, "which", fake.which)
    monkeypatch.setattr(Runner, "run", fake.run)
    monkeypatch.setattr(Runner, "interactive", fake.interactive)
    return fake


@pytest.mark.parametrize(
    "arguments",
    [
        ["login"],
        ["setup"],
        ["login", "all", "--dry-run"],
        ["login", "colab", "--dry-run"],
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


def test_workspace_defaults_own_scopes_borrowed_by_brain_sensors() -> None:
    # gws replaces its whole grant on login: dropping a borrowed scope breaks its consumers.
    workspace = Config().auth.workspace
    for scope in ("analytics.readonly", "webmasters.readonly", "youtube.readonly", "yt-analytics.readonly"):
        assert f"https://www.googleapis.com/auth/{scope}" in workspace.scopes
    for api in ("analyticsadmin", "analyticsdata", "searchconsole", "youtube", "youtubeanalytics"):
        assert f"{api}.googleapis.com" in workspace.apis


def test_workspace_grant_missing_borrowed_scope_logs_in(provider: RecordingRunner) -> None:
    borrowed = "https://www.googleapis.com/auth/youtube.readonly"
    granted = [scope for scope in Config().auth.workspace.scopes if scope != borrowed]
    provider.responses = [workspace_status(scopes=granted), workspace_status()]
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code == 0, result.exception
    assert borrowed in provider.actions[0][-1].split(",")


@pytest.mark.parametrize("arguments", [["login", "github"], ["setup", "github"]])
def test_github_plaintext_token_warns_after_satisfied_probe(provider: RecordingRunner, arguments: list[str]) -> None:
    provider.responses = [github_status(tokenSource="/home/user/.config/gh/hosts.yml")]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.exception
    assert not provider.actions
    assert "plaintext hosts.yml" in result.stderr


def test_github_plaintext_token_warns_after_login(provider: RecordingRunner) -> None:
    provider.responses = [
        response({"hosts": {}}),
        PROTOCOL,
        github_status(tokenSource="/home/user/.config/gh/hosts.yml"),
    ]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][:3] == ["gh", "auth", "login"]
    assert "plaintext hosts.yml" in result.stderr
    assert "/home/user" not in result.stderr


@pytest.mark.parametrize("source", ["keyring", "GH_TOKEN", None])
def test_github_keyring_or_environment_token_does_not_warn(provider: RecordingRunner, source: str | None) -> None:
    provider.responses = [github_status() if source is None else github_status(tokenSource=source)]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert "plaintext" not in result.stderr


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


def test_github_no_accounts_logs_in_through_the_web_with_configured_protocol(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), PROTOCOL, github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][:3] == ["gh", "auth", "login"]
    assert provider.actions[0][-3:] == ["--web", "--git-protocol", "ssh"]
    assert provider.calls[1] == ["gh", "config", "get", "git_protocol", "--host", "github.com"]


@pytest.mark.parametrize("protocol", [CommandResult("", "private", 1), CommandResult("ftp\n", "", 0)])
def test_github_unknown_protocol_keeps_the_native_prompt(provider: RecordingRunner, protocol: CommandResult) -> None:
    provider.responses = [response({"hosts": {}}), protocol, github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][-1] == "--web"
    assert "private" not in result.output


@pytest.mark.parametrize(
    ("sommelier", "display", "expected"),
    [("1", ":0", {"WAYLAND_DISPLAY": ""}), ("", ":0", None), ("1", "", None)],
)
def test_github_login_copies_the_device_code_through_x11_on_crostini(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, sommelier: str, display: str, expected: object
) -> None:
    # Under Sommelier, wl-copy never forks, so gh would wait on it forever after printing nothing.
    monkeypatch.setenv("SOMMELIER_VERSION", sommelier)
    monkeypatch.setenv("DISPLAY", display)
    provider.responses = [response({"hosts": {}}), PROTOCOL, github_status()]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.envs == [expected]


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


def test_gcp_skip_requires_cli_and_scoped_adc(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("private-cli", "", 0), CommandResult("private-adc", "", 0)]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions
    assert provider.calls == [["gcloud", "auth", "print-access-token"], ADC_PROBE]
    assert "private" not in result.output


@pytest.mark.parametrize("adc", [CommandResult("", "Your default credentials were not found", 1), SCOPE_GAP])
def test_missing_or_narrow_adc_relogs_only_adc_with_configured_scopes(
    provider: RecordingRunner, adc: CommandResult
) -> None:
    # gcloud auth login --update-adc would replace the ADC grant with defaults and drop Colab's scope.
    provider.responses = [TOKEN, adc, TOKEN, TOKEN]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [ADC_LOGIN]
    assert "https://www.googleapis.com/auth/colaboratory" in ADC_SCOPES
    assert "private" not in result.output


def test_gcp_force_runs_both_logins_and_verifies(provider: RecordingRunner) -> None:
    provider.responses = [TOKEN, TOKEN]
    result = CliRunner().invoke(app, ["login", "gcp", "--force"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gcloud", "auth", "login"], ADC_LOGIN]


@pytest.mark.parametrize(
    "diagnostic",
    [
        # gcloud 585 texts for an expired session (core/credentials/exceptions.py).
        (
            "There was a problem reauthenticating while refreshing your current auth tokens: private\n"
            "Please retry your command or run:\n\n  $ gcloud auth login"
        ),
        "Please run:\n\n  $ gcloud auth login\n\nto complete reauthentication.",
        (
            "There was a problem refreshing your current auth tokens: private\nPlease run:\n\n"
            "  $ gcloud auth application-default login\n\nto obtain new credentials."
        ),
    ],
)
def test_expired_gcloud_session_triggers_login(provider: RecordingRunner, diagnostic: str) -> None:
    provider.responses = [CommandResult("", diagnostic, 1), TOKEN, TOKEN, TOKEN]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gcloud", "auth", "login"]]
    assert "private" not in result.output


def test_gcp_network_failure_does_not_trigger_login(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("", "network private", 1)]
    result = CliRunner().invoke(app, ["login", "gcp"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "private" not in str(result.exception)


COLAB_LISTING = CommandResult("[colab] No active sessions found on server.\n", "", 0)
COLAB_SESSIONS = ["colab", "--auth=adc", "sessions"]


@pytest.mark.parametrize(
    "listing",
    [COLAB_LISTING, CommandResult("[private] private | Hardware: T4 | Shape: Standard | Variant: GPU\n", "", 0)],
)
def test_colab_scoped_adc_skips_login_and_keeps_session_details_private(
    provider: RecordingRunner, listing: CommandResult
) -> None:
    provider.responses = [TOKEN, listing]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code == 0, result.exception
    assert provider.calls == [ADC_PROBE, COLAB_SESSIONS]
    assert "private" not in result.output


def test_colab_missing_scope_requests_the_configured_grant(provider: RecordingRunner) -> None:
    provider.responses = [SCOPE_GAP, COLAB_LISTING]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code == 0, result.exception
    assert provider.calls == [ADC_PROBE, ADC_LOGIN, COLAB_SESSIONS]
    assert "private" not in result.output


def test_colab_force_requests_the_grant_without_probing(provider: RecordingRunner) -> None:
    provider.responses = [COLAB_LISTING]
    result = CliRunner().invoke(app, ["login", "colab", "--force"])
    assert result.exit_code == 0, result.exception
    assert provider.calls == [ADC_LOGIN, COLAB_SESSIONS]


def test_colab_requires_its_scopes_in_the_adc_policy(provider: RecordingRunner, tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("auth:\n  gcp:\n    adc_scopes: [openid]\n")
    result = CliRunner().invoke(app, ["--config", str(path), "login", "colab", "--dry-run"])
    assert result.exit_code != 0
    assert "colaboratory" in str(result.exception)
    assert not provider.calls


def test_colab_preview_includes_scopes_and_session_check(provider: RecordingRunner) -> None:
    result = CliRunner().invoke(app, ["login", "colab", "--dry-run"])
    assert result.exit_code == 0, result.exception
    assert " ".join(ADC_LOGIN) in result.stdout
    assert "colab --auth=adc sessions" in result.stdout
    assert not provider.calls


@pytest.mark.parametrize("missing", ["colab", "gcloud"])
def test_colab_missing_tool_fails_before_authentication(provider: RecordingRunner, missing: str) -> None:
    provider.missing.add(missing)
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert not provider.calls


def test_colab_external_adc_is_not_overwritten(provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/private/customer.json")
    provider.responses = [SCOPE_GAP]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "GOOGLE_APPLICATION_CREDENTIALS" in str(result.exception)
    assert "/private" not in str(result.exception)


@pytest.mark.parametrize("initial", [CommandResult("", "network private", 1), CommandResult("", "", 0)])
def test_colab_unknown_postcheck_is_not_success(provider: RecordingRunner, initial: CommandResult) -> None:
    provider.responses = [SCOPE_GAP, initial]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert provider.actions == [ADC_LOGIN]
    assert "inspect colab --auth=adc sessions" in str(result.exception)
    assert "private" not in str(result.exception)


def test_colab_unknown_adc_state_does_not_authenticate(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("", "network private", 1)]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert not provider.actions
    assert "colab authentication state is unknown" in str(result.exception)
    assert "private" not in str(result.exception)


def test_colab_failed_login_stops_before_postcheck(provider: RecordingRunner) -> None:
    provider.responses = [SCOPE_GAP]
    provider.action_code = 17
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert provider.calls == [ADC_PROBE, ADC_LOGIN]


@pytest.mark.parametrize(
    "listing",
    [
        CommandResult(COLAB_LISTING.stdout, "No valid default credentials found. private", 0),
        CommandResult("", "google.auth.exceptions.DefaultCredentialsError: private", 1),
        CommandResult("", "Request had insufficient authentication scopes. private", 1),
        CommandResult("ACCESS_TOKEN_SCOPE_INSUFFICIENT private", "", 1),
        CommandResult("", "invalid_grant: private", 1),
    ],
)
def test_colab_failed_postcheck_is_not_success(provider: RecordingRunner, listing: CommandResult) -> None:
    provider.responses = [SCOPE_GAP, listing]
    result = CliRunner().invoke(app, ["login", "colab"])
    assert result.exit_code != 0
    assert provider.calls == [ADC_PROBE, ADC_LOGIN, COLAB_SESSIONS]
    assert "required scopes" in str(result.exception)
    assert "private" not in str(result.exception)


def client_status(**kwargs: Any) -> CommandResult:
    return response(
        {
            "client_config_exists": True,
            "project_id": "fixture-project",
            "enabled_apis": Config().auth.workspace.apis,
            **kwargs,
        }
    )


def test_setup_workspace_names_gcp_login_for_stale_gcloud(provider: RecordingRunner) -> None:
    reauth = CommandResult("", "Reauthentication failed.\n\n  $ gcloud auth login\n\nto obtain new credentials.", 1)
    provider.responses = [client_status(enabled_apis=None), reauth]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code != 0
    assert "dot login gcp" in str(result.exception)
    assert not provider.actions


def test_setup_workspace_already_configured_needs_only_gws_status(provider: RecordingRunner) -> None:
    provider.responses = [client_status()]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions
    assert provider.calls == [["gws", "auth", "status"]]


def test_setup_workspace_enables_apis_missing_from_gws_status(provider: RecordingRunner) -> None:
    apis = Config().auth.workspace.apis
    provider.responses = [client_status(enabled_apis=apis[1:]), response([{"config": {"name": api}} for api in apis])]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gcloud", "services", "enable", apis[0], "--project", "fixture-project", "--quiet"]]
    assert provider.calls[0] == ["gws", "auth", "status"]


def test_setup_workspace_other_project_lists_apis_with_gcloud(provider: RecordingRunner) -> None:
    provider.responses = [
        client_status(project_id="other-project", enabled_apis=[]),
        response([{"config": {"name": api}} for api in Config().auth.workspace.apis]),
        client_status(),
    ]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code == 0, result.exception
    assert [args[:3] for args in provider.actions] == [["gws", "auth", "setup"]]
    assert provider.calls[1][:3] == ["gcloud", "services", "list"]


def test_workspace_setup_enables_only_missing_apis_and_stops_on_failure(provider: RecordingRunner) -> None:
    apis = Config().auth.workspace.apis
    provider.responses = [
        response({"client_config_exists": False}),
        response([{"config": {"name": api}} for api in apis[1:]]),
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


def test_project_and_scope_override_precedence(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        "auth:\n  github:\n    scopes: [repo]\n  workspace:\n    project: config-project\n    scopes: [openid]\n"
    )
    monkeypatch.setenv("GWS_PROJECT", "env-project")
    runner = CliRunner()
    result = runner.invoke(app, ["--config", str(path), "login", "github", "--dry-run"])
    assert result.exit_code == 0, result.exception
    assert "--hostname github.com --scopes repo" in result.stdout
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
        ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
    ]
    assert [line for line in result.output.splitlines() if line.startswith("[")] == ["[docker]", "[hf]", "[uv]"]


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
    provider.responses = [
        response({"client_config_exists": False}),
        response([]),
        enabled,
        client_status(),
        client_status(),
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
    provider.responses = [response({"client_config_exists": False}), response([]), response([])]
    result = CliRunner().invoke(app, ["setup", "workspace", "fixture-project"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1
    assert "remain missing" in str(result.exception)


def test_github_rejected_token_reauthenticates(provider: RecordingRunner) -> None:
    provider.responses = [
        github_status(state="error", error="HTTP 401: Bad credentials (HTTP 401)"),
        PROTOCOL,
        github_status(),
    ]
    result = CliRunner().invoke(app, ["login", "github"])
    assert result.exit_code == 0, result.exception
    assert provider.actions[0][:3] == ["gh", "auth", "login"]


def test_new_github_setup_logs_in_then_reconciles_old_grants(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), PROTOCOL, github_status()]
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
    assert "[uv]" not in result.output
    result = runner.invoke(app, ["--config", str(path), "prune", "all", "--yes"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [
        ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
        ["npm", "cache", "verify"],
    ]


@pytest.mark.parametrize(
    ("environment", "target"),
    [
        ({}, ".cache/huggingface/hub"),
        ({"XDG_CACHE_HOME": "~/xdg"}, "xdg/huggingface/hub"),
        ({"XDG_CACHE_HOME": "~/xdg", "HF_HOME": "$HOME/hf"}, "hf/hub"),
        ({"HF_HOME": "~/hf", "HUGGINGFACE_HUB_CACHE": "$HOME/legacy"}, "legacy"),
        ({"HUGGINGFACE_HUB_CACHE": "~/legacy", "HF_HUB_CACHE": "$HOME/custom"}, "custom"),
    ],
)
def test_hf_cache_creates_the_native_cache_location(
    provider: RecordingRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: dict[str, str],
    target: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HOME", "XDG_CACHE_HOME"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    preview = CliRunner().invoke(app, ["cache", "hf", "--dry-run"])
    assert preview.exit_code == 0
    assert not (tmp_path / target).exists()
    result = CliRunner().invoke(app, ["cache", "hf"])
    assert result.exit_code == 0, result.exception
    assert (tmp_path / target).is_dir()
    assert provider.actions == [["hf", "cache", "ls"]]


def test_workspace_login_opens_the_printed_oauth_url_once(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []
    monkeypatch.setenv("BROWSER", "fixture-browser")
    monkeypatch.setattr(auth.webbrowser, "open", lambda url: opened.append(url) or True)
    provider.responses = [workspace_status(scopes=["openid"]), workspace_status()]
    result = CliRunner().invoke(app, ["login", "workspace"])
    assert result.exit_code == 0, result.exception
    assert provider.relays[0] is not None
    stderr = StringIO()
    relay = auth.browser_opener(auth.State(stderr=stderr))
    relay("Open this URL in your browser to authenticate:\n")
    relay("  https://accounts.google.com/o/oauth2/auth?a=1\n")
    relay("  https://accounts.google.com/o/oauth2/auth?a=2\n")
    assert opened == ["https://accounts.google.com/o/oauth2/auth?a=1"]
    assert "Opened the sign-in page" in stderr.getvalue()


def test_workspace_login_ignores_foreign_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BROWSER", "fixture-browser")
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: pytest.fail("only Google OAuth URLs open"))
    relay = auth.browser_opener(auth.State())
    relay("  https://example.test/?next=https://accounts.google.com/\n")
    relay("https://accounts.google.com/o/oauth2/auth trailing words\n")


def test_browser_requires_a_graphical_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("BROWSER", "DISPLAY", "WAYLAND_DISPLAY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth.sys, "platform", "linux")
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: pytest.fail("console browsers would seize the terminal"))
    assert not auth.open_browser("https://accounts.google.com/o/oauth2/auth")


def test_login_all_skips_every_ready_provider(provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    provider.responses = [github_status(), TOKEN, TOKEN, client_status(), workspace_status()]
    result = CliRunner().invoke(app, ["login", "all"])
    assert result.exit_code == 0, result.exception
    assert not provider.actions
    assert [args[:3] for args in provider.calls] == [
        ["gh", "auth", "status"],
        ["gcloud", "auth", "print-access-token"],
        ADC_PROBE[:3],
        ["gws", "auth", "status"],
        ["gws", "auth", "status"],
    ]


def test_login_all_refreshes_gcloud_before_workspace_setup(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # gws omits enabled APIs when its live gcloud query fails, so setup falls back to gcloud itself.
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    reauth = CommandResult("", "Reauthentication failed.\n\n  $ gcloud auth login\n\nto obtain new credentials.", 1)
    enabled = response([{"config": {"name": api}} for api in Config().auth.workspace.apis])
    provider.responses = [github_status(), reauth, TOKEN, TOKEN, TOKEN, client_status(enabled_apis=None), enabled]
    provider.responses.append(workspace_status())
    result = CliRunner().invoke(app, ["login", "all"])
    assert result.exit_code == 0, result.exception
    assert provider.actions == [["gcloud", "auth", "login"]]
    assert provider.calls[-2][:3] == ["gcloud", "services", "list"]


def test_login_all_without_project_skips_workspace_setup(provider: RecordingRunner) -> None:
    provider.responses = [github_status(), TOKEN, TOKEN, workspace_status()]
    result = CliRunner().invoke(app, ["login", "all"])
    assert result.exit_code == 0, result.exception
    assert "Skipping Workspace setup" in result.stderr
    assert not provider.actions


def test_login_all_reconciles_github_first_and_stops_on_failure(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=[*Config().auth.github.scopes, "delete_repo"])]
    provider.action_code = 17
    result = CliRunner().invoke(app, ["login", "all"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1
    assert "--remove-scopes" in provider.actions[0]


def test_login_all_preview_lists_every_step(provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    result = CliRunner().invoke(app, ["login", "all", "--dry-run"])
    assert result.exit_code == 0, result.exception
    assert not provider.calls
    for command in (
        "gh auth login",
        "--web",
        "gcloud services enable",
        "gws auth setup",
        "gws auth login",
        " ".join(ADC_LOGIN),
    ):
        assert command in result.stdout
