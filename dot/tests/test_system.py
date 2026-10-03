from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO

import pytest
from typer.testing import CliRunner

from fmind_dot import system
from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.hooks import Notification, build_notification, notification_command
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.system import run_doctor


class FakeRunner(Runner):
    def __init__(self, installed: set[str] | None = None) -> None:
        self.installed = installed or set()
        self.calls: list[list[str]] = []
        self.output_limits: list[int | None] = []

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
        del cwd, input_text, env, timeout, check
        self.calls.append(list(args))
        return CommandResult(stdout="ok\n", stderr="", returncode=0)

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
        on_stdout_line: Callable[[str], None] | None = None,
    ) -> int:
        del cwd, stdin, stdout, stderr, env, on_stdout_line
        self.calls.append(list(args))
        return 0


def state_with(runner: FakeRunner, config: Config | None = None) -> State:
    state = State(runner=runner)
    state._config = config or Config()  # noqa: SLF001 - explicit dependency injection for the command boundary.
    return state


def test_build_notification_preserves_agent_hook_context() -> None:
    notification = build_notification(
        "claude",
        "needs-input",
        Path("/home/fmind/fmind/dot"),
        title="Fix notifications",
    )

    assert notification.summary == "⏳ Claude Code · dot"
    assert notification.headline == "Needs your input"
    assert notification.details == ("Fix notifications",)


def test_notification_command_prefers_notify_send() -> None:
    runner = FakeRunner({"notify-send", "gdbus"})

    command = notification_command(runner, Notification("Done", "Turn finished", ("~/dot",)), system="linux")

    assert command[0] == "notify-send"
    assert command[-2:] == ["Done", "Turn finished\n~/dot"]


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
    runner = FakeRunner({"python"})

    results = run_doctor(state_with(runner, config), fix=False)

    assert results["passed"] is False
    assert all(limit is not None for limit in runner.output_limits)
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

    results = run_doctor(state_with(FakeRunner(), config), fix=False)

    assert results["env_vars"] == [{"name": "minimal", "status": "pass"}]


def test_authentication_probes_require_deep_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    probes = []

    def probe(_state: State) -> list[system.CheckResult]:
        probes.append("authentication")
        return [system.CheckResult("fixture", "pass", "authenticated")]

    monkeypatch.setattr(system, "_auth_results", probe)
    state = state_with(FakeRunner())
    local = run_doctor(state, fix=False)
    assert probes == []
    assert local["auth"][0]["status"] == "skip"
    deep = run_doctor(state, fix=False, deep=True)
    assert probes == ["authentication"]
    assert deep["auth"][0]["status"] == "pass"


def test_doctor_detects_pgcli_import_failure() -> None:
    class BrokenPgcli(FakeRunner):
        def run_bounded(self, args: Sequence[str], **kwargs: object) -> CommandResult:
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
    result = run_doctor(state_with(BrokenPgcli({"pgcli"}), config), fix=False)
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

    result = run_doctor(state_with(FakeRunner(), config), fix=fix)

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
    results = system.headroom_results([first, second, first, tmp_path / "absent"], memory=None)
    disks = [result for result in results if result.name == "disk"]
    assert len(disks) == 1
    assert disks[0].path == f"{first}, {second}"
