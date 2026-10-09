"""Agent hook payloads and desktop notifications, from the native event to the platform command."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fmind_dot.hooks as hooks
from fmind_dot import agent as agent_module
from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.hooks import Notification, notification_command
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from tests.fakes import ScriptedRunner


def state_with(
    runner: Runner,
    config: Config | None = None,
) -> State:
    state = State(runner=runner, stdin=StringIO(), stdout=StringIO(), stderr=StringIO())
    state._config = config or Config()  # noqa: SLF001 - command boundary dependency injection.
    return state


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
        input=json.dumps({"cwd": str(project), "notification_type": "permission_prompt"}),
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


@pytest.mark.parametrize("agent", ["claude", "grok", "codex", "copilot", "agy"])
@pytest.mark.parametrize("field", ["background_tasks", "backgroundTasks", "session_crons", "sessionCrons"])
def test_background_work_never_announces_a_handoff(monkeypatch: pytest.MonkeyPatch, agent: str, field: str) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    for value in ([{"status": "running"}], None, False, "unknown", {}):
        result = CliRunner().invoke(
            app,
            ["agent", "hook", "notify", agent, "stop"],
            input=json.dumps({"fullyIdle": True, field: value}),
        )
        assert result.exit_code == 0
    assert captured == []


@pytest.mark.parametrize(("agent", "key"), [("claude", "notification_type"), ("grok", "notificationType")])
def test_only_idle_and_actionable_notifications_reach_the_user(
    monkeypatch: pytest.MonkeyPatch, agent: str, key: str
) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    for kind in ("auth_success", "agent_completed", "task_complete", "quota_auto_resume_fired", "unknown", None):
        for event in ("ready", "needs-input"):
            result = CliRunner().invoke(app, ["agent", "hook", "notify", agent, event], input=json.dumps({key: kind}))
            assert result.exit_code == 0
    assert captured == []
    for event, kind in (("ready", "idle_prompt"), ("needs-input", "permission_prompt")):
        result = CliRunner().invoke(app, ["agent", "hook", "notify", agent, event], input=json.dumps({key: kind}))
        assert result.exit_code == 0
    assert [notification.headline for notification in captured] == ["Your turn", "Needs your input"]


def test_question_alerts_survive_background_work_and_stop_reentry(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    result = CliRunner().invoke(
        app,
        ["agent", "hook", "notify", "claude", "needs-input"],
        input=json.dumps(
            {
                "notification_type": "permission_prompt",
                "stop_hook_active": True,
                "background_tasks": [{"status": "running"}],
            }
        ),
    )
    assert result.exit_code == 0
    assert [notification.headline for notification in captured] == ["Needs your input"]


@pytest.mark.parametrize("payload", ["", '{"fullyIdle":false}', "{}"])
def test_agy_stop_requires_explicit_idle(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    result = CliRunner().invoke(app, ["agent", "hook", "notify", "agy", "stop"], input=payload)
    assert result.exit_code == 0
    assert captured == []


@pytest.mark.parametrize(
    "payload", [{"agent_id": "child"}, {"subagentType": "worker"}, {"hook_event_name": "SubagentStop"}]
)
def test_child_completion_never_announces_a_handoff(monkeypatch: pytest.MonkeyPatch, payload: dict[str, str]) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(agent_module, "send_notification", lambda _state, notification: captured.append(notification))
    result = CliRunner().invoke(app, ["agent", "hook", "notify", "claude", "stop"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert captured == []


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


def test_deeply_nested_hook_payload_exits_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    # About a million levels exceed the interpreter stack while decoding.
    result = CliRunner().invoke(
        app, ["agent", "hook", "notify", "claude", "stop"], input="[" * 1_000_000 + "]" * 1_000_000
    )

    assert result.exit_code == 0
    assert result.exception is None
    assert result.stderr.startswith("agent hook notify failed:")


def test_notification_commands_cover_linux_fallback_and_darwin_escaping() -> None:
    linux = hooks.notification_command(
        ScriptedRunner({"gdbus"}),
        hooks.Notification("Done", "Turn finished", ("~/dot",)),
        system="linux",
    )
    assert linux[0] == "gdbus"
    assert {"uint32 0", "@as []", "@a{sv} {}", "int32 10000"} <= set(linux)

    darwin = hooks.notification_command(
        ScriptedRunner(),
        hooks.Notification('Done "now"', "Turn finished", (r"~/a\b",)),
        system="darwin",
    )
    assert darwin[0:2] == ["osascript", "-e"]
    assert r"Done \"now\"" in darwin[2]
    assert r"~/a\\b" in darwin[2]


def test_notification_validation_and_minimal_platform_commands(tmp_path: Path) -> None:
    with pytest.raises(DotError, match="agent name is required"):
        hooks.build_notification("", "stop", None)
    with pytest.raises(DotError, match="unknown agent notify event"):
        hooks.build_notification("codex", "unknown", None)

    minimal = hooks.build_notification("custom", "needs-input", None)
    assert minimal == hooks.Notification("⏳ custom", "Needs your input")
    assert (
        'display notification "Needs your input"'
        in hooks.notification_command(ScriptedRunner(), minimal, system="darwin")[2]
    )

    session_only = hooks.build_notification(
        "codex",
        "stop",
        tmp_path / "outside",
    )
    assert session_only.details == ()

    with pytest.raises(DotError, match="unsupported on plan9"):
        hooks.notification_command(ScriptedRunner(), minimal, system="plan9")
    with pytest.raises(DotError, match="install notify-send or gdbus"):
        hooks.notification_command(ScriptedRunner(), minimal, system="linux")


def test_hook_payload_is_strict() -> None:
    class TTYInput(StringIO):
        def isatty(self) -> bool:
            return True

    assert hooks.read_hook_payload(TTYInput("ignored")) is None
    assert hooks.read_hook_payload(StringIO("  \n")) is None
    with pytest.raises(DotError, match="failed to parse agent hook input"):
        hooks.read_hook_payload(StringIO("{"))
    with pytest.raises(DotError, match="expected a JSON object"):
        hooks.read_hook_payload(StringIO("[]"))
    with pytest.raises(DotError, match="stopHookActive must be a boolean"):
        hooks.read_hook_payload(StringIO('{"stopHookActive":"false"}'))
    with pytest.raises(DotError, match="fullyIdle must be a boolean"):
        hooks.read_hook_payload(StringIO('{"fullyIdle":1}'))
    assert hooks.read_hook_payload(StringIO('{"fullyIdle":true,"cwd":"/workspace"}')) == {
        "fullyIdle": True,
        "cwd": "/workspace",
    }


def test_notification_dispatch_skips_unsupported_hosts_and_redacts_backend_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = ScriptedRunner(
        {"notify-send"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult("", "oauth-token=secret", 4),
    )
    state = state_with(runner)
    monkeypatch.setattr(hooks.platform, "system", lambda: "Plan9")
    hooks.send_notification(state, hooks.Notification("Done"))
    assert runner.calls == []

    monkeypatch.setattr(hooks.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")
    with pytest.raises(DotError, match="failed to send desktop notification with notify-send") as raised:
        hooks.send_notification(state, hooks.Notification("Done"))
    assert "secret" not in str(raised.value)


def test_notification_dispatch_skips_missing_desktop_service(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = ScriptedRunner(
        {"gdbus"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(
            "",
            "Error: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown: "
            "The name org.freedesktop.Notifications was not provided by any .service files",
            1,
        ),
    )
    state = state_with(runner)
    monkeypatch.setattr(hooks.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")

    hooks.send_notification(state, hooks.Notification("Done"))

    assert isinstance(state.stderr, StringIO)
    assert "notification skipped: no desktop notification service" in state.stderr.getvalue()


def _zellij_pane(monkeypatch: pytest.MonkeyPatch, pane: str) -> None:
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "work")
    monkeypatch.setenv("ZELLIJ_PANE_ID", pane)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ('[{"id":7,"is_plugin":false,"title":"Fix notifications"}]', "Fix notifications"),
        ('[{"id":7,"is_plugin":false,"title":"[ . ] Working | Fix hooks | dot"}]', "Fix hooks"),
        ('[{"id":8,"is_plugin":false,"title":"Other task"}]', ""),
        ('[{"id":7,"is_plugin":true,"title":"Plugin"}]', ""),
        ('[{"id":7,"is_plugin":false,"title":null}]', ""),
        ('{"panes":[]}', ""),
        ("invalid JSON", ""),
    ],
)
def test_notification_title_uses_only_originating_terminal(
    monkeypatch: pytest.MonkeyPatch, output: str, expected: str
) -> None:
    _zellij_pane(monkeypatch, "7")
    runner = ScriptedRunner({"zellij"}, run=lambda *_args: CommandResult(output, "", 0))
    assert hooks.notification_title(runner) == expected


@pytest.mark.parametrize("failure", ["timeout", "exited"])
def test_notification_title_failure_keeps_plain_notification(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    _zellij_pane(monkeypatch, "7")

    def run(*_args: object) -> CommandResult:
        if failure == "timeout":
            raise DotError("command timed out: zellij")
        return CommandResult("[]", "", int(failure == "exited"))

    runner = ScriptedRunner({"zellij"}, run=run)
    assert hooks.notification_title(runner) == ""
    assert hooks.build_notification("codex", "stop", Path("/work/project")).details == ()


@pytest.mark.parametrize("pane", ["", "terminal_7", "-1", "\uff17"])
def test_notification_title_skips_unavailable_origin(monkeypatch: pytest.MonkeyPatch, pane: str) -> None:
    _zellij_pane(monkeypatch, pane)
    runner = ScriptedRunner({"zellij"})
    assert hooks.notification_title(runner) == ""
    assert runner.calls == []


def test_notification_text_is_short_and_has_no_terminal_controls() -> None:
    notification = hooks.build_notification(
        "codex", "stop", Path("/work/project"), title="\x1b[31mFix\n hooks\x1b[0m\x00"
    )
    assert notification.details == ("Fix hooks",)
    long = hooks.build_notification("codex", "stop", None, title="x" * 100)
    assert long.details == ("x" * 79 + "…",)
    assert hooks.build_notification("codex", "stop", Path("/work/project"), title="project").details == ()


@pytest.mark.parametrize("agent", ["codex", "claude", "grok", "agy", "copilot"])
def test_all_harness_notifications_dispatch_on_macos_without_dbus(monkeypatch: pytest.MonkeyPatch, agent: str) -> None:
    monkeypatch.setattr(hooks.platform, "system", lambda: "Darwin")
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    runner = ScriptedRunner()
    notification = hooks.build_notification(agent, "stop", Path("/work/project"), title='Fix "quoted" paths')
    hooks.send_notification(state_with(runner), notification)
    assert len(runner.calls) == 1
    assert runner.calls[0][:2] == ["osascript", "-e"]
    assert 'subtitle "Your turn"' in runner.calls[0][2]
    assert r"Fix \"quoted\" paths" in runner.calls[0][2]
    assert "Zellij" not in runner.calls[0][2]
    assert "pane" not in runner.calls[0][2]


def test_linux_notification_renders_title_as_text_without_actions() -> None:
    notification = hooks.build_notification("codex", "stop", Path("/work/project"), title="Fix <hooks> & tests")
    for installed in ({"notify-send", "gdbus"}, {"gdbus"}):
        command = hooks.notification_command(ScriptedRunner(installed), notification, system="linux")
        assert "Your turn\nFix &lt;hooks&gt; &amp; tests" in command
        if command[0] == "gdbus":
            assert "@as []" in command
        else:
            assert not any("action" in argument for argument in command)


def test_notification_command_prefers_notify_send() -> None:
    runner = ScriptedRunner({"notify-send", "gdbus"})

    command = notification_command(runner, Notification("Done", "Turn finished", ("~/dot",)), system="linux")

    assert command[0] == "notify-send"
    assert command[-2:] == ["Done", "Turn finished\n~/dot"]
