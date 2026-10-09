"""Workstation doctor, headroom, completion, and install-freshness checks with scripted providers."""

from __future__ import annotations

import json
import stat
from collections.abc import Callable, Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.core import TyperGroup, TyperOption
from typer.main import get_command
from typer.testing import CliRunner

from fmind_dot import system
from fmind_dot.cli import app
from fmind_dot.config import Config, SecretConfig, ToolConfig
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.system import run_doctor
from tests.fakes import ScriptedRunner, doctor_sections


@pytest.fixture(autouse=True)
def ample_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doctor verdicts must not depend on the test host's free disk; disk tests override this."""
    monkeypatch.setattr(system.shutil, "disk_usage", _disk(30))


def test_verify_fails_closed_for_required_environment_and_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("REQUIRED_FOR_TEST", raising=False)
    config = Config()
    config.doctor.env_vars.required = ["REQUIRED_FOR_TEST"]
    config.doctor.env_vars.optional = []
    config.doctor.tools = ["python", "missing"]
    secret = tmp_path / "key"
    secret.write_text("encrypted", encoding="utf-8")
    secret.chmod(0o600)
    config.doctor.secrets[0].path = str(secret)
    runner = ScriptedRunner({"python"})

    results = doctor_sections(run_doctor(state_with(runner, config), fix=False))

    assert results["passed"] is False
    encoded = json.dumps(results)
    assert "MISSING (required)" in encoded
    assert '"name": "missing", "status": "fail"' in encoded


def test_verify_omits_empty_optional_result_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config()
    config.doctor.env_vars.required = []
    config.doctor.env_vars.optional = []
    config.doctor.secrets = []
    config.doctor.tools = []
    monkeypatch.setattr(
        system,
        "_environment_results",
        lambda _state: [system.CheckResult("minimal", "pass", "")],
    )

    results = doctor_sections(run_doctor(state_with(ScriptedRunner(), config), fix=False))

    assert results["env_vars"] == [{"name": "minimal", "status": "pass"}]


def test_authentication_probes_require_deep_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    probes = []

    def probe(_state: State) -> list[system.CheckResult]:
        probes.append("authentication")
        return [system.CheckResult("fixture", "pass", "authenticated")]

    monkeypatch.setattr(system, "_auth_results", probe)
    state = state_with(ScriptedRunner())
    local = doctor_sections(run_doctor(state, fix=False))
    assert probes == []
    assert local["auth"][0]["status"] == "skip"
    deep = doctor_sections(run_doctor(state, fix=False, deep=True))
    assert probes == ["authentication"]
    assert deep["auth"][0]["status"] == "pass"


def test_doctor_detects_pgcli_import_failure() -> None:
    class BrokenPgcli(ScriptedRunner):
        def run(self, args: Sequence[str], **kwargs: object) -> CommandResult:  # type: ignore[override]
            del kwargs
            if list(args) == ["/bin/pgcli", "--version"]:
                return CommandResult(stdout="", stderr="ImportError: no pq wrapper available", returncode=1)
            return CommandResult(stdout="ok", stderr="", returncode=0)

    config = Config()
    assert "pgcli" in config.doctor.tools
    config.doctor.tools = ["pgcli"]
    config.doctor.env_vars.required = []
    config.doctor.env_vars.optional = []
    config.doctor.secrets = []
    result = doctor_sections(run_doctor(state_with(BrokenPgcli({"pgcli"}), config), fix=False))
    assert result["passed"] is False
    assert result["tools"][0]["status"] == "fail"
    assert result["tools"][0]["condition"] == "broken"


@pytest.mark.parametrize("fix", [False, True])
@pytest.mark.parametrize("mode", [0o600, 0o700])
def test_doctor_rejects_secret_directories_without_changing_permissions(tmp_path: Path, fix: bool, mode: int) -> None:
    secret = tmp_path / "key"
    secret.mkdir(mode=mode)
    config = Config()
    config.doctor.tools = []
    config.doctor.secrets[0].path = str(secret)

    result = doctor_sections(run_doctor(state_with(ScriptedRunner(), config), fix=fix))

    assert result["secrets"][0]["status"] == "fail"
    assert result["secrets"][0]["details"] == "not a regular file"
    assert secret.stat().st_mode & 0o777 == mode


def _disk(free_gib: float) -> Callable[[object], object]:
    usage = type("Usage", (), {"free": int(free_gib * 1024**3)})
    return lambda _path: usage


@pytest.mark.parametrize(
    ("free_gib", "memory_gib", "verdict", "exit_code"),
    [(30, 4, "PASS", 0), (15, 4, "WARN", 0), (5, 4, "FAIL", 1), (30, 0.5, "FAIL", 1)],
)
def test_headroom_prints_one_line_and_fails_below_limits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, free_gib: float, memory_gib: float, verdict: str, exit_code: int
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TMPDIR", raising=False)
    monkeypatch.setattr(system.shutil, "disk_usage", _disk(free_gib))
    monkeypatch.setattr(system, "available_memory_bytes", lambda: int(memory_gib * 1024**3))
    result = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert result.exit_code == exit_code, result.output
    assert len(result.stdout.splitlines()) == 1
    assert result.stdout.startswith(f"{verdict} · headroom: ")
    assert ("limits:" in result.stdout) == (verdict != "PASS")


def test_headroom_ignores_malformed_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("prune: [\n", encoding="utf-8")
    monkeypatch.setattr(system.shutil, "disk_usage", _disk(30))
    monkeypatch.setattr(system, "available_memory_bytes", lambda: 4 * 1024**3)
    result = CliRunner().invoke(app, ["--config", str(malformed), "doctor", "--headroom"])
    assert result.exit_code == 0, result.output
    assert result.stdout.startswith("PASS · headroom: ")


def test_headroom_rejects_mutating_or_probing_flags() -> None:
    result = CliRunner().invoke(app, ["doctor", "--headroom", "--deep"])
    assert result.exit_code == 2


def test_headroom_groups_paths_by_filesystem_and_parses_available_memory(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 8000000 kB\nMemAvailable: 2097152 kB\n")
    assert system.available_memory_bytes(meminfo) == 2 * 1024**3
    assert system.available_memory_bytes(tmp_path / "missing") is None
    vm_stat = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                               70000.\n"
        "Pages active:                            400000.\n"
        "Pages inactive:                           70000.\n"
        "Pages speculative:                         5536.\n"
    )
    assert system.vm_stat_available_bytes(vm_stat) == (70000 - 5536 + 70000) * 16384
    assert system.vm_stat_available_bytes("Pages free: 1.\n") is None
    results = system.headroom_results([first, second, first, tmp_path / "absent"], memory=None)
    disks = [result for result in results if result.name == "disk"]
    assert len(disks) == 1
    assert disks[0].path == f"{first}, {second}"


def test_macos_memory_reads_vm_stat_and_degrades_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    output = "Mach Virtual Memory Statistics: (page size of 4096 bytes)\nPages free: 10.\nPages inactive: 6.\n"

    class VmStat:
        def run(self, args: list[str], **_kwargs: object) -> CommandResult:
            assert args == ["vm_stat"]
            return CommandResult(output, "", 0)

    monkeypatch.setattr(system.sys, "platform", "darwin")
    monkeypatch.setattr(system, "Runner", VmStat)
    assert system.available_memory_bytes() == 16 * 4096
    output = "unexpected"
    assert system.available_memory_bytes() is None


def state_with(
    runner: Runner,
    config: Config | None = None,
    *,
    stdin: str = "",
) -> State:
    state = State(
        runner=runner,
        stdin=StringIO(stdin),
        stdout=StringIO(),
        stderr=StringIO(),
    )
    state._config = config or Config()  # noqa: SLF001 - command boundary dependency injection.
    return state


def test_completion_uses_only_the_configured_generator() -> None:
    config = Config()
    config.completions.custom_commands["custom"] = ToolConfig(args=["completions", "fish"])

    def empty_then_fallback(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult("# fallback\n" if args[1:] == ["completion", "fish"] else "", "", 0)

    runner = ScriptedRunner({"custom"}, run=empty_then_fallback)
    with pytest.raises(DotError, match="empty output"):
        system._generate_completion(state_with(runner, config), "custom")  # noqa: SLF001
    assert [call[1:] for call in runner.calls] == [["completions", "fish"]]

    failing = ScriptedRunner(
        {"plain"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("", "private-provider-payload", 7),
    )
    with pytest.raises(DotError, match="failed to generate completions for plain"):
        system._generate_completion(state_with(failing), "plain")  # noqa: SLF001
    assert failing.calls == [["plain", "completion", "fish"]]


def test_dot_completion_uses_typer_fish_source_protocol() -> None:
    runner = ScriptedRunner(
        {"env", "dot"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("# dot fish completion\n", "", 0),
    )

    assert "_DOT_COMPLETE=complete_fish" in system._generate_completion(state_with(runner), "dot")  # noqa: SLF001
    assert runner.calls == []


def test_bf_completion_uses_typer_fish_source_protocol() -> None:
    runner = ScriptedRunner(
        {"env", "bf"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("# bf fish completion\n", "", 0),
    )

    assert system._generate_completion(state_with(runner), "bf") == "# bf fish completion\n"  # noqa: SLF001
    assert runner.calls == [["env", "_BF_COMPLETE=source_fish", "bf"]]


def test_completion_publication_is_atomic_and_sets_private_cache_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completions = tmp_path / "completions"
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    config = Config()
    config.completions.path = str(completions)
    config.completions.tools = ["dot"]

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
    state = state_with(runner, config)
    with pytest.raises(DotError, match=r"atuin-init\.fish.*carapace-init\.fish"):
        system.run_completion(state)
    assert isinstance(state.stdout, StringIO)
    output = state.stdout.getvalue()
    assert "Failed to generate atuin-init.fish" in output
    assert "Failed to generate carapace-init.fish" in output
    assert "Completions updated" not in output


def test_completion_generation_reports_missing_generators_and_empty_output() -> None:
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


@pytest.mark.parametrize("check_only", [False, True])
def test_completion_run_skips_missing_tools_and_reports_failed_generators(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    check_only: bool,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    config = Config()
    config.completions.path = str(tmp_path / "completions")
    config.completions.tools = ["missing", "broken", "working"]
    directory = Path(config.completions.path)
    directory.mkdir()
    previous = directory / "broken.fish"
    previous.write_text("# known good\n")

    def scripts(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "fish":
            return CommandResult("", "", 0)
        if args[0] == "working":
            return CommandResult("# working\n", "", 0)
        return CommandResult("", "private", 7)

    state = state_with(ScriptedRunner({"fish", "broken", "working"}, run=scripts), config)
    # Both modes exit 1 on a failed generator; installation still keeps the successful scripts.
    with pytest.raises(DotError, match="completion generation failed: broken"):
        system.run_completion(state, check_only=check_only)
    if not check_only:
        assert (directory / "working.fish").read_text() == "# working\n"
    assert previous.read_text() == "# known good\n"
    assert isinstance(state.stdout, StringIO)
    output = state.stdout.getvalue()
    assert "missing is not installed or active, skipping" in output
    assert "Failed to generate completions for broken" in output
    assert "Generated completions for working" in output
    assert "Completions updated" not in output


def test_completion_rejects_empty_scripts_before_replacing_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "tool.fish"
    target.write_text("# known good\n", encoding="utf-8")

    with pytest.raises(DotError, match="generated Fish script is empty"):
        system._write_validated_fish(state_with(ScriptedRunner()), target, " \n", 0o644)  # noqa: SLF001

    assert target.read_text(encoding="utf-8") == "# known good\n"


def _minimal_verify_config() -> Config:
    config = Config()
    config.doctor.env_vars.required = []
    config.doctor.env_vars.optional = []
    config.doctor.secrets = []
    config.doctor.tools = []
    return config


@pytest.mark.parametrize(
    ("payload", "status", "condition"),
    [
        ({"auth_method": "none"}, "fail", "unauthenticated"),
        ({"auth_method": "oauth", "token_valid": False}, "fail", "unauthenticated"),
        ({"auth_method": "oauth", "token_valid": True, "scopes": Config().auth.workspace.scopes}, "pass", "healthy"),
        ({"auth_method": "oauth", "token_valid": True, "scopes": ["openid"]}, "fail", "unauthenticated"),
        ({"auth_method": "oauth", "token_valid": True}, "fail", "broken"),
        ({"auth_method": "oauth", "token_valid": "true"}, "fail", "broken"),
        ({"unexpected": "private-response"}, "fail", "broken"),
        ([], "fail", "broken"),
        ("private-invalid-json", "fail", "broken"),
    ],
    ids=[
        "no-credentials",
        "invalid-token",
        "valid-token",
        "missing-scopes",
        "unreported-scopes",
        "wrong-type",
        "unknown-shape",
        "array",
        "bad-json",
    ],
)
def test_doctor_workspace_auth_inspects_native_status(payload: object, status: str, condition: str) -> None:
    output = payload if isinstance(payload, str) else json.dumps(payload)
    runner = ScriptedRunner({"gws"}, run=lambda _args, _cwd, _input, _check: CommandResult(output, "", 0))
    config = Config()
    config.doctor.tools = []
    config.doctor.secrets = []

    report = doctor_sections(system.run_doctor(state_with(runner, config), fix=False, deep=True))

    result = next(item for item in report["auth"] if item["name"] == "gws")
    assert (result["status"], result["condition"]) == (status, condition)
    assert "private-" not in json.dumps(report)


_GH_STATUS = ["gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"]


def _gh_status_runner(**entry: object) -> ScriptedRunner:
    payload = {"hosts": {"github.com": [{"state": "success", "active": True, "tokenSource": "keyring", **entry}]}}
    return ScriptedRunner({"gh"}, run=lambda _args, _cwd, _input, _check: CommandResult(json.dumps(payload), "", 0))


@pytest.mark.parametrize(
    ("output", "status", "condition"),
    [
        ({"tokenSource": "keyring"}, "pass", "healthy"),
        ({"tokenSource": "/home/private-user/.config/gh/hosts.yml"}, "warn", "insecure"),
        ({"state": "error", "error": "non-200 OK status code: 401 Unauthorized body: {}"}, "fail", "unauthenticated"),
        ({"state": "error", "error": "private network failure"}, "fail", "broken"),
        ('{"hosts": {}}', "fail", "unauthenticated"),
        ("private-invalid-json", "fail", "broken"),
    ],
    ids=["keyring", "plaintext-hosts-yml", "invalid-token", "network-error", "no-account", "bad-json"],
)
def test_doctor_github_auth_inspects_token_source(output: dict[str, str] | str, status: str, condition: str) -> None:
    runner = (
        _gh_status_runner(**output)
        if isinstance(output, dict)
        else ScriptedRunner({"gh"}, run=lambda _args, _cwd, _input, _check: CommandResult(output, "", 0))
    )

    report = doctor_sections(system.run_doctor(state_with(runner, _minimal_verify_config()), fix=False, deep=True))

    result = report["auth"][0]
    assert _GH_STATUS in runner.calls
    assert (result["name"], result["status"], result["condition"]) == ("gh", status, condition)
    if status == "warn":
        assert "gh auth logout" in result["details"]
    # macOS's legitimate disk paths start with /private; reject the fixture's sensitive values.
    encoded = json.dumps(report)
    for sensitive in ("private-user", "private network failure", "private-invalid-json"):
        assert sensitive not in encoded


@pytest.mark.parametrize(
    "stderr",
    [
        "ERROR: (gcloud.auth.application-default.print-access-token) Your default credentials were not found.",
        "Reauthentication is needed. Please run `gcloud auth application-default login` to reauthenticate.",
    ],
    ids=["adc-missing", "reauth-needed"],
)
def test_doctor_gcloud_adc_login_errors_are_unauthenticated(stderr: str) -> None:
    def adc(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult("", stderr, 1) if "application-default" in args else CommandResult("token", "", 0)

    runner = ScriptedRunner({"gcloud"}, run=adc)
    report = doctor_sections(system.run_doctor(state_with(runner, _minimal_verify_config()), fix=False, deep=True))

    auth = {item["name"]: item for item in report["auth"]}
    assert (auth["gcloud-adc"]["details"], auth["gcloud-adc"]["condition"]) == ("NOT authenticated", "unauthenticated")


def test_verify_probes_path_visible_tools_and_redacts_output() -> None:
    config = _minimal_verify_config()
    config.doctor.tools = ["healthy", "broken"]

    def probe(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "/bin/broken":
            return CommandResult("token=stdout-secret", "token=stderr-secret", 3)
        return CommandResult("healthy", "", 0)

    runner = ScriptedRunner({"healthy", "broken", "docker"}, run=probe)
    results = doctor_sections(system.run_doctor(state_with(runner, config), fix=False, deep=True))
    by_name = {item["name"]: item for item in results["tools"]}
    assert by_name["healthy"]["status"] == "pass"
    assert by_name["broken"]["status"] == "fail"
    assert by_name["broken"]["condition"] == "broken"
    encoded = json.dumps(results)
    assert "stdout-secret" not in encoded
    assert "stderr-secret" not in encoded


def test_verify_requires_nonempty_access_tokens_without_rendering_them() -> None:
    config = _minimal_verify_config()

    def auth(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args == ["gcloud", "auth", "print-access-token"]:
            return CommandResult("", "", 0)
        if args[:4] == ["gcloud", "auth", "application-default", "print-access-token"]:
            return CommandResult("synthetic-secret-token", "", 0)
        return CommandResult("ok", "", 0)

    runner = ScriptedRunner({"gcloud", "docker"}, run=auth)
    results = doctor_sections(system.run_doctor(state_with(runner, config), fix=False, deep=True))
    auth_results = {item["name"]: item for item in results["auth"]}
    assert auth_results["gcloud"]["status"] == "fail"
    assert auth_results["gcloud"]["condition"] == "broken"
    assert auth_results["gcloud-adc"]["status"] == "pass"
    assert "synthetic-secret-token" not in json.dumps(results)


def test_verify_classifies_probe_exceptions_auth_failures_and_stopped_docker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(system.Path, "home", classmethod(lambda _cls: tmp_path))
    config = _minimal_verify_config()
    config.doctor.tools = ["timeout-tool", "error-tool"]

    def probes(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[0] == "/bin/timeout-tool":
            raise CommandTimeoutError("command timed out")
        if args[0] == "/bin/error-tool":
            raise OSError("private operating-system error")
        if args == _GH_STATUS:
            return CommandResult("", "Login required for private-host", 1)
        if args == ["gcloud", "auth", "print-access-token"]:
            raise CommandTimeoutError("command timed out")
        if args[:4] == ["gcloud", "auth", "application-default", "print-access-token"]:
            raise OSError("private adc error")
        if args == ["gws", "auth", "status"]:
            return CommandResult("", "unclassified private failure", 2)
        if args == ["docker", "info"]:
            return CommandResult("", "private daemon failure", 3)
        raise AssertionError(args)

    installed = {"timeout-tool", "error-tool", "gh", "gcloud", "gws", "jules", "docker"}
    results = doctor_sections(
        system.run_doctor(state_with(ScriptedRunner(installed, run=probes), config), fix=False, deep=True)
    )

    tools = {item["name"]: item for item in results["tools"]}
    assert tools["timeout-tool"]["details"] == "capability probe timed out"
    assert tools["error-tool"]["details"] == "capability probe failed"
    auth = {item["name"]: item for item in results["auth"]}
    # gh JSON status exits zero without credentials; a failed status is unknown, as for dot login.
    assert auth["gh"]["condition"] == "broken"
    assert auth["gcloud"]["details"] == "auth check timed out; state unknown"
    assert auth["gcloud-adc"]["details"] == "auth check failed; state unknown"
    assert auth["gws"]["condition"] == "broken"
    assert "jules" not in auth
    assert results["docker"][0]["details"] == "not running"
    encoded = json.dumps(results)
    for sensitive in (
        "private operating-system error",
        "private-host",
        "private adc error",
        "unclassified private failure",
        "private daemon failure",
    ):
        assert sensitive not in encoded


def test_verify_reports_environment_and_secret_edge_cases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("REQUIRED_SET", "yes")
    monkeypatch.setenv("OPTIONAL_SET", "yes")
    monkeypatch.delenv("OPTIONAL_MISSING", raising=False)
    config = _minimal_verify_config()
    config.doctor.env_vars.required = ["REQUIRED_SET"]
    config.doctor.env_vars.optional = ["OPTIONAL_SET", "OPTIONAL_MISSING"]
    missing = tmp_path / "missing"
    insecure = tmp_path / "insecure"
    relaxed = tmp_path / "relaxed"
    loop = tmp_path / "loop"
    insecure.write_text("encrypted", encoding="utf-8")
    insecure.chmod(0o644)
    relaxed.write_text("public", encoding="utf-8")
    relaxed.chmod(0o666)
    loop.symlink_to(loop)
    config.doctor.secrets = [
        SecretConfig(path=str(missing)),
        SecretConfig(path=str(insecure)),
        SecretConfig(path=str(relaxed), required_perms=0),
        SecretConfig(path=str(loop)),
    ]

    results = doctor_sections(system.run_doctor(state_with(ScriptedRunner(), config), fix=False, deep=True))

    environment = {item["name"]: item for item in results["env_vars"]}
    assert environment["REQUIRED_SET"]["status"] == "pass"
    assert environment["OPTIONAL_SET"]["status"] == "pass"
    assert environment["OPTIONAL_MISSING"] == {
        "name": "OPTIONAL_MISSING",
        "status": "skip",
        "condition": "skipped",
        "details": "unset (optional)",
    }
    secrets = {item["name"]: item for item in results["secrets"]}
    assert secrets[str(missing)]["status"] == "warn"
    assert secrets[str(insecure)]["status"] == "fail"
    assert secrets[str(relaxed)]["status"] == "pass"
    assert secrets[str(loop)]["details"] == "unable to inspect file"


def test_verify_repairs_permissions_and_reports_repair_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = tmp_path / "key"
    secret.write_text("encrypted", encoding="utf-8")
    secret.chmod(0o644)
    config = _minimal_verify_config()
    config.doctor.secrets = [SecretConfig(path=str(secret))]
    runner = ScriptedRunner({"docker"})

    repaired = doctor_sections(system.run_doctor(state_with(runner, config), fix=True, deep=True))
    assert repaired["secrets"][0]["status"] == "pass"
    assert stat.S_IMODE(secret.stat().st_mode) == 0o600

    secret.chmod(0o644)

    def deny_chmod(_path: Path, _mode: int) -> None:
        raise PermissionError("chmod-denied-secret-marker")

    monkeypatch.setattr(Path, "chmod", deny_chmod)
    failed = doctor_sections(system.run_doctor(state_with(runner, config), fix=True, deep=True))
    assert failed["secrets"][0]["status"] == "fail"
    assert "chmod-denied-secret-marker" not in json.dumps(failed)


@pytest.mark.parametrize("changed_file", ["module.py", "api-prices.yaml"])
def test_verify_compares_installed_python_package_with_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, changed_file: str
) -> None:
    source = tmp_path / "source"
    source_package = source / "dot/src/fmind_dot"
    installed_package = tmp_path / "installed/fmind_dot"
    source_package.mkdir(parents=True)
    installed_package.mkdir(parents=True)
    (source / "dot/pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n', encoding="utf-8")
    for package in (source_package, installed_package):
        (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(system, "PACKAGE_DIRECTORY", installed_package)
    monkeypatch.setattr(system, "_installed_version", lambda: "1.26.2")
    config = _minimal_verify_config()

    def source_path(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        return CommandResult(f"{source}\n", "", 0) if args == ["chezmoi", "source-path"] else CommandResult("ok", "", 0)

    runner = ScriptedRunner({"chezmoi", "docker"}, run=source_path)
    current = doctor_sections(system.run_doctor(state_with(runner, config), fix=False, deep=True))
    assert current["install"][0]["status"] == "pass"

    (installed_package / changed_file).write_text("VALUE = 0\n", encoding="utf-8")
    stale = doctor_sections(system.run_doctor(state_with(runner, config), fix=False, deep=True))
    assert stale["install"][0]["status"] == "fail"
    assert stale["install"][0]["details"] == "STALE: installed Python package differs from source"


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
    monkeypatch.setattr(system, "PACKAGE_DIRECTORY", installed_package)
    runner = ScriptedRunner(
        {"chezmoi"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(f"{source}\n", "", 0),
    )
    malformed = system._install_results(state_with(runner, config))  # noqa: SLF001
    assert malformed[0].condition == "broken"

    project.write_text('[project]\nname = "fmind-dot"\nversion = "0.0.0"\n', encoding="utf-8")
    stale = system._install_results(state_with(runner, config))  # noqa: SLF001
    assert stale[0].details == "STALE: installed version differs from source"


def test_doctor_from_a_source_checkout_skips_install_freshness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # `uv run --project dot dot doctor` imports the checkout itself, which trivially matches its source.
    source = tmp_path / "checkout"
    package = source / "dot/src/fmind_dot"
    package.mkdir(parents=True)
    (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "dot/pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "0.0.0"\n', encoding="utf-8")
    monkeypatch.setattr(system, "PACKAGE_DIRECTORY", package)
    runner = ScriptedRunner(
        {"chezmoi"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(f"{source}\n", "", 0),
    )

    [result] = system._install_results(state_with(runner, _minimal_verify_config()))  # noqa: SLF001

    assert (result.status, result.condition) == ("skip", "skipped")
    assert "source checkout" in result.details
    assert "STALE" not in result.details


def test_verify_command_renders_json_and_human_exit_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    app = typer.Typer(add_completion=False)
    system.register(app)
    state = state_with(ScriptedRunner())
    passing: list[system.CheckResult] = []
    failing = [system.CheckResult("REQUIRED", "fail", "MISSING", group="env_vars")]
    monkeypatch.setattr(system, "run_doctor", lambda _state, **_kwargs: passing)

    json_result = CliRunner().invoke(app, ["doctor", "--json", "--fix"], obj=state)
    assert json_result.exit_code == 0
    assert isinstance(state.stdout, StringIO)
    assert '"passed": true' in state.stdout.getvalue()
    assert json.loads(state.stdout.getvalue())["schema"] == "dot.diagnostics/v1"

    state.stdout.seek(0)
    state.stdout.truncate()
    human_result = CliRunner().invoke(app, ["doctor"], obj=state)
    assert human_result.exit_code == 0
    assert "Environment Variables" in state.stdout.getvalue()

    monkeypatch.setattr(system, "run_doctor", lambda _state, **_kwargs: failing)
    state.stdout.seek(0)
    state.stdout.truncate()
    failed_result = CliRunner().invoke(app, ["doctor"], obj=state)
    assert failed_result.exit_code == 1
    assert "✗ REQUIRED" in state.stdout.getvalue()


def test_system_command_surface_and_verify_flags() -> None:
    app = typer.Typer(add_completion=False)
    system.register(app)
    command = get_command(app)
    assert isinstance(command, TyperGroup)
    assert set(command.commands) == {"completion", "doctor"}
    option_names = {
        name
        for parameter in command.commands["doctor"].params
        if isinstance(parameter, TyperOption)
        for name in parameter.opts
    }
    assert {"--json", "-j", "--fix", "--deep"} <= option_names
    assert "-f" not in option_names


def test_bundled_completion_resolves_the_selected_mise_package(tmp_path: Path) -> None:
    package = tmp_path / "package"
    scripts = package / "share/fish/vendor_completions.d"
    scripts.mkdir(parents=True)
    (scripts / "tool.fish").write_text("complete -c tool -l example\n")
    config = Config()
    config.completions.custom_commands["tool"] = ToolConfig(package="github:owner/tool")
    runner = ScriptedRunner(
        {"tool", "mise"},
        run=lambda _args, _cwd, _input, _check: CommandResult(str(package), "", 0),
    )
    assert system._generate_completion(state_with(runner, config), "tool") == "complete -c tool -l example\n"  # noqa: SLF001
    assert runner.calls == [["mise", "where", "--", "github:owner/tool"]]
    (scripts / "tool.fish").write_bytes(b"complete -c tool -d \xff\n")
    with pytest.raises(DotError, match="bundled Fish completion for tool is not UTF-8"):
        system._generate_completion(state_with(runner, config), "tool")  # noqa: SLF001
    (package / "tool.fish").write_text("# ambiguous source\n")
    with pytest.raises(DotError, match="expected one bundled Fish completion for tool, found 2"):
        system._generate_completion(state_with(runner, config), "tool")  # noqa: SLF001


def test_completion_selection_is_authoritative_and_preserves_carapace_exclusions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CARAPACE_EXCLUDES", "custom")
    config = Config()
    config.completions.path = str(tmp_path / "completions")
    config.completions.tools = ["uv"]
    runner = ScriptedRunner({"fish", "uv", "carapace"})
    environments: list[Mapping[str, str] | None] = []
    original = runner.run

    def capture(args: Sequence[str], **kwargs: Any) -> CommandResult:
        if args[0] == "carapace":
            environments.append(kwargs.get("env"))
        return original(args, **kwargs)

    monkeypatch.setattr(runner, "run", capture)
    system.run_completion(state_with(runner, config))
    assert (tmp_path / "completions/uv.fish").is_file()
    assert not (tmp_path / "completions/dot.fish").exists()
    assert environments == [{"CARAPACE_EXCLUDES": "custom,uv"}]


@pytest.mark.parametrize("active", [True, False])
def test_completion_resolves_optional_mise_shims(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, active: bool) -> None:
    mise = tmp_path / "mise"
    mise.touch()
    shim = tmp_path / "a2a"
    shim.symlink_to(mise)

    def scripts(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args == ["mise", "which", "a2a"]:
            return CommandResult(
                "/selected/a2a" if active else "", "" if active else "not currently active", 0 if active else 1
            )
        return CommandResult("complete -c a2a -l help\n", "", 0)

    runner = ScriptedRunner(run=scripts)
    monkeypatch.setattr(runner, "which", lambda name: {"a2a": shim, "mise": mise}.get(name))
    if active:
        assert "complete -c a2a" in system._generate_completion(state_with(runner), "a2a")  # noqa: SLF001
        assert runner.calls[-1] == ["a2a", "completion", "fish"]
    else:
        with pytest.raises(FileNotFoundError):
            system._generate_completion(state_with(runner), "a2a")  # noqa: SLF001
        assert runner.calls == [["mise", "which", "a2a"]]


def test_completion_check_leaves_installed_scripts_and_cache_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = Config()
    config.completions.path = str(tmp_path / "completions")
    config.completions.tools = ["dot"]
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    completions = Path(config.completions.path)
    completions.mkdir()
    installed = completions / "dot.fish"
    installed.write_text("last known good\n")
    runner = ScriptedRunner({"fish", "atuin", "carapace"})
    state = state_with(runner, config)
    system.run_completion(state, check_only=True)
    assert installed.read_text() == "last known good\n"
    assert list(completions.iterdir()) == [installed]
    assert not cache.exists()
    assert isinstance(state.stdout, StringIO)
    assert "Completion check passed" in state.stdout.getvalue()
    # The temporary check directory is not an installation target worth reporting.
    assert "Completions updated" not in state.stdout.getvalue()
    assert ["atuin", "init", "fish", "--disable-ai"] in runner.calls
    assert ["carapace", "_carapace", "fish"] in runner.calls

    installing = state_with(ScriptedRunner({"fish"}), config)
    system.run_completion(installing)
    assert isinstance(installing.stdout, StringIO)
    assert installing.stdout.getvalue().endswith(f"\n✓ Completions updated in {completions}\n")


def test_completion_mise_resolution_error_is_not_a_missing_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mise = tmp_path / "mise"
    mise.touch()
    shim = tmp_path / "acli"
    shim.symlink_to(mise)
    runner = ScriptedRunner(run=lambda *_: CommandResult("", "configuration is not trusted", 1))
    monkeypatch.setattr(runner, "which", lambda name: {"acli": shim, "mise": mise}.get(name))
    with pytest.raises(DotError, match="failed to resolve mise"):
        system._generate_completion(state_with(runner), "acli")  # noqa: SLF001


def test_verify_skips_docker_service_when_engine_is_absent() -> None:
    config = _minimal_verify_config()
    config.doctor.tools = []

    results = doctor_sections(system.run_doctor(state_with(ScriptedRunner(set()), config), fix=False, deep=False))

    assert results["docker"] == [
        {"name": "docker", "status": "skip", "condition": "skipped", "details": "not installed (optional)"}
    ]
    assert results["passed"] is True


@pytest.mark.parametrize(
    ("free_gib", "status", "passed"),
    [(30, "pass", True), (15, "warn", True), (5, "fail", False)],
)
def test_doctor_checks_disk_and_points_to_cleanup(
    monkeypatch: pytest.MonkeyPatch, free_gib: float, status: str, passed: bool
) -> None:
    monkeypatch.setattr(system.shutil, "disk_usage", _disk(free_gib))

    results = doctor_sections(run_doctor(state_with(ScriptedRunner(set()), _minimal_verify_config()), fix=False))

    assert {item["name"] for item in results["resources"]} == {"disk"}
    assert {item["status"] for item in results["resources"]} == {status}
    assert all(("dot prune" in item["details"]) == (status != "pass") for item in results["resources"])
    assert results["passed"] is passed


def test_doctor_counts_chezmoi_orphans_without_failing(tmp_path: Path) -> None:
    leftover = tmp_path / "leftover"
    leftover.write_text("old", encoding="utf-8")
    managed = tmp_path / "managed"
    managed.write_text("new", encoding="utf-8")
    entries = {str(leftover): {"type": "file"}, str(managed): {"type": "file"}}

    def chezmoi(args: list[str], cwd: Path | None, input_text: str | None, check: bool) -> CommandResult:
        del cwd, input_text, check
        if args[:2] == ["chezmoi", "state"]:
            return CommandResult(json.dumps({"entryState": entries}), "", 0)
        if args[:2] == ["chezmoi", "managed"]:
            return CommandResult(f"{managed}\0", "", 0)
        return CommandResult("", "", 1)

    runner = ScriptedRunner({"chezmoi"}, run=chezmoi)
    found = doctor_sections(run_doctor(state_with(runner, _minimal_verify_config()), fix=False))
    orphans = [item for item in found["install"] if item["name"] == "chezmoi orphans"]
    assert orphans == [
        {
            "name": "chezmoi orphans",
            "status": "warn",
            "condition": "orphaned",
            "details": "1 target(s) chezmoi no longer manages; review with `dot orphan`",
        }
    ]
    assert found["passed"] is True

    leftover.unlink()
    clean = doctor_sections(run_doctor(state_with(runner, _minimal_verify_config()), fix=False))
    assert [item["status"] for item in clean["install"] if item["name"] == "chezmoi orphans"] == ["pass"]
