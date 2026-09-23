from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot import agent as agent_module
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.hooks import Notification
from fmind_dot.state import State


@pytest.fixture(autouse=True)
def no_live_terminal_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_module, "notification_title", lambda _runner: "")


def test_notify_hook_uses_shared_event_and_workspace_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "work")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "7")
    monkeypatch.setattr(agent_module, "notification_title", lambda _runner: "Fix notifications")
    captured: list[Notification] = []

    def capture(_state: State, notification: Notification) -> None:
        captured.append(notification)

    monkeypatch.setattr(agent_module, "send_notification", capture)

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "notify", "claude", "needs-input"],
        input=json.dumps({"cwd": str(project)}),
    )

    assert result.exit_code == 0
    assert captured == [
        Notification(
            "⏳ Claude Code · project",
            "Needs your input",
            ("Fix notifications",),
        )
    ]


@pytest.mark.parametrize("agent", ["codex", "claude", "grok", "agy", "copilot"])
def test_turn_notifications_obey_idle_and_reentry_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    payload = {"cwd": str(tmp_path), "fullyIdle": True}
    command = ["agent", "hook", "notify", agent, "stop"]
    assert CliRunner().invoke(app, command, input=json.dumps(payload)).exit_code == 0
    assert len(captured) == 1
    for guard in ("stop_hook_active", "stopHookActive"):
        assert CliRunner().invoke(app, command, input=json.dumps({**payload, guard: True})).exit_code == 0
    if agent == "agy":
        assert CliRunner().invoke(app, command, input=json.dumps({**payload, "fullyIdle": False})).exit_code == 0
    assert len(captured) == 1


@pytest.mark.parametrize("payload", ["{}", "not json"])
def test_notify_failure_warns_on_stderr_without_failing_the_turn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    result = CliRunner().invoke(app, ["agent", "hook", "notify", "codex", "stop"], input=payload)

    assert result.exit_code == 0
    assert result.stdout == ""
    assert "agent hook notify failed:" in result.stderr
    assert not (tmp_path / ".agents").exists()


@pytest.mark.parametrize("exists", [False, True], ids=["missing-config", "malformed-config"])
def test_notify_does_not_load_unrelated_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exists: bool
) -> None:
    config = tmp_path / "broken.yaml"
    if exists:
        config.write_text("prune: [\n")
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))

    result = CliRunner().invoke(app, ["--config", str(config), "agent", "hook", "notify", "codex", "stop"], input="{}")

    assert result.exit_code == 0
    assert result.stdout == result.stderr == ""
    assert len(captured) == 1


def _fail(_state: State, _notification: Notification) -> None:
    raise DotError("notifier exited with status 7")


@pytest.mark.parametrize(
    "command", [["session", "claude"], ["session", "codex", "session-id"], ["copilot-session-end"]]
)
def test_retired_capture_hooks_are_usage_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: list[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = CliRunner().invoke(app, ["agent", "hook", *command], input="{}")
    assert result.exit_code == 2
    assert not (tmp_path / ".agents").exists()
