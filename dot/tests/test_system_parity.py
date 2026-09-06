from __future__ import annotations

import json
import stat
from collections.abc import Callable, Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import IO

import pytest
import typer
from typer.core import TyperGroup, TyperOption
from typer.main import get_command
from typer.testing import CliRunner

import fmind_dot.system as system
from fmind_dot.config import Config, SecretConfig, ToolConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State

RunHandler = Callable[[list[str], Path | None, str | None, bool], CommandResult]
_WHEEL_SHA256 = "a" * 64


class ScriptedRunner(Runner):
    def __init__(
        self,
        installed: set[str] | None = None,
        *,
        run: RunHandler | None = None,
        interactive_codes: Mapping[str, int] | None = None,
    ) -> None:
        self.installed = installed or set()
        self.run_handler = run
        self.interactive_codes = interactive_codes or {}
        self.calls: list[list[str]] = []
        self.output_limits: list[int | None] = []
        self.interactive_calls: list[list[str]] = []

    def which(self, command: str) -> Path | None:
        return Path("/bin") / command if command in self.installed else None

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
        del env, timeout
        command = list(args)
        self.calls.append(command)
        result = self.run_handler(command, cwd, input_text, check) if self.run_handler else CommandResult("ok\n", "", 0)
        if check and result.returncode != 0:
            raise DotError(f"command failed ({result.returncode}): {command[0]}")
        return result

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
        self.output_limits.append(max_output_bytes)
        return self.run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)

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
        del cwd, stdin, stdout, stderr, env
        command = list(args)
        self.interactive_calls.append(command)
        return self.interactive_codes.get(command[0], 0)


def state_with(runner: Runner, config: Config | None = None, *, stdin: str = "") -> State:
    state = State(runner=runner, stdin=StringIO(stdin), stdout=StringIO(), stderr=StringIO())
    state._config = config or Config()  # noqa: SLF001 - command boundary dependency injection.
    return state


def test_completion_falls_back_for_empty_custom_output_but_not_for_standard_failure() -> None:
    config = Config()
    config.completions.custom_commands["custom"] = ToolConfig(args=["completions", "fish"])

    def empty_then_fallback(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult("# fallback\n" if args[1:] == ["completion", "fish"] else "", "", 0)

    runner = ScriptedRunner({"custom"}, run=empty_then_fallback)
    assert system._generate_completion(state_with(runner, config), "custom") == "# fallback\n"  # noqa: SLF001
    assert [call[1:] for call in runner.calls] == [["completions", "fish"], ["completion", "fish"]]

    failing = ScriptedRunner(
        {"plain"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("", "private-provider-payload", 7),
    )
    with pytest.raises(DotError, match="failed to generate completions for plain"):
        system._generate_completion(state_with(failing), "plain")  # noqa: SLF001
    assert failing.calls == [["plain", "completion", "fish"]]


def test_completion_publication_is_atomic_and_sets_private_cache_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completions = tmp_path / "completions"
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    config = Config()
    config.completions.path = str(completions)
    config.completions.tools = []

    def scripts(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, check
        if args[0] == "fish":
            assert input_text
            assert input_text.strip()
            return CommandResult("", "", 0)
        if Path(args[0]).name.startswith("python"):
            return CommandResult("", "recursive completion generation is not portable", 9)
        return CommandResult(f"# generated by {Path(args[0]).name}\n", "", 0)

    runner = ScriptedRunner({"fish", "atuin", "carapace"}, run=scripts)
    system.run_completion(state_with(runner, config))

    assert stat.S_IMODE((cache / "fish").stat().st_mode) == 0o700
    assert stat.S_IMODE((cache / "fish/atuin-init.fish").stat().st_mode) == 0o600
    assert stat.S_IMODE((cache / "fish/carapace-init.fish").stat().st_mode) == 0o600
    assert stat.S_IMODE((completions / "dot.fish").stat().st_mode) == 0o644
    assert "_DOT_COMPLETE=complete_fish" in (completions / "dot.fish").read_text(encoding="utf-8")
    assert all(not Path(call[0]).name.startswith("python") for call in runner.calls)
    assert list(completions.glob(".dot.fish.*")) == []


def test_completion_validation_preserves_last_known_good_file(tmp_path: Path) -> None:
    target = tmp_path / "tool.fish"
    target.write_text("# known good\n", encoding="utf-8")
    target.chmod(0o600)

    runner = ScriptedRunner(
        {"fish"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("", "private syntax diagnostic", 1),
    )
    with pytest.raises(DotError, match="failed syntax validation"):
        system._write_validated_fish(state_with(runner), target, "if true\n", 0o644)  # noqa: SLF001
    assert target.read_text(encoding="utf-8") == "# known good\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".tool.fish.*")) == []


def test_completion_collects_both_shell_integration_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    config = Config()
    config.completions.path = str(tmp_path / "completions")
    config.completions.tools = []

    def fail_integrations(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult("# dot\n", "", 0) if args[0] not in {"atuin", "carapace"} else CommandResult("", "", 9)

    runner = ScriptedRunner({"fish", "atuin", "carapace"}, run=fail_integrations)
    with pytest.raises(DotError) as raised:
        system.run_completion(state_with(runner, config))
    assert "atuin-init.fish" in str(raised.value)
    assert "carapace-init.fish" in str(raised.value)


def test_login_and_setup_failures_name_the_failed_operation() -> None:
    gcloud = ScriptedRunner({"gcloud"}, interactive_codes={"gcloud": 7})
    with pytest.raises(DotError, match=r"gcloud login failed \(7\)"):
        system.run_login_gcp(state_with(gcloud))
    assert gcloud.interactive_calls == [["gcloud", "auth", "login", "--update-adc"]]

    setup = ScriptedRunner({"gcloud", "gws"}, interactive_codes={"gcloud": 8})
    with pytest.raises(DotError, match=r"failed to enable gcloud services \(8\)"):
        system.run_setup_workspace(state_with(setup), "project-1")
    assert setup.interactive_calls[0][-3:] == ["--project", "project-1", "--quiet"]


def test_github_login_confirmation_defaults_to_cancel_and_preserves_argv() -> None:
    runner = ScriptedRunner({"gh"})
    canceled = state_with(runner, stdin="\n")
    system.run_login_github(canceled)
    assert runner.interactive_calls == []
    assert isinstance(canceled.stdout, StringIO)
    assert "Canceled." in canceled.stdout.getvalue()

    accepted = state_with(runner, stdin="yes\n")
    system.run_login_github(accepted)
    assert runner.interactive_calls[-1] == [
        "gh",
        "auth",
        "login",
        "--hostname",
        "github.com",
        "--scopes",
        "gist,notifications,read:org,repo,user",
    ]


def test_login_wrappers_cover_success_and_missing_tool() -> None:
    with pytest.raises(DotError, match="required tool is not installed: gws"):
        system.run_login_workspace(state_with(ScriptedRunner()))

    runner = ScriptedRunner({"gws", "gcloud"})
    workspace = state_with(runner)
    system.run_login_workspace(workspace)
    system.run_login_gcp(workspace)
    assert runner.interactive_calls[0][:3] == ["gws", "auth", "login"]
    assert runner.interactive_calls[1] == ["gcloud", "auth", "login", "--update-adc"]
    assert isinstance(workspace.stdout, StringIO)
    assert "credentials successfully updated" in workspace.stdout.getvalue()


def test_workspace_setup_requires_project_and_configured_apis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    runner = ScriptedRunner({"gws", "gcloud"})
    with pytest.raises(DotError, match="provide a project ID"):
        system.run_setup_workspace(state_with(runner))

    config = Config()
    config.setup.workspace_apis = []
    monkeypatch.setenv("GWS_PROJECT", "from-env")
    with pytest.raises(DotError, match="no Google Workspace APIs configured"):
        system.run_setup_workspace(state_with(runner, config))


def test_completion_generation_reports_missing_generators_and_fallback_failures() -> None:
    config = Config()
    config.completions.custom_commands["custom"] = ToolConfig(binary="helper", args=["generate"])
    with pytest.raises(FileNotFoundError, match="missing"):
        system._generate_completion(state_with(ScriptedRunner(), config), "missing")  # noqa: SLF001
    with pytest.raises(DotError, match="generator for custom is not installed"):
        system._generate_completion(state_with(ScriptedRunner({"custom"}), config), "custom")  # noqa: SLF001

    def failing_fallback(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args == ["helper", "generate"]:
            return CommandResult("", "", 0)
        raise OSError("provider-private")

    runner = ScriptedRunner({"custom", "helper"}, run=failing_fallback)
    with pytest.raises(DotError, match="failed to generate completions for custom") as raised:
        system._generate_completion(state_with(runner, config), "custom")  # noqa: SLF001
    assert "provider-private" not in str(raised.value)


def test_completion_run_skips_missing_tools_and_reports_failed_generators(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    config = Config()
    config.completions.path = str(tmp_path / "completions")
    config.completions.tools = ["missing", "broken"]

    def scripts(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "fish":
            return CommandResult("", "", 0)
        return CommandResult("", "private", 7)

    state = state_with(ScriptedRunner({"fish", "broken"}, run=scripts), config)
    with pytest.raises(DotError, match="broken: failed to generate completions for broken"):
        system.run_completion(state)
    assert isinstance(state.stdout, StringIO)
    output = state.stdout.getvalue()
    assert "missing is not installed, skipping" in output
    assert "Failed to generate completions for broken" in output


def test_completion_rejects_empty_scripts_before_replacing_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "tool.fish"
    target.write_text("# known good\n", encoding="utf-8")

    with pytest.raises(DotError, match="generated Fish script is empty"):
        system._write_validated_fish(state_with(ScriptedRunner()), target, " \n", 0o644)  # noqa: SLF001

    assert target.read_text(encoding="utf-8") == "# known good\n"


def test_notification_commands_cover_linux_fallback_and_darwin_escaping() -> None:
    linux = system.notification_command(
        ScriptedRunner({"gdbus"}),
        system.Notification("Done", "Turn finished", ("~/dot",)),
        system="linux",
    )
    assert linux[0] == "gdbus"
    assert {"uint32 0", "@as []", "@a{sv} {}", "int32 10000"} <= set(linux)

    darwin = system.notification_command(
        ScriptedRunner(),
        system.Notification('Done "now"', "Turn finished", (r"~/a\b",)),
        system="darwin",
    )
    assert darwin[0:2] == ["osascript", "-e"]
    assert r"Done \"now\"" in darwin[2]
    assert r"~/a\\b" in darwin[2]


def test_notification_validation_and_minimal_platform_commands(tmp_path: Path) -> None:
    with pytest.raises(DotError, match="agent name is required"):
        system.build_notification("", "stop", None, tmp_path, {}.get)
    with pytest.raises(DotError, match="unknown agent notify event"):
        system.build_notification("codex", "unknown", None, tmp_path, {}.get)

    minimal = system.build_notification("custom", "session-end", None, tmp_path, {}.get)
    assert minimal == system.Notification("🏁 custom", "Session ended")
    assert (
        'display notification "Session ended"'
        in system.notification_command(ScriptedRunner(), minimal, system="darwin")[2]
    )

    session_only = system.build_notification(
        "codex",
        "stop",
        tmp_path / "outside",
        tmp_path / "home",
        {"ZELLIJ_SESSION_NAME": "work"}.get,
    )
    assert session_only.details == (str(tmp_path / "outside"), "zellij work")

    with pytest.raises(DotError, match="unsupported on plan9"):
        system.notification_command(ScriptedRunner(), minimal, system="plan9")
    with pytest.raises(DotError, match="install notify-send or gdbus"):
        system.notification_command(ScriptedRunner(), minimal, system="linux")


def test_hook_payload_is_strict_and_run_notify_honors_idle_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    class TTYInput(StringIO):
        def isatty(self) -> bool:
            return True

    tty_state = state_with(ScriptedRunner())
    tty_state.stdin = TTYInput("ignored")
    assert system._hook_payload(tty_state) == {}  # noqa: SLF001 - hook input is a trust boundary.
    assert system._hook_payload(state_with(ScriptedRunner(), stdin="  \n")) == {}  # noqa: SLF001
    with pytest.raises(DotError, match="failed to parse agent hook input"):
        system._hook_payload(state_with(ScriptedRunner(), stdin="{"))  # noqa: SLF001
    with pytest.raises(DotError, match="expected a JSON object"):
        system._hook_payload(state_with(ScriptedRunner(), stdin="[]"))  # noqa: SLF001

    delivered: list[system.Notification] = []
    monkeypatch.setattr(system, "send_notification", lambda _state, notification: delivered.append(notification))
    with pytest.raises(DotError, match="agent name or notification summary"):
        system.run_notify(state_with(ScriptedRunner()), [])

    system.run_notify(state_with(ScriptedRunner()), ["Summary", "Headline", "detail"])
    system.run_notify(
        state_with(ScriptedRunner(), stdin='{"stopHookActive":true}'),
        ["codex", "stop"],
    )
    system.run_notify(
        state_with(ScriptedRunner(), stdin='{"fullyIdle":false}'),
        ["antigravity", "stop"],
    )
    system.run_notify(state_with(ScriptedRunner(), stdin="{}"), ["agy", "stop"])
    with pytest.raises(DotError, match="stopHookActive must be a boolean"):
        system.run_notify(
            state_with(ScriptedRunner(), stdin='{"stopHookActive":"false"}'),
            ["agy", "stop"],
        )
    with pytest.raises(DotError, match="fullyIdle must be a boolean"):
        system.run_notify(
            state_with(ScriptedRunner(), stdin='{"fullyIdle":1}'),
            ["agy", "stop"],
        )
    system.run_notify(
        state_with(ScriptedRunner(), stdin='{"fullyIdle":true,"workspacePaths":[null,"","/workspace/project"]}'),
        ["agy", "needs-input"],
    )

    assert delivered[0] == system.Notification("Summary", "Headline", ("detail",))
    assert delivered[1].summary == "⏳ Antigravity · project"


def test_run_notify_accepts_direct_hook_cwd_and_ignores_invalid_workspace_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delivered: list[system.Notification] = []
    monkeypatch.setattr(system, "send_notification", lambda _state, notification: delivered.append(notification))

    system.run_notify(
        state_with(ScriptedRunner(), stdin='{"cwd":"/workspace/direct"}'),
        ["codex", "session-end"],
    )
    system.run_notify(
        state_with(ScriptedRunner(), stdin='{"workspacePaths":"invalid"}'),
        ["codex", "stop"],
    )

    assert delivered[0].summary == "🏁 Codex · direct"
    assert delivered[1].summary == "✅ Codex"


def test_notification_dispatch_skips_unsupported_hosts_and_redacts_backend_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = ScriptedRunner(
        {"notify-send"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("", "oauth-token=secret", 4),
    )
    state = state_with(runner)
    monkeypatch.setattr(system.platform, "system", lambda: "Plan9")
    system.send_notification(state, system.Notification("Done"))
    assert runner.calls == []

    monkeypatch.setattr(system.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")
    with pytest.raises(DotError, match="failed to send desktop notification with notify-send") as raised:
        system.send_notification(state, system.Notification("Done"))
    assert "secret" not in str(raised.value)


def _minimal_verify_config() -> Config:
    config = Config()
    config.verify.env_vars.required = []
    config.verify.env_vars.optional = []
    config.verify.secrets = []
    config.verify.tools = []
    return config


def test_verify_probes_path_visible_tools_and_redacts_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    config = _minimal_verify_config()
    config.verify.tools = ["healthy", "broken"]

    def probe(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "/bin/broken":
            return CommandResult("token=stdout-secret", "token=stderr-secret", 3)
        return CommandResult("healthy", "", 0)

    runner = ScriptedRunner({"healthy", "broken", "docker"}, run=probe)
    results = system.run_verify(state_with(runner, config), fix=False)
    by_name = {item["name"]: item for item in results["tools"]}
    assert by_name["healthy"]["status"] == "pass"
    assert by_name["broken"]["status"] == "fail"
    assert by_name["broken"]["condition"] == "broken"
    assert all(limit == system._PROBE_OUTPUT_LIMIT_BYTES for limit in runner.output_limits)  # noqa: SLF001
    encoded = json.dumps(results)
    assert "stdout-secret" not in encoded
    assert "stderr-secret" not in encoded


def test_verify_requires_nonempty_access_tokens_without_rendering_them(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    config = _minimal_verify_config()

    def auth(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args == ["gcloud", "auth", "print-access-token"]:
            return CommandResult("", "", 0)
        if args == ["gcloud", "auth", "application-default", "print-access-token"]:
            return CommandResult("synthetic-secret-token", "", 0)
        return CommandResult("ok", "", 0)

    runner = ScriptedRunner({"gcloud", "docker"}, run=auth)
    results = system.run_verify(state_with(runner, config), fix=False)
    auth_results = {item["name"]: item for item in results["auth"]}
    assert auth_results["gcloud"]["status"] == "fail"
    assert auth_results["gcloud"]["condition"] == "broken"
    assert auth_results["gcloud-adc"]["status"] == "pass"
    assert "synthetic-secret-token" not in json.dumps(results)


def test_verify_fails_closed_when_probe_output_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    config = _minimal_verify_config()
    config.verify.tools = ["noisy"]

    def truncated(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "/bin/noisy":
            return CommandResult("healthy", "", 0, stdout_truncated=True)
        if args == ["gcloud", "auth", "print-access-token"]:
            return CommandResult("token", "", 0, stdout_truncated=True)
        if args == ["docker", "info"]:
            return CommandResult("running", "", 0, stdout_truncated=True)
        return CommandResult("ok", "", 0)

    runner = ScriptedRunner({"noisy", "gcloud", "docker"}, run=truncated)
    results = system.run_verify(state_with(runner, config), fix=False)

    assert results["passed"] is False
    assert results["tools"][0]["status"] == "fail"
    assert results["auth"][1]["status"] == "fail"
    assert results["docker"][0]["status"] == "fail"


def test_verify_classifies_probe_exceptions_auth_failures_and_stopped_docker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("JULES_API_KEY", "configured")
    monkeypatch.setattr(system.Path, "home", classmethod(lambda _cls: tmp_path))
    config = _minimal_verify_config()
    config.verify.tools = ["timeout-tool", "error-tool"]

    def probes(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "/bin/timeout-tool":
            raise DotError("command timed out")
        if args[0] == "/bin/error-tool":
            raise OSError("private operating-system error")
        if args == ["gh", "auth", "status"]:
            return CommandResult("", "Login required for private-host", 1)
        if args == ["gcloud", "auth", "print-access-token"]:
            raise DotError("command timed out")
        if args == ["gcloud", "auth", "application-default", "print-access-token"]:
            raise OSError("private adc error")
        if args == ["gws", "auth", "status"]:
            return CommandResult("", "unclassified private failure", 2)
        if args == ["jules", "remote", "list", "--repo"]:
            return CommandResult("available", "", 0)
        if args == ["docker", "info"]:
            return CommandResult("", "private daemon failure", 3)
        raise AssertionError(args)

    installed = {"timeout-tool", "error-tool", "gh", "gcloud", "gws", "jules", "docker"}
    results = system.run_verify(state_with(ScriptedRunner(installed, run=probes), config), fix=False)

    tools = {item["name"]: item for item in results["tools"]}
    assert tools["timeout-tool"]["details"] == "capability probe timed out"
    assert tools["error-tool"]["details"] == "capability probe failed"
    auth = {item["name"]: item for item in results["auth"]}
    assert auth["gh"]["condition"] == "unauthenticated"
    assert auth["gcloud"]["details"] == "auth check timed out; state unknown"
    assert auth["gcloud-adc"]["details"] == "auth check failed; state unknown"
    assert auth["gws"]["condition"] == "broken"
    assert auth["jules"]["status"] == "pass"
    assert results["docker"][0]["details"] == "not running"
    assert "private" not in json.dumps(results)


def test_verify_reports_environment_and_secret_edge_cases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("REQUIRED_SET", "yes")
    monkeypatch.setenv("OPTIONAL_SET", "yes")
    monkeypatch.delenv("OPTIONAL_MISSING", raising=False)
    config = _minimal_verify_config()
    config.verify.env_vars.required = ["REQUIRED_SET"]
    config.verify.env_vars.optional = ["OPTIONAL_SET", "OPTIONAL_MISSING"]
    missing = tmp_path / "missing"
    insecure = tmp_path / "insecure"
    relaxed = tmp_path / "relaxed"
    loop = tmp_path / "loop"
    insecure.write_text("encrypted", encoding="utf-8")
    insecure.chmod(0o644)
    relaxed.write_text("public", encoding="utf-8")
    relaxed.chmod(0o666)
    loop.symlink_to(loop)
    config.verify.secrets = [
        SecretConfig(path=str(missing)),
        SecretConfig(path=str(insecure)),
        SecretConfig(path=str(relaxed), required_perms=0),
        SecretConfig(path=str(loop)),
    ]

    results = system.run_verify(state_with(ScriptedRunner(), config), fix=False)

    environment = {item["name"]: item for item in results["env_vars"]}
    assert environment["REQUIRED_SET"]["status"] == "pass"
    assert environment["OPTIONAL_SET"]["status"] == "pass"
    assert environment["OPTIONAL_MISSING"]["status"] == "warn"
    secrets = {item["name"]: item for item in results["secrets"]}
    assert secrets[str(missing)]["status"] == "warn"
    assert secrets[str(insecure)]["status"] == "fail"
    assert secrets[str(relaxed)]["status"] == "pass"
    assert secrets[str(loop)]["details"] == "unable to inspect file"


def test_verify_repairs_permissions_and_reports_repair_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    secret = tmp_path / "key"
    secret.write_text("encrypted", encoding="utf-8")
    secret.chmod(0o644)
    config = _minimal_verify_config()
    config.verify.secrets = [SecretConfig(path=str(secret))]
    runner = ScriptedRunner({"docker"})

    repaired = system.run_verify(state_with(runner, config), fix=True)
    assert repaired["secrets"][0]["status"] == "pass"
    assert stat.S_IMODE(secret.stat().st_mode) == 0o600

    secret.chmod(0o644)

    def deny_chmod(_path: Path, _mode: int) -> None:
        raise PermissionError("private")

    monkeypatch.setattr(Path, "chmod", deny_chmod)
    failed = system.run_verify(state_with(runner, config), fix=True)
    assert failed["secrets"][0]["status"] == "fail"
    assert "private" not in json.dumps(failed)


def test_verify_compares_installed_python_package_with_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    (source / "dot/pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    (source / "dot/uv.lock").write_text("version = 1\n", encoding="utf-8")
    for package in (source_package, installed_package):
        (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", installed_package)
    monkeypatch.setattr(system, "_PACKAGE_VERSION", "1.26.2")
    receipt = system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    config = _minimal_verify_config()

    def source_path(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult(f"{source}\n", "", 0) if args == ["chezmoi", "source-path"] else CommandResult("ok", "", 0)

    runner = ScriptedRunner({"chezmoi", "docker"}, run=source_path)
    current = system.run_verify(state_with(runner, config), fix=False)
    assert current["install"][0]["status"] == "pass"

    (installed_package / "module.py").write_text("VALUE = 0\n", encoding="utf-8")
    stale = system.run_verify(state_with(runner, config), fix=False)
    assert stale["install"][0]["status"] == "fail"
    assert "STALE" in stale["install"][0]["details"]


def test_install_receipt_rejects_stale_package_and_binds_wheel_digest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    (source_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (installed_package / "module.py").write_text("VALUE = 0\n", encoding="utf-8")
    project = source / "dot/pyproject.toml"
    project.write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    (source / "dot/uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", installed_package)
    monkeypatch.setattr(system, "_PACKAGE_VERSION", "1.26.2")
    wheel_digest = _WHEEL_SHA256

    with pytest.raises(DotError, match="installed Python package differs from source"):
        system.write_install_receipt(source, wheel_digest, system._install_basis_digest(source))  # noqa: SLF001
    assert not (installed_package / system._INSTALL_RECEIPT_NAME).exists()  # noqa: SLF001

    (installed_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    receipt = system.write_install_receipt(
        source,
        wheel_digest,
        system._install_basis_digest(source),  # noqa: SLF001
    )
    assert json.loads(receipt.read_text(encoding="utf-8")) == {
        "basis_sha256": system._install_basis_digest(source),  # noqa: SLF001
        "installed_version": "1.26.2",
        "schema_version": 2,
        "source_root": str(source),
        "wheel_sha256": wheel_digest,
    }
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["wheel_sha256"] = "not-a-digest"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    assert system._install_receipt_matches(source) is False  # noqa: SLF001

    project.write_text('[project]\nname = "fmind-dot"\nversion = "1.26.3"\n', encoding="utf-8")
    with pytest.raises(DotError, match="installed version differs from source project"):
        system.write_install_receipt(source, wheel_digest, system._install_basis_digest(source))  # noqa: SLF001


def test_install_receipt_rejects_source_basis_changed_since_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    for package in (source_package, installed_package):
        (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "dot/pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    lock = source / "dot/uv.lock"
    lock.write_text("version = 1\n", encoding="utf-8")
    expected_basis = system._install_basis_digest(source)  # noqa: SLF001
    lock.write_text("version = 2\n", encoding="utf-8")
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", installed_package)
    monkeypatch.setattr(system, "_PACKAGE_VERSION", "1.26.2")

    with pytest.raises(DotError, match="source changed during deployment"):
        system.write_install_receipt(source, _WHEEL_SHA256, expected_basis)
    assert not (installed_package / system._INSTALL_RECEIPT_NAME).exists()  # noqa: SLF001


def test_verify_receipt_binds_project_metadata_and_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    project = source / "dot/pyproject.toml"
    lock = source / "dot/uv.lock"
    project.write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    lock.write_text("version = 1\n", encoding="utf-8")
    for package in (source_package, installed_package):
        (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", installed_package)
    monkeypatch.setattr(system, "_PACKAGE_VERSION", "1.26.2")
    system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001
    config = _minimal_verify_config()

    def source_path(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult(f"{source}\n", "", 0) if args == ["chezmoi", "source-path"] else CommandResult("ok", "", 0)

    runner = ScriptedRunner({"chezmoi", "docker"}, run=source_path)
    project.write_text(
        '[project]\nname = "fmind-dot"\nversion = "1.26.2"\n[project.scripts]\ndot = "changed:main"\n',
        encoding="utf-8",
    )
    metadata_stale = system.run_verify(state_with(runner, config), fix=False)
    assert metadata_stale["install"][0]["details"] == "STALE: install receipt differs from source"

    system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001
    lock.write_text("version = 2\n", encoding="utf-8")
    lock_stale = system.run_verify(state_with(runner, config), fix=False)
    assert lock_stale["install"][0]["details"] == "STALE: install receipt differs from source"

    receipt = system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001
    receipt.chmod(0o644)
    exposed_receipt = system.run_verify(state_with(runner, config), fix=False)
    assert exposed_receipt["install"][0]["details"] == "STALE: install receipt differs from source"


def test_install_verification_classifies_source_resolution_and_checkout_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = _minimal_verify_config()

    def source_error(_args: list[str], _cwd: Path | None, _input_text: str | None, _check: bool) -> CommandResult:
        raise OSError("private source error")

    unavailable = system._install_results(  # noqa: SLF001 - install freshness is a public verify section.
        state_with(ScriptedRunner({"chezmoi"}, run=source_error), config)
    )
    assert unavailable[0].condition == "unknown"

    for invalid_output in ("", "first\nsecond\n"):
        runner = ScriptedRunner(
            {"chezmoi"},
            run=lambda _args, _cwd, _input_text, _check, output=invalid_output: CommandResult(output, "", 0),
        )
        assert system._install_results(state_with(runner, config))[0].condition == "unknown"  # noqa: SLF001

    not_checkout = tmp_path / "not-checkout"
    not_checkout.mkdir()
    runner = ScriptedRunner(
        {"chezmoi"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(f"{not_checkout}\n", "", 0),
    )
    assert system._install_results(state_with(runner, config))[0].condition == "skipped"  # noqa: SLF001

    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    (source_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (installed_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    project = source / "dot/pyproject.toml"
    project.write_text("not = [valid", encoding="utf-8")
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", installed_package)
    runner = ScriptedRunner(
        {"chezmoi"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(f"{source}\n", "", 0),
    )
    malformed = system._install_results(state_with(runner, config))  # noqa: SLF001
    assert malformed[0].condition == "broken"

    project.write_text('[project]\nname = "fmind-dot"\nversion = "0.0.0"\n', encoding="utf-8")
    stale = system._install_results(state_with(runner, config))  # noqa: SLF001
    assert stale[0].details == "STALE: installed version differs from source"


def test_install_receipt_fails_closed_for_symlinked_package_and_atomic_publish_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(system, "_PACKAGE_VERSION", "1.26.2")
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    source_package.mkdir(parents=True)
    (source_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "dot/pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    (source / "dot/uv.lock").write_text("version = 1\n", encoding="utf-8")
    real_package = tmp_path / "installed"
    real_package.mkdir()
    package_link = tmp_path / "installed-link"
    package_link.symlink_to(real_package, target_is_directory=True)
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", package_link)
    with pytest.raises(DotError, match="must be a real directory"):
        system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001

    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", real_package)
    (real_package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    original_replace = Path.replace

    def fail_receipt_replace(path: Path, target: Path) -> Path:
        if path.name.startswith(f".{system._INSTALL_RECEIPT_NAME}."):  # noqa: SLF001
            raise OSError("publish denied")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_receipt_replace)
    with pytest.raises(OSError, match="publish denied"):
        system.write_install_receipt(source, _WHEEL_SHA256, system._install_basis_digest(source))  # noqa: SLF001
    assert [path.name for path in real_package.iterdir()] == ["module.py"]


def test_malformed_install_receipt_is_never_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package = tmp_path / "installed"
    package.mkdir()
    receipt = package / system._INSTALL_RECEIPT_NAME  # noqa: SLF001
    receipt.write_text("{malformed", encoding="utf-8")
    receipt.chmod(0o600)
    monkeypatch.setattr(system, "_PACKAGE_DIRECTORY", package)

    assert system._install_receipt_matches(tmp_path) is False  # noqa: SLF001 - receipt is an external trust boundary.


def test_verify_command_renders_json_and_human_exit_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    app = typer.Typer()
    system.register(app)
    state = state_with(ScriptedRunner())
    empty_sections = {
        "env_vars": [],
        "auth": [],
        "secrets": [],
        "docker": [],
        "tools": [],
        "install": [],
    }
    passing = empty_sections | {"passed": True}
    failing = empty_sections | {
        "env_vars": [{"name": "REQUIRED", "status": "fail", "details": "MISSING", "path": "", "condition": ""}],
        "passed": False,
    }
    monkeypatch.setattr(system, "run_verify", lambda _state, *, fix: passing | {"fixed": fix})

    json_result = CliRunner().invoke(app, ["verify", "--json", "--fix"], obj=state)
    assert json_result.exit_code == 0
    assert isinstance(state.stdout, StringIO)
    assert '"passed": true' in state.stdout.getvalue()
    assert '"fixed": true' in state.stdout.getvalue()

    state.stdout.seek(0)
    state.stdout.truncate()
    human_result = CliRunner().invoke(app, ["verify"], obj=state)
    assert human_result.exit_code == 0
    assert "Verification passed" in state.stdout.getvalue()

    monkeypatch.setattr(system, "run_verify", lambda _state, *, fix: failing | {"fixed": fix})
    state.stdout.seek(0)
    state.stdout.truncate()
    failed_result = CliRunner().invoke(app, ["verify"], obj=state)
    assert failed_result.exit_code == 1
    assert "✗ REQUIRED" in state.stdout.getvalue()
    assert "Verification failed" in state.stdout.getvalue()


def test_system_command_aliases_and_verify_flags_remain_compatible() -> None:
    app = typer.Typer()
    system.register(app)
    command = get_command(app)
    assert isinstance(command, TyperGroup)
    assert {"completion", "g", "login", "l", "notify", "n", "setup", "u", "verify", "v"} <= set(command.commands)
    login = command.commands["login"]
    setup = command.commands["setup"]
    assert isinstance(login, TyperGroup)
    assert isinstance(setup, TyperGroup)
    assert {"github", "g", "workspace", "w", "gcp", "c"} <= set(login.commands)
    assert {"workspace", "w"} <= set(setup.commands)
    option_names = {
        name
        for parameter in command.commands["verify"].params
        if isinstance(parameter, TyperOption)
        for name in parameter.opts
    }
    assert {"--json", "-j", "--fix", "-f"} <= option_names
