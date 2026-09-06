from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO

import pytest

from fmind_dot import system
from fmind_dot.config import Config
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.system import (
    Notification,
    build_notification,
    notification_command,
    run_setup_workspace,
    run_verify,
)


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
    ) -> int:
        del cwd, stdin, stdout, stderr, env
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
        Path("/home/fmind"),
        {"ZELLIJ_SESSION_NAME": "main", "ZELLIJ_PANE_ID": "3"}.get,
    )

    assert notification.summary == "⏳ Claude Code · dot"
    assert notification.headline == "Waiting for your input"
    assert notification.details == ("~/fmind/dot", "zellij main · pane 3")


def test_notification_command_prefers_notify_send() -> None:
    runner = FakeRunner({"notify-send", "gdbus"})

    command = notification_command(runner, Notification("Done", "Turn finished", ("~/dot",)), system="linux")

    assert command[0] == "notify-send"
    assert command[-2:] == ["Done", "Turn finished\n~/dot"]


def test_setup_workspace_uses_argument_then_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner({"gcloud", "gws"})
    state = state_with(runner)
    monkeypatch.setenv("GWS_PROJECT", "from-env")

    run_setup_workspace(state, "explicit-project")

    assert runner.calls[0][-3:] == ["--project", "explicit-project", "--quiet"]
    assert runner.calls[1] == ["gws", "auth", "setup", "--project", "explicit-project"]


def test_verify_fails_closed_for_required_environment_and_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("REQUIRED_FOR_TEST", raising=False)
    config = Config()
    config.verify.env_vars.required = ["REQUIRED_FOR_TEST"]
    config.verify.env_vars.optional = []
    config.verify.tools = ["python", "missing"]
    secret = tmp_path / "key"
    secret.write_text("encrypted", encoding="utf-8")
    secret.chmod(0o600)
    config.verify.secrets[0].path = str(secret)
    runner = FakeRunner({"python"})

    results = run_verify(state_with(runner, config), fix=False)

    assert results["passed"] is False
    assert all(limit is not None for limit in runner.output_limits)
    encoded = json.dumps(results)
    assert "MISSING (required)" in encoded
    assert '"name": "missing", "status": "fail"' in encoded


def test_verify_omits_empty_optional_result_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Config()
    config.verify.env_vars.required = []
    config.verify.env_vars.optional = []
    config.verify.secrets = []
    config.verify.tools = []
    monkeypatch.setattr(
        system,
        "_environment_results",
        lambda _state: [system.CheckResult("minimal", "pass", "")],
    )

    results = run_verify(state_with(FakeRunner(), config), fix=False)

    assert results["env_vars"] == [{"name": "minimal", "status": "pass"}]
