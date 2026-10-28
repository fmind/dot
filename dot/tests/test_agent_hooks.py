"""Agent hook payloads and desktop notifications, from the native event to the platform command."""

from __future__ import annotations

import json
import wave
from io import StringIO
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fmind_dot.hooks as hooks
from fmind_dot import agent as agent_module
from fmind_dot.cli import app
from fmind_dot.errors import DotError

# Bound at import, before conftest pins print-mode detection off for every test.
from fmind_dot.hooks import Notification, agy_print_mode
from fmind_dot.process import CommandResult
from fmind_dot.state import State
from tests.fakes import ScriptedRunner, make_state


def test_notify_hook_uses_shared_event_and_workspace_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    captured: list[Notification] = []

    def capture(_state: State, notification: Notification, **_options: bool) -> None:
        captured.append(notification)

    monkeypatch.setattr(agent_module, "send_notification", capture)

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "notify", "claude", "needs-input"],
        input=json.dumps({"cwd": str(project), "notification_type": "permission_prompt"}),
    )

    assert result.exit_code == 0
    assert captured == [Notification("⏳ Claude Code · project", "Needs your input")]


@pytest.mark.parametrize("agent", ["claude", "agy", "copilot"])
def test_turn_notifications_obey_idle_and_reentry_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str
) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
    payload = {"cwd": str(tmp_path), "fullyIdle": True}
    command = ["agent", "hook", "notify", agent, "stop"]
    assert CliRunner().invoke(app, command, input=json.dumps(payload)).exit_code == 0
    assert len(captured) == 1
    for guard in ("stop_hook_active", "stopHookActive"):
        assert CliRunner().invoke(app, command, input=json.dumps({**payload, guard: True})).exit_code == 0
    if agent == "agy":
        assert CliRunner().invoke(app, command, input=json.dumps({**payload, "fullyIdle": False})).exit_code == 0
    assert len(captured) == 1


@pytest.mark.parametrize("agent", ["claude", "copilot", "agy"])
@pytest.mark.parametrize("field", ["background_tasks", "backgroundTasks", "session_crons", "sessionCrons"])
def test_background_work_never_announces_a_handoff(monkeypatch: pytest.MonkeyPatch, agent: str, field: str) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
    for value in ([{"status": "running"}], None, False, "unknown", {}):
        result = CliRunner().invoke(
            app,
            ["agent", "hook", "notify", agent, "stop"],
            input=json.dumps({"fullyIdle": True, field: value}),
        )
        assert result.exit_code == 0
    assert captured == []


@pytest.mark.parametrize("key", ["notification_type", "notificationType"])
def test_only_idle_and_actionable_notifications_reach_the_user(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    agent = "claude"
    captured: list[Notification] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
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
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
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
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
    result = CliRunner().invoke(app, ["agent", "hook", "notify", "agy", "stop"], input=payload)
    assert result.exit_code == 0
    assert captured == []


def _process(proc: Path, pid: int, parent: int, *argv: str) -> None:
    (proc / str(pid)).mkdir(parents=True)
    (proc / str(pid) / "cmdline").write_bytes(b"\0".join(arg.encode() for arg in argv) + b"\0")
    (proc / str(pid) / "stat").write_text(f"{pid} ({Path(argv[0]).name} worker) S {parent} 1 1\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("ancestors", "expected"),
    [
        (
            [("sh", "-c", "dot agent hook notify agy stop"), ("/home/u/.local/bin/agy", "--model", "m", "-p", "Role")],
            True,
        ),
        ([("/home/u/.local/bin/agy", "--print=check")], True),
        ([("sh", "-c", "dot"), ("agy",)], False),
        ([("agy", "--prompt-interactive", "start")], False),
        ([("sh",), ("bash",), ("zellij",), ("fish",)], False),
    ],
)
def test_agy_print_mode_reads_the_nearest_agy_ancestor(
    tmp_path: Path, ancestors: list[tuple[str, ...]], expected: bool
) -> None:
    for offset, argv in enumerate(ancestors):
        _process(tmp_path, 100 + offset, 101 + offset, *argv)
    assert agy_print_mode(tmp_path, 100) is expected


def test_agy_print_mode_fails_open_without_process_metadata(tmp_path: Path) -> None:
    assert agy_print_mode(tmp_path, 100) is False
    (tmp_path / "100").mkdir()
    (tmp_path / "100" / "cmdline").write_bytes(b"sh\0")
    (tmp_path / "100" / "stat").write_text("100 (sh) S not-a-pid\n", encoding="utf-8")
    assert agy_print_mode(tmp_path, 100) is False


def test_headless_agy_turns_stay_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
    monkeypatch.setattr(hooks, "agy_print_mode", lambda: True)
    payload = json.dumps({"cwd": str(tmp_path), "fullyIdle": True})
    assert CliRunner().invoke(app, ["agent", "hook", "notify", "agy", "stop"], input=payload).exit_code == 0
    assert CliRunner().invoke(app, ["agent", "hook", "notify", "claude", "stop"], input=payload).exit_code == 0
    assert [notification.summary for notification in captured] == [f"✅ Claude Code · {tmp_path.name}"]


@pytest.mark.parametrize(
    "payload", [{"agent_id": "child"}, {"subagentType": "worker"}, {"hook_event_name": "SubagentStop"}]
)
def test_child_completion_never_announces_a_handoff(monkeypatch: pytest.MonkeyPatch, payload: dict[str, str]) -> None:
    captured: list[Notification] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, **_: captured.append(notification)
    )
    result = CliRunner().invoke(app, ["agent", "hook", "notify", "claude", "stop"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert captured == []


@pytest.mark.parametrize("payload", ["{}", "not json"])
def test_notify_failure_warns_on_stderr_without_failing_the_turn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: str
) -> None:
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    result = CliRunner().invoke(app, ["agent", "hook", "notify", "copilot", "stop"], input=payload)

    assert result.exit_code == 0
    assert result.stdout == ""
    assert "agent hook notify failed:" in result.stderr
    assert not (tmp_path / ".agents").exists()


@pytest.mark.parametrize("exists", [False, True], ids=["missing-config", "malformed-config"])
def test_broken_configuration_keeps_default_notifications(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exists: bool
) -> None:
    config = tmp_path / "broken.yaml"
    if exists:
        config.write_text("prune: [\n")
    captured: list[tuple[Notification, bool]] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, sound: captured.append((notification, sound))
    )

    result = CliRunner().invoke(
        app, ["--config", str(config), "agent", "hook", "notify", "copilot", "stop"], input="{}"
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr.startswith("agent hook notify used default settings:")
    assert result.stderr.count("\n") == 1
    assert captured == [(Notification("✅ Copilot", "Your turn"), True)]


def _fail(_state: State, _notification: Notification, **_options: bool) -> None:
    raise DotError("notifier exited with status 7")


def test_deeply_nested_hook_payload_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_module, "send_notification", _fail)

    # About a million levels exceed the interpreter stack while decoding.
    result = CliRunner().invoke(
        app, ["agent", "hook", "notify", "claude", "stop"], input="[" * 1_000_000 + "]" * 1_000_000
    )

    assert result.exit_code == 0
    assert result.exception is None
    assert result.stderr.startswith("agent hook notify failed:")


def test_notification_commands_cover_linux_and_darwin_escaping() -> None:
    linux = hooks.notification_command(
        ScriptedRunner({"notify-send"}),
        hooks.Notification("Done", "Turn finished"),
        system="linux",
    )
    assert linux == [
        "notify-send",
        "--app-name=dot",
        "--expire-time=10000",
        "--hint=boolean:suppress-sound:true",
        "Done",
        "Turn finished",
    ]

    darwin = hooks.notification_command(
        ScriptedRunner(),
        hooks.Notification('Done "now"', r"Turn \finished"),
        system="darwin",
    )
    assert darwin[0:2] == ["osascript", "-e"]
    assert r"Done \"now\"" in darwin[2]
    assert r"Turn \\finished" in darwin[2]


def test_notification_validation_and_minimal_platform_commands(tmp_path: Path) -> None:
    with pytest.raises(DotError, match="agent name is required"):
        hooks.build_notification("", "stop", None)
    with pytest.raises(DotError, match="unknown agent notify event"):
        hooks.build_notification("copilot", "unknown", None)

    minimal = hooks.build_notification("custom", "needs-input", None)
    assert minimal == hooks.Notification("⏳ custom", "Needs your input")
    assert (
        'display notification "Needs your input"'
        in hooks.notification_command(ScriptedRunner(), minimal, system="darwin")[2]
    )

    session_only = hooks.build_notification("copilot", "stop", tmp_path / "outside")
    assert session_only == hooks.Notification("✅ Copilot · outside", "Your turn")

    with pytest.raises(DotError, match="unsupported on plan9"):
        hooks.notification_command(ScriptedRunner(), minimal, system="plan9")
    with pytest.raises(DotError, match=r"install notify-send \(libnotify-bin\)"):
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
    state = make_state(runner)
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
        {"notify-send"},
        run=lambda _args, _cwd, _input_text, _check: CommandResult(
            "",
            "GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown: "
            "The name org.freedesktop.Notifications was not provided by any .service files",
            1,
        ),
    )
    state = make_state(runner)
    monkeypatch.setattr(hooks.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")

    hooks.send_notification(state, hooks.Notification("Done"))

    assert isinstance(state.stderr, StringIO)
    assert "notification skipped: no desktop notification service" in state.stderr.getvalue()


def test_notification_text_is_short_and_has_no_terminal_controls() -> None:
    notification = hooks.build_notification("copilot", "stop", Path("/work/\x1b[31mFix\n hooks\x1b[0m\x00"))
    assert notification.summary == "✅ Copilot · Fix hooks"
    long = hooks.build_notification("copilot", "stop", Path("/work") / ("x" * 100))
    assert long.summary == "✅ Copilot · " + "x" * 79 + "…"


@pytest.mark.parametrize("agent", ["claude", "agy", "copilot", "opencode"])
def test_all_harness_notifications_dispatch_on_macos_without_dbus(monkeypatch: pytest.MonkeyPatch, agent: str) -> None:
    monkeypatch.setattr(hooks.platform, "system", lambda: "Darwin")
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    runner = ScriptedRunner()
    notification = hooks.build_notification(agent, "stop", Path('/work/"quoted"'))
    hooks.send_notification(make_state(runner), notification)
    assert len(runner.calls) == 1
    assert runner.calls[0][:2] == ["osascript", "-e"]
    assert 'display notification "Your turn"' in runner.calls[0][2]
    assert r"\"quoted\"" in runner.calls[0][2]


def test_linux_notification_renders_body_as_text_without_actions() -> None:
    notification = hooks.Notification("Done", "Fix <hooks> & tests")
    command = hooks.notification_command(ScriptedRunner({"notify-send"}), notification, system="linux")
    assert "Fix &lt;hooks&gt; &amp; tests" in command
    assert not any("action" in argument for argument in command)


_PANES = [
    {"id": 3, "is_plugin": True, "title": "tab-bar", "tab_name": "Tab #1"},
    {"id": 7, "is_plugin": False, "title": "~/work", "tab_name": "shell"},
    {"id": 3, "is_plugin": False, "title": "✳ Fix \x1b[31mhooks\x1b[0m", "tab_name": "review"},
]


def _zellij(stdout: str, returncode: int = 0) -> ScriptedRunner:
    return ScriptedRunner({"zellij"}, run=lambda _args, _cwd, _input, _check: CommandResult(stdout, "", returncode))


def test_zellij_pane_reads_the_hook_pane_tab_and_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "dot")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "3")
    runner = _zellij(json.dumps(_PANES))

    assert hooks.zellij_pane(runner) == hooks.ZellijPane("dot", "review", "Fix hooks")
    assert runner.calls == [["zellij", "action", "list-panes", "--tab", "--json"]]


@pytest.mark.parametrize(
    ("pane_id", "stdout", "returncode"),
    [("9", json.dumps(_PANES), 0), ("3", "not json", 0), ("3", json.dumps(_PANES), 1), ("3", "{}", 0), ("x", "[]", 0)],
    ids=["unknown-pane", "malformed", "failed", "not-a-list", "bad-id"],
)
def test_zellij_pane_is_optional_context(
    monkeypatch: pytest.MonkeyPatch, pane_id: str, stdout: str, returncode: int
) -> None:
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "dot")
    monkeypatch.setenv("ZELLIJ_PANE_ID", pane_id)
    assert hooks.zellij_pane(_zellij(stdout, returncode)) is None


def test_zellij_pane_needs_a_session_and_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _zellij(json.dumps(_PANES))
    assert hooks.zellij_pane(runner) is None
    monkeypatch.setenv("ZELLIJ_SESSION_NAME", "dot")
    monkeypatch.setenv("ZELLIJ_PANE_ID", "3")
    assert hooks.zellij_pane(ScriptedRunner()) is None
    assert runner.calls == []


def test_notification_context_follows_tab_and_title_settings() -> None:
    pane = hooks.ZellijPane("dot", "review", "Fix hooks")
    build = hooks.build_notification
    assert build("claude", "stop", None, pane=pane, tab=True, title=True) == Notification(
        "✅ Claude Code", "dot/review", "Fix hooks"
    )
    assert build("claude", "stop", None, pane=pane, tab=False, title=True) == Notification(
        "✅ Claude Code", "Fix hooks"
    )
    assert build("claude", "stop", None, pane=pane, tab=True) == Notification("✅ Claude Code", "dot/review")
    assert build("claude", "stop", None, pane=pane) == Notification("✅ Claude Code", "Your turn")
    untitled = hooks.ZellijPane("dot", "", "")
    assert build("claude", "stop", None, pane=untitled, tab=True, title=True) == Notification("✅ Claude Code", "dot")


def test_notification_commands_render_detail_and_sound() -> None:
    notification = Notification("Done", "dot/<tab>", "Fix hooks")
    linux = hooks.notification_command(ScriptedRunner({"notify-send"}), notification, system="linux", sound=True)
    assert linux[-1] == "dot/&lt;tab&gt;\nFix hooks"
    darwin = hooks.notification_command(ScriptedRunner(), notification, system="darwin", sound=True)[2]
    assert darwin.endswith('subtitle "Fix hooks" sound name "Glass"')
    silent = hooks.notification_command(ScriptedRunner(), Notification("Done"), system="darwin")[2]
    assert "subtitle" not in silent
    assert "sound" not in silent


def test_linux_sound_plays_the_generated_chime_after_the_notification(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(hooks.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")
    runner = ScriptedRunner({"notify-send", "paplay"})

    hooks.send_notification(make_state(runner), Notification("Done"), sound=True)
    hooks.send_notification(make_state(runner), Notification("Done"))

    chime = tmp_path / ".cache/dot/notify.wav"
    assert [call[0] for call in runner.calls] == ["notify-send", "paplay", "notify-send"]
    assert runner.calls[1] == ["paplay", str(chime)]
    with wave.open(str(chime)) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 44_100)
        assert 0.3 < audio.getnframes() / audio.getframerate() < 0.5
    assert [path.name for path in chime.parent.iterdir()] == ["notify.wav"]


def test_linux_sound_names_its_fix_when_no_player_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hooks.platform, "system", lambda: "Linux")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/bus")
    runner = ScriptedRunner({"notify-send"})
    with pytest.raises(DotError, match=r"agent\.notify\.sound: false"):
        hooks.send_notification(make_state(runner), Notification("Done"), sound=True)
    assert [call[0] for call in runner.calls] == ["notify-send"]


def test_notify_hook_applies_configured_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = tmp_path / "dot.yaml"
    config.write_text("agent:\n  notify:\n    sound: false\n    title: false\n")
    monkeypatch.setattr(hooks, "zellij_pane", lambda _runner: hooks.ZellijPane("dot", "review", "Fix hooks"))
    monkeypatch.setattr(agent_module, "zellij_pane", hooks.zellij_pane)
    captured: list[tuple[Notification, bool]] = []
    monkeypatch.setattr(
        agent_module, "send_notification", lambda _state, notification, sound: captured.append((notification, sound))
    )

    result = CliRunner().invoke(
        app,
        ["--config", str(config), "agent", "hook", "notify", "claude", "needs-input"],
        input=json.dumps({"notification_type": "permission_prompt"}),
    )

    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""
    assert captured == [(Notification("⏳ Claude Code", "dot/review"), False)]
