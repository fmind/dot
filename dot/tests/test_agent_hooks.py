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


def test_notify_hook_uses_shared_event_and_workspace_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "work")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "7")
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
            "Waiting for your input",
            ("~/project", "zellij work · pane 7"),
        )
    ]


def test_notify_hook_spools_notifier_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    def fail(_state: State, _notification: Notification) -> None:
        raise DotError("notifier exited with status 7")

    monkeypatch.setattr(agent_module, "send_notification", fail)

    result = CliRunner().invoke(app, ["agent", "hook", "notify", "codex", "session-end"], input="{}")

    assert result.exit_code == 1
    records = list((tmp_path / ".agents" / "hook-failures" / "v1").glob("*.json"))
    assert len(records) == 1
    failure = json.loads(records[0].read_text(encoding="utf-8"))
    assert failure["agent"] == "codex"
    assert failure["operation"] == "notify:session-end"
    assert failure["detail"] == "notifier exited with status 7"
