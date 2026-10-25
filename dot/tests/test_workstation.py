"""Public workstation workflows use recorded providers, never real credentials or caches."""

import io
import json
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO, Any, get_args

import pytest
from typer.testing import CliRunner, Result

from fmind_dot import auth
from fmind_dot.cli import app
from fmind_dot.config import CacheProvider, Config, PruneProvider
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.workstation import CACHE_TOOLS, run_prune


def test_setup_without_arguments_shows_help() -> None:
    result = cli(["setup"])
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
    ) -> int:
        assert cwd is None
        assert stdin is not None
        assert stdout is not None
        assert stderr is not None
        self.calls.append(list(args))
        self.actions.append(list(args))
        self.envs.append(env)
        return self.action_code


def cli(arguments: list[str], *, exit_code: int = 0) -> Result:
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == exit_code, f"{result.output}{result.exception!r}"
    return result


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
def provider(monkeypatch: pytest.MonkeyPatch) -> RecordingRunner:
    fake = RecordingRunner()
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
        # A caller's own uv lock timeout would replace the one prune sets.
        "UV_LOCK_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Runner, "which", fake.which)
    monkeypatch.setattr(Runner, "run", fake.run)
    monkeypatch.setattr(Runner, "interactive", fake.interactive)
    # One worker keeps concurrent readiness probes in the order the recorded responses follow.
    monkeypatch.setattr(auth, "PROBE_WORKERS", 1)
    return fake


@pytest.mark.parametrize(
    "arguments",
    [
        ["setup"],
        ["login", "--dry-run"],
        ["login", "colab", "--dry-run"],
        ["login", "github", "--dry-run"],
        ["setup", "github", "--dry-run"],
        ["setup", "workspace", "fixture-project", "--dry-run"],
        ["cache", "--dry-run"],
        ["prune", "all", "--dry-run"],
    ],
)
def test_help_and_preview_never_call_providers(provider: RecordingRunner, arguments: list[str]) -> None:
    cli(arguments)
    assert provider.calls == []


def test_workspace_satisfied_scope_superset_skips_login(provider: RecordingRunner) -> None:
    provider.responses = [workspace_status(scopes=[*Config().auth.workspace.scopes, "extra"])]
    result = cli(["login", "workspace"])
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
    cli(["login", "workspace"])
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
    borrowed = (
        "analytics.readonly",
        "webmasters.readonly",
        "youtube.readonly",
        "yt-analytics.readonly",
        # Management scopes the brain's google CLI narrows its explicit writes to.
        "analytics.edit",
        "analytics.manage.users",
        "business.manage",
        "webmasters",
        # Read-only Admin, Analytics access and Chrome management scopes the google CLI reads with.
        "admin.directory.user.readonly",
        "admin.directory.group.readonly",
        "admin.reports.usage.readonly",
        "analytics.manage.users.readonly",
        "chrome.management.policy.readonly",
        "chrome.management.reports.readonly",
        # Read-only scopes the brain's gws collectors narrow their tokens to, and the audit-log reader.
        "admin.reports.audit.readonly",
        "calendar.readonly",
        "chat.messages.readonly",
        "chat.spaces.readonly",
        "contacts.other.readonly",
        "contacts.readonly",
        "documents.readonly",
        "drive.readonly",
        "forms.responses.readonly",
        "gmail.readonly",
        "meetings.space.readonly",
        "tasks.readonly",
    )
    for scope in borrowed:
        assert f"https://www.googleapis.com/auth/{scope}" in workspace.scopes
    for api in (
        "admin",
        "analyticsadmin",
        "analyticsdata",
        "businessprofileperformance",
        "chromemanagement",
        "chromepolicy",
        "mybusinessaccountmanagement",
        "mybusinessbusinessinformation",
        "pagespeedonline",
        "searchconsole",
        "youtube",
        "youtubeanalytics",
    ):
        assert f"{api}.googleapis.com" in workspace.apis


def test_adc_defaults_own_scopes_borrowed_by_brain_sensors() -> None:
    # ADC login replaces its whole grant: the brain's sensors narrow their tokens to these read-only scopes.
    scopes = Config().auth.gcp.adc_scopes
    for scope in ("bigquery.readonly", "logging.read", "cloud-platform.read-only"):
        assert f"https://www.googleapis.com/auth/{scope}" in scopes


def test_workspace_grant_missing_borrowed_scope_logs_in(provider: RecordingRunner) -> None:
    borrowed = "https://www.googleapis.com/auth/youtube.readonly"
    granted = [scope for scope in Config().auth.workspace.scopes if scope != borrowed]
    provider.responses = [workspace_status(scopes=granted), workspace_status()]
    cli(["login", "workspace"])
    assert borrowed in provider.actions[0][-1].split(",")


ONE_OFF = "https://www.googleapis.com/auth/admin.directory.user.security"


def test_workspace_one_off_grant_extends_the_login_and_names_the_restore(provider: RecordingRunner) -> None:
    configured = Config().auth.workspace.scopes
    provider.responses = [workspace_status(), workspace_status(scopes=[*configured, ONE_OFF])]
    # OpenID Connect names take no URL prefix, so these match configured scopes instead of inventing invalid ones.
    grants = ["--grant", "admin.directory.user.security", "--grant", "email", "--grant", "openid"]
    result = cli(["login", "workspace", *grants])
    assert provider.actions == [["gws", "auth", "login", "--scopes", ",".join([*configured, ONE_OFF])]]
    assert "dot login workspace --force" in result.stderr


@pytest.mark.parametrize(("sommelier", "hinted"), [("1", True), ("", False)])
def test_workspace_login_explains_the_chromeos_loopback_hang(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, sommelier: str, hinted: bool
) -> None:
    monkeypatch.setenv("SOMMELIER_VERSION", sommelier)
    provider.responses = [workspace_status(scopes=["openid"]), workspace_status()]
    result = cli(["login", "workspace"])
    assert ("replace localhost with 127.0.0.1" in result.stderr) is hinted


def test_workspace_lingering_one_off_scope_is_reported_without_login(provider: RecordingRunner) -> None:
    provider.responses = [workspace_status(scopes=[*Config().auth.workspace.scopes, ONE_OFF])]
    result = cli(["login", "workspace"])
    assert not provider.actions
    assert ONE_OFF in result.stderr
    assert "--force" in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["login", "workspace", "--grant", "bad scope"],
        ["login", "github", "--grant", "write public key"],
        ["login", "github", "--grant", "write:public_key", "--check"],
    ],
)
def test_invalid_or_checked_grant_fails_before_probes(provider: RecordingRunner, arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code != 0
    assert not provider.calls


def test_github_one_off_grant_refreshes_and_names_its_removal(provider: RecordingRunner) -> None:
    configured = Config().auth.github.scopes
    provider.responses = [github_status(), github_status(scopes=[*configured, "write:public_key"])]
    result = cli(["login", "github", "--grant", "write:public_key"])
    [refresh] = provider.actions
    assert refresh[:3] == ["gh", "auth", "refresh"]
    assert "write:public_key" in refresh[refresh.index("--scopes") + 1].split(",")
    assert "--remove-scopes" not in refresh
    assert "dot setup github removes write:public_key" in result.stderr


def test_github_one_off_grant_outside_the_policy_names_its_own_removal(provider: RecordingRunner) -> None:
    configured = Config().auth.github.scopes
    provider.responses = [github_status(), github_status(scopes=[*configured, "write:discussion"])]
    result = cli(["login", "github", "--grant", "write:discussion"])
    assert "gh auth refresh -h github.com --remove-scopes write:discussion removes the rest" in result.stderr
    assert "dot setup github removes" not in result.stderr


def test_github_unsatisfied_one_off_grant_is_named_in_the_failure(provider: RecordingRunner) -> None:
    provider.responses = [github_status(), github_status()]
    result = CliRunner().invoke(app, ["login", "github", "--grant", "write:public_key"])
    assert result.exit_code == 1
    assert "configured scope policy and one-off scopes" in str(result.exception)


def test_github_defaults_read_keys_and_packages_but_exclude_their_writes() -> None:
    github = Config().auth.github
    assert {"read:gpg_key", "read:packages", "read:public_key", "read:ssh_signing_key", "project"} <= set(github.scopes)
    one_off = {"write:gpg_key", "write:packages", "write:public_key", "write:ssh_signing_key"}
    assert one_off <= set(github.remove_scopes)
    assert not one_off & set(github.scopes)
    # gh always requests repo, read:org and gist and cannot remove them, so removing one would never settle.
    assert {"gist", "read:org", "repo"} <= set(github.scopes)


@pytest.mark.parametrize("arguments", [["login", "github"], ["setup", "github"]])
def test_github_plaintext_token_warns_after_satisfied_probe(provider: RecordingRunner, arguments: list[str]) -> None:
    provider.responses = [github_status(tokenSource="/home/user/.config/gh/hosts.yml")]
    result = cli(arguments)
    assert not provider.actions
    assert "plaintext hosts.yml" in result.stderr


def test_github_plaintext_token_warns_after_login(provider: RecordingRunner) -> None:
    provider.responses = [
        response({"hosts": {}}),
        PROTOCOL,
        github_status(tokenSource="/home/user/.config/gh/hosts.yml"),
    ]
    result = cli(["login", "github"])
    assert provider.actions[0][:3] == ["gh", "auth", "login"]
    assert "plaintext hosts.yml" in result.stderr
    assert "/home/user" not in result.stderr


@pytest.mark.parametrize("source", ["keyring", "GH_TOKEN", None])
def test_github_keyring_or_environment_token_does_not_warn(provider: RecordingRunner, source: str | None) -> None:
    provider.responses = [github_status() if source is None else github_status(tokenSource=source)]
    result = cli(["login", "github"])
    assert "plaintext" not in result.stderr


def test_github_normalized_grants_skip_login(provider: RecordingRunner) -> None:
    # GitHub reports write:packages alone once it is granted: it implies read:packages.
    scopes = [scope for scope in Config().auth.github.scopes if scope != "read:packages"]
    provider.responses = [github_status(scopes=[*scopes, "write:packages"])]
    cli(["login", "github"])
    assert not provider.actions


def test_github_missing_scopes_refreshes_instead_of_login(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=["repo"]), github_status()]
    cli(["login", "github"])
    assert [args[:3] for args in provider.actions] == [["gh", "auth", "refresh"]]


def test_github_setup_reconciles_excluded_scopes_once(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=[*Config().auth.github.scopes, "delete_repo"]), github_status()]
    cli(["setup", "github"])
    assert len(provider.actions) == 1
    assert "--remove-scopes" in provider.actions[0]


def test_github_admin_signing_key_scope_satisfies_login(provider: RecordingRunner) -> None:
    scopes = [scope for scope in Config().auth.github.scopes if scope != "read:ssh_signing_key"]
    provider.responses = [github_status(scopes=[*scopes, "admin:ssh_signing_key"])]
    cli(["login", "github"])
    assert not provider.actions


def test_github_setup_removes_one_off_writes_and_keeps_key_reads(provider: RecordingRunner) -> None:
    granted = [*Config().auth.github.scopes, "admin:org", "write:public_key", "write:ssh_signing_key"]
    provider.responses = [github_status(scopes=granted), github_status()]
    cli(["setup", "github"])
    [refresh] = provider.actions
    requested = set(refresh[refresh.index("--scopes") + 1].split(","))
    removed = set(refresh[refresh.index("--remove-scopes") + 1].split(","))
    assert {"read:public_key", "read:ssh_signing_key"} <= requested
    assert {
        "admin:org",
        "delete_repo",
        "write:packages",
        "write:public_key",
        "write:ssh_signing_key",
    } <= removed
    assert not requested & removed


def test_github_setup_already_satisfied_skips_refresh(provider: RecordingRunner) -> None:
    provider.responses = [github_status()]
    cli(["setup", "github"])
    assert not provider.actions


def test_github_no_accounts_logs_in_through_the_web_with_configured_protocol(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), PROTOCOL, github_status()]
    cli(["login", "github"])
    assert provider.actions[0][:3] == ["gh", "auth", "login"]
    assert provider.actions[0][-3:] == ["--web", "--git-protocol", "ssh"]
    assert provider.calls[1] == ["gh", "config", "get", "git_protocol", "--host", "github.com"]


@pytest.mark.parametrize("protocol", [CommandResult("", "private", 1), CommandResult("ftp\n", "", 0)])
def test_github_unknown_protocol_keeps_the_native_prompt(provider: RecordingRunner, protocol: CommandResult) -> None:
    provider.responses = [response({"hosts": {}}), protocol, github_status()]
    result = cli(["login", "github"])
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
    cli(["login", "github"])
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
    result = cli(["login", "gcp"])
    assert not provider.actions
    assert provider.calls == [["gcloud", "auth", "print-access-token"], ADC_PROBE]
    assert "private" not in result.output


@pytest.mark.parametrize("adc", [CommandResult("", "Your default credentials were not found", 1), SCOPE_GAP])
def test_missing_or_narrow_adc_relogs_only_adc_with_configured_scopes(
    provider: RecordingRunner, adc: CommandResult
) -> None:
    # gcloud auth login --update-adc would replace the ADC grant with defaults and drop Colab's scope.
    provider.responses = [TOKEN, adc, TOKEN, TOKEN]
    result = cli(["login", "gcp"])
    assert provider.actions == [ADC_LOGIN]
    assert "https://www.googleapis.com/auth/colaboratory" in ADC_SCOPES
    assert "private" not in result.output


def test_gcp_force_runs_both_logins_and_verifies(provider: RecordingRunner) -> None:
    provider.responses = [TOKEN, TOKEN]
    cli(["login", "gcp", "--force"])
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
    result = cli(["login", "gcp"])
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
    result = cli(["login", "colab"])
    assert provider.calls == [ADC_PROBE, COLAB_SESSIONS]
    assert "private" not in result.output


def test_colab_missing_scope_requests_the_configured_grant(provider: RecordingRunner) -> None:
    provider.responses = [SCOPE_GAP, COLAB_LISTING]
    result = cli(["login", "colab"])
    assert provider.calls == [ADC_PROBE, ADC_LOGIN, COLAB_SESSIONS]
    assert "private" not in result.output


def test_colab_force_requests_the_grant_without_probing(provider: RecordingRunner) -> None:
    provider.responses = [COLAB_LISTING]
    cli(["login", "colab", "--force"])
    assert provider.calls == [ADC_LOGIN, COLAB_SESSIONS]


def test_colab_requires_its_scopes_in_the_adc_policy(provider: RecordingRunner, tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("auth:\n  gcp:\n    adc_scopes: [openid]\n")
    result = CliRunner().invoke(app, ["--config", str(path), "login", "colab", "--dry-run"])
    assert result.exit_code != 0
    assert "colaboratory" in str(result.exception)
    assert not provider.calls


def test_colab_preview_includes_scopes_and_session_check(provider: RecordingRunner) -> None:
    result = cli(["login", "colab", "--dry-run"])
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
    cli(["setup", "workspace", "fixture-project"])
    assert not provider.actions
    assert provider.calls == [["gws", "auth", "status"]]


def test_setup_workspace_enables_apis_missing_from_gws_status(provider: RecordingRunner) -> None:
    apis = Config().auth.workspace.apis
    provider.responses = [client_status(enabled_apis=apis[1:]), response([{"config": {"name": api}} for api in apis])]
    cli(["setup", "workspace", "fixture-project"])
    assert provider.actions == [["gcloud", "services", "enable", apis[0], "--project", "fixture-project", "--quiet"]]
    assert provider.calls[0] == ["gws", "auth", "status"]


def test_setup_workspace_other_project_lists_apis_with_gcloud(provider: RecordingRunner) -> None:
    provider.responses = [
        client_status(project_id="other-project", enabled_apis=[]),
        response([{"config": {"name": api}} for api in Config().auth.workspace.apis]),
        client_status(),
    ]
    cli(["setup", "workspace", "fixture-project"])
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
    cli(["setup", "workspace", *args], exit_code=2)
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
    result = cli(["cache"])
    assert provider.actions == [
        ["docker", "system", "df"],
        ["hf", "cache", "ls"],
        ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
    ]
    assert [line for line in result.output.splitlines() if line.startswith("[")] == ["[docker]", "[hf]", "[uv]"]


def test_cache_json_parses_native_reports_without_stderr(provider: RecordingRunner) -> None:
    provider.responses = [
        CommandResult('{"Type":"Images","Size":"1GB"}\n{"Type":"Containers","Size":"0B"}\n', "", 0),
        CommandResult('[{"repo_id":"org/model"}]', "", 0),
        CommandResult("1024\n", "SECRET-DIAGNOSTIC", 0),
    ]
    result = cli(["cache", "--json"])
    document = json.loads(result.stdout)
    assert document["schema"] == "dot.cache/v1"
    reports = {entry["name"]: entry["report"] for entry in document["providers"]}
    assert reports == {
        "docker": [{"Type": "Images", "Size": "1GB"}, {"Type": "Containers", "Size": "0B"}],
        "hf": [{"repo_id": "org/model"}],
        "uv": {"bytes": 1024},
    }
    assert "SECRET-DIAGNOSTIC" not in result.output
    assert not provider.actions


def test_cache_json_reports_a_failed_provider_and_exits_nonzero(provider: RecordingRunner) -> None:
    provider.responses = [CommandResult("", "boom", 3)]
    result = cli(["cache", "uv", "--json"], exit_code=1)
    entry = json.loads(result.stdout)["providers"][0]
    assert entry["error"].startswith("exit 3; run uv cache size")
    assert "boom" not in result.output


def test_cache_json_keeps_other_providers_when_one_times_out(provider: RecordingRunner) -> None:
    provider.responses = [
        CommandTimeoutError("command timed out: docker"),
        CommandResult("[]", "", 0),
        CommandResult("1024\n", "", 0),
    ]
    result = cli(["cache", "--json"], exit_code=1)
    entries = {entry["name"]: entry for entry in json.loads(result.stdout)["providers"]}
    assert entries["docker"]["error"].startswith("timed out after 120s")
    assert entries["uv"]["report"] == {"bytes": 1024}


def test_cache_text_continues_past_a_failed_provider_and_exits_nonzero(provider: RecordingRunner) -> None:
    provider.action_code = 1
    result = cli(["cache"], exit_code=1)
    assert [args[0] for args in provider.actions] == ["docker", "hf", "uv"]
    assert "cache inspection failed for docker, hf, uv" in str(result.exception)


def test_cache_json_keeps_other_reports_when_a_provider_cannot_start(provider: RecordingRunner) -> None:
    provider.responses = [OSError("SECRET-DIAGNOSTIC"), CommandResult("[]", "", 0), CommandResult("1024\n", "", 0)]
    result = cli(["cache", "--json"], exit_code=1)
    entries = {entry["name"]: entry for entry in json.loads(result.stdout)["providers"]}
    assert entries["docker"]["error"].startswith("could not start cache inspection")
    assert entries["uv"]["report"] == {"bytes": 1024}
    assert "SECRET-DIAGNOSTIC" not in result.output


@pytest.mark.parametrize("as_json", [False, True])
def test_cache_continues_when_hf_directory_is_unusable(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, as_json: bool
) -> None:
    cache = tmp_path / "private-hf-cache"
    cache.write_text("occupied")
    monkeypatch.setenv("HF_HUB_CACHE", str(cache))
    provider.responses = [CommandResult("[]", "", 0), CommandResult("1024\n", "", 0)]
    result = cli(["cache", *(["--json"] if as_json else [])], exit_code=1)
    if as_json:
        entries = {entry["name"]: entry for entry in json.loads(result.stdout)["providers"]}
        assert entries["hf"]["error"].startswith("could not start cache inspection")
        assert entries["uv"]["report"] == {"bytes": 1024}
    else:
        assert [args[0] for args in provider.actions] == ["docker", "uv"]
        assert "cache inspection failed for hf" in str(result.exception)
    assert str(cache) not in result.output


def test_cache_all_skips_missing_tools_but_an_explicit_provider_requires_it(provider: RecordingRunner) -> None:
    provider.missing.add("docker")
    provider.responses = [CommandResult("[]", "", 0), CommandResult("1024\n", "", 0)]
    result = cli(["cache", "--json"])
    entries = {entry["name"]: entry for entry in json.loads(result.stdout)["providers"]}
    assert entries["docker"]["skipped"] == "docker not installed"
    text = CliRunner().invoke(app, ["cache"])
    assert "[docker] skipped: docker not installed" in text.output
    explicit = CliRunner().invoke(app, ["cache", "docker"])
    assert explicit.exit_code != 0


def test_cache_rejects_unknown_providers(provider: RecordingRunner) -> None:
    cli(["cache", "npm"], exit_code=2)
    assert not provider.calls


def test_cache_registry_covers_every_configurable_provider() -> None:
    assert set(get_args(PruneProvider)) == set(CACHE_TOOLS)
    assert all(CACHE_TOOLS[name].inspect and CACHE_TOOLS[name].inspect_json for name in get_args(CacheProvider))


def test_cache_json_dry_run_lists_commands_without_probes(provider: RecordingRunner) -> None:
    result = cli(["cache", "--json", "--dry-run"])
    document = json.loads(result.stdout)
    assert document["dry_run"] is True
    assert document["providers"][0]["command"] == "docker system df --format json"
    assert not provider.calls


def test_prune_default_runs_unattended_and_only_drops_stale_entries(provider: RecordingRunner) -> None:
    result = cli(["prune"])

    assert provider.actions == [
        ["hf", "cache", "prune", "--yes"],
        ["mise", "cache", "clear"],
        ["npm", "cache", "verify"],
        ["trivy", "clean", "--scan-cache"],
        ["uv", "cache", "prune"],
    ]
    # dprint has no safe tier: clearing its plugins would break offline formatting and commit hooks.
    assert "[dprint] skipped: only --aggressive clears it" in result.stdout
    # A running `uv run` holds the cache lock, so uv fails fast instead of waiting or forcing.
    assert provider.envs[-1] == {"UV_LOCK_TIMEOUT": "10"}
    assert all(env is None for env in provider.envs[:-1])


def test_prune_aggressive_asks_first_then_empties_whole_caches(provider: RecordingRunner) -> None:
    refused = CliRunner().invoke(app, ["prune", "--aggressive"])
    assert refused.exit_code == 1
    assert "requires confirmation" in str(refused.exception)
    assert not provider.actions

    cli(["prune", "--aggressive", "--yes"])

    assert provider.actions == [
        ["dprint", "clear-cache"],
        ["hf", "cache", "prune", "--yes"],
        ["mise", "cache", "clear"],
        ["npm", "cache", "clean", "--force"],
        ["trivy", "clean", "--all"],
        ["uv", "cache", "clean"],
    ]


class _TerminalInput(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_prune_aggressive_asks_only_about_caches_it_empties(provider: RecordingRunner) -> None:
    prompts = io.StringIO()
    state = State(stdin=_TerminalInput("y\n"), stdout=io.StringIO(), stderr=prompts)
    state.__dict__["_config"] = Config()
    run_prune(state, ["hf", "uv"], aggressive=True)
    assert "Empty the whole caches for uv (" in prompts.getvalue()

    # hf has no aggressive step, so its default cleanup runs without a prompt or terminal.
    cli(["prune", "hf", "--aggressive"])
    assert provider.actions == [
        ["hf", "cache", "prune", "--yes"],
        ["uv", "cache", "clean"],
        ["hf", "cache", "prune", "--yes"],
    ]


@pytest.mark.parametrize(
    ("command", "providers"), [("cache", get_args(CacheProvider)), ("prune", get_args(PruneProvider))]
)
def test_cache_and_prune_complete_provider_names(
    monkeypatch: pytest.MonkeyPatch, command: str, providers: tuple[str, ...]
) -> None:
    monkeypatch.setenv("_DOT_COMPLETE", "complete_fish")
    monkeypatch.setenv("_TYPER_COMPLETE_FISH_ACTION", "get-args")
    monkeypatch.setenv("_TYPER_COMPLETE_ARGS", f"dot {command} ")
    result = CliRunner().invoke(app, prog_name="dot")
    assert result.stdout.split() == ["all", *providers]


def test_docker_prune_requires_explicit_selection(provider: RecordingRunner) -> None:
    cli(["prune", "docker"])
    cli(["prune", "docker", "--aggressive", "--yes"])
    assert provider.actions == [
        ["docker", "builder", "prune", "--force"],
        ["docker", "builder", "prune", "--all", "--force"],
    ]


def test_prune_rejects_unknown_providers(provider: RecordingRunner) -> None:
    result = CliRunner().invoke(app, ["prune", "pip"])
    assert result.exit_code == 2
    assert not provider.calls


def test_prune_missing_tools_fails_before_any_cleanup(provider: RecordingRunner) -> None:
    provider.missing.add("uv")
    result = CliRunner().invoke(app, ["prune", "all", "--yes"])
    assert result.exit_code != 0
    assert not provider.actions


def test_native_failure_continues_and_names_the_failed_providers(provider: RecordingRunner) -> None:
    provider.action_code = 17
    result = CliRunner().invoke(app, ["prune"])
    assert result.exit_code == 1
    # One busy or broken cache must not block the others.
    assert len(provider.actions) == 5
    assert str(result.exception) == (
        "cache cleanup failed for hf, mise, npm, trivy, uv; the other providers were cleaned"
    )
    assert "if a running `uv run` process holds the cache" in result.stderr


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
    cli(["login", "github"])
    assert provider.actions[0][:3] == ["gh", "auth", "login"]


def test_new_github_setup_logs_in_then_reconciles_old_grants(provider: RecordingRunner) -> None:
    provider.responses = [response({"hosts": {}}), PROTOCOL, github_status()]
    cli(["setup", "github"])
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
    cli(["cache", "hf"])
    assert (tmp_path / target).is_dir()
    assert provider.actions == [["hf", "cache", "ls"]]


def workspace_client_status(**kwargs: Any) -> CommandResult:
    """gws reports its OAuth client and token in one status, shared by Workspace setup and login."""
    return response({**json.loads(client_status().stdout), **json.loads(workspace_status().stdout), **kwargs})


def test_login_skips_every_ready_provider_with_one_probe_each(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    provider.responses = [github_status(), TOKEN, TOKEN, workspace_client_status()]
    cli(["login"])
    assert not provider.actions
    assert [args[:3] for args in provider.calls] == [
        ["gh", "auth", "status"],
        ["gcloud", "auth", "print-access-token"],
        ADC_PROBE[:3],
        ["gws", "auth", "status"],
    ]


@pytest.mark.usefixtures("provider")
def test_login_probes_providers_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "PROBE_WORKERS", 4)
    barrier = threading.Barrier(4, timeout=5)
    answers = {"gh": github_status(), "gcloud": TOKEN, "gws": workspace_status()}

    def run(args: Sequence[str], **_: Any) -> CommandResult:
        # Every probe waits for the other three, so a sequential run would time out.
        barrier.wait()
        return answers[args[0]]

    monkeypatch.setattr(Runner, "run", lambda _self, args, **options: run(args, **options))
    result = cli(["login", "--check"])
    assert result.stdout.splitlines() == ["github: ready", "gcp: ready", "workspace: ready"]


def test_login_reconciles_only_the_machine_providers_in_dependency_order(
    provider: RecordingRunner, tmp_path: Path
) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("auth:\n  login: [colab, workspace, gcp]\n", encoding="utf-8")
    provider.responses = [TOKEN, TOKEN, workspace_status(), CommandResult("session\n", "", 0)]
    result = cli(["--config", str(path), "login"])
    assert not provider.actions
    assert [args[0] for args in provider.calls] == ["gcloud", "gcloud", "gws", "colab"]
    assert result.stderr.index("Google Cloud") < result.stderr.index("Workspace is") < result.stderr.index("Colab")


def test_login_rejects_group_options_before_a_provider(provider: RecordingRunner) -> None:
    result = cli(["login", "--check", "gcp"], exit_code=2)
    assert "dot login gcp --check" in result.output
    assert not provider.calls


def test_machine_login_refreshes_gcloud_before_workspace_setup(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # gws omits enabled APIs when its live gcloud query fails, so setup falls back to gcloud itself.
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    reauth = CommandResult("", "Reauthentication failed.\n\n  $ gcloud auth login\n\nto obtain new credentials.", 1)
    enabled = response([{"config": {"name": api}} for api in Config().auth.workspace.apis])
    stale = workspace_client_status(enabled_apis=None)
    # The gcloud login invalidates the first gws status, which embeds a live gcloud query.
    provider.responses = [github_status(), reauth, TOKEN, stale, TOKEN, TOKEN, stale, enabled]
    cli(["login"])
    assert provider.actions == [["gcloud", "auth", "login"]]
    assert provider.calls[-1][:3] == ["gcloud", "services", "list"]


def test_machine_login_rejects_invalid_project_before_any_login(
    provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GWS_PROJECT", "Not A Project")
    result = cli(["login", "--dry-run"], exit_code=1)
    assert "fix GWS_PROJECT or auth.workspace.project" in str(result.exception)
    assert not provider.calls
    assert result.stdout == ""


def test_machine_login_without_project_skips_workspace_setup(provider: RecordingRunner) -> None:
    provider.responses = [github_status(), TOKEN, TOKEN, workspace_status()]
    result = cli(["login"])
    assert "Skipping Workspace setup" in result.stderr
    assert not provider.actions


def test_machine_login_reconciles_github_first_and_stops_on_failure(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=[*Config().auth.github.scopes, "delete_repo"]), TOKEN, TOKEN]
    provider.responses.append(workspace_status())
    provider.action_code = 17
    result = CliRunner().invoke(app, ["login"])
    assert result.exit_code != 0
    assert len(provider.actions) == 1
    assert "--remove-scopes" in provider.actions[0]


def test_machine_login_preview_lists_every_step(provider: RecordingRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GWS_PROJECT", "fixture-project")
    result = cli(["login", "--dry-run"])
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


def test_login_check_reports_readiness_without_authenticating(provider: RecordingRunner) -> None:
    provider.responses = [github_status()]
    ready = CliRunner().invoke(app, ["login", "github", "--check"])
    assert ready.exit_code == 0, ready.exception
    assert ready.stdout == "github: ready\n"
    assert not provider.actions


def test_machine_login_check_exits_one_and_names_each_provider(provider: RecordingRunner) -> None:
    provider.responses = [github_status(scopes=["repo"]), TOKEN, SCOPE_GAP, workspace_status()]
    result = cli(["login", "--check"], exit_code=1)
    assert result.stdout.splitlines() == ["github: login needed", "gcp: login needed", "workspace: ready"]
    assert "Run dot login in a terminal" in result.stderr
    assert "private" not in result.output
    assert not provider.actions


def test_login_check_waits_for_a_timed_out_probe_only_once(provider: RecordingRunner) -> None:
    provider.responses = [CommandTimeoutError("command timed out: gws")]
    result = cli(["login", "workspace", "--check"], exit_code=1)
    assert result.stdout.startswith("workspace: unknown (")
    assert provider.calls == [["gws", "auth", "status"]]


def test_login_check_reports_unknown_state_and_rejects_conflicting_flags(provider: RecordingRunner) -> None:
    provider.responses = [response({"unexpected": True})]
    unknown = CliRunner().invoke(app, ["login", "workspace", "--check"])
    assert unknown.exit_code == 1
    assert unknown.stdout.startswith("workspace: unknown (")
    conflict = CliRunner().invoke(app, ["login", "gcp", "--check", "--force"])
    assert conflict.exit_code == 2
    assert not provider.actions
