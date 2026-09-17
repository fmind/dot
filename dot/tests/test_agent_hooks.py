from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot import agent as agent_module
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.state import State
from fmind_dot.system import Notification


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


@pytest.mark.parametrize(("event", "exit_code"), [("SessionEnd", 0), ("PreCompact", 1), ("SubagentStop", 1)])
def test_claude_missing_transcript_only_skips_session_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, event: str, exit_code: int
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    payload = {
        "session_id": "unused-session",
        "transcript_path": str(tmp_path / "absent.jsonl"),
        "hook_event_name": event,
        "reason": "prompt_input_exit",
    }
    result = CliRunner().invoke(app, ["agent", "hook", "session", "claude"], input=json.dumps(payload))
    assert result.exit_code == exit_code
    assert not (tmp_path / ".agents/sessions").exists()
    if event == "SessionEnd":
        assert "Session capture skipped" in result.stderr
        assert not (tmp_path / ".agents/hook-failures").exists()
        # Once the native transcript exists, the same event must capture it.
        Path(payload["transcript_path"]).write_text('{"type":"user","message":{"content":"fixture"}}\n')
        captured = CliRunner().invoke(app, ["agent", "hook", "session", "claude"], input=json.dumps(payload))
        assert captured.exit_code == 0
        assert "Session capture skipped" not in captured.stderr
        assert (tmp_path / ".agents/sessions").exists()
    else:
        assert isinstance(result.exception, DotError)
        assert "unavailable" in str(result.exception)


def test_claude_session_end_rejects_directory_transcript(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["agent", "hook", "session", "claude"],
        input=json.dumps({"session_id": "fixture", "transcript_path": str(tmp_path), "hook_event_name": "SessionEnd"}),
    )
    assert result.exit_code == 1
    assert "Session capture skipped" not in result.stderr


def _fail(_state: State, _notification: Notification) -> None:
    raise DotError("notifier exited with status 7")


def test_notify_hook_spools_notifier_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    result = CliRunner().invoke(app, ["agent", "hook", "notify", "codex", "session-end"], input="{}")

    assert result.exit_code == 1
    records = list((tmp_path / ".agents" / "hook-failures" / "v1").glob("*.json"))
    assert len(records) == 1
    failure = json.loads(records[0].read_text(encoding="utf-8"))
    assert failure["agent"] == "codex"
    assert failure["operation"] == "notify:session-end"
    assert failure["detail"] == "notifier exited with status 7"


def test_notify_hook_refuses_to_spool_through_a_symlinked_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    home = tmp_path / "home"
    home.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    result = CliRunner().invoke(app, ["agent", "hook", "notify", "codex", "session-end"], input="{}")

    assert result.exit_code == 1
    assert f"agent hook failure spool unavailable: unsafe directory {home}" in result.output
    assert not (real / ".agents").exists()
