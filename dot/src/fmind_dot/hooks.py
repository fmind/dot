"""Native hook payloads and desktop notifications for agent events."""

import html
import json
import math
import os
import platform
import re
import struct
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from fmind_dot.archive.parsers import AGENT_ADAPTERS, resolve_cwd
from fmind_dot.errors import DotError
from fmind_dot.process import Runner
from fmind_dot.state import State

_NOTIFY_EVENTS = {
    "stop": ("✅", "Your turn"),
    "ready": ("✅", "Your turn"),
    "needs-input": ("⏳", "Needs your input"),
}
_NOTIFY_EXPIRE_MS = "10000"
_DARWIN_SOUND = "Glass"
_SOUND_PLAYERS = ("pw-play", "paplay")
_AGY_PRINT_FLAGS = (b"-p", b"--print", b"--prompt")


def agy_print_mode(proc: Path = Path("/proc"), pid: int | None = None) -> bool:
    """Whether the agy process running this hook answers a non-interactive print turn.

    agy's hook payload has no mode field, so read the nearest agy ancestor's arguments;
    hooks run through `sh -c`, so it is the parent or grandparent. Without /proc (macOS)
    or a readable ancestor, the hook keeps notifying as before.
    """
    pid = os.getppid() if pid is None else pid
    for _ in range(4):
        if pid <= 1:
            return False
        try:
            argv = (proc / str(pid) / "cmdline").read_bytes().split(b"\0")
            stat = (proc / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
            if Path(os.fsdecode(argv[0])).name == "agy":
                return any(
                    arg in _AGY_PRINT_FLAGS or arg.startswith((b"-p=", b"--print=", b"--prompt=")) for arg in argv
                )
            # The parent PID follows the parenthesized command name, which may contain spaces.
            pid = int(stat.rsplit(")", 1)[1].split()[1])
        except OSError, IndexError, ValueError:
            return False
    return False


@dataclass(frozen=True)
class Notification:
    summary: str
    headline: str = ""
    # Second body line (the pane title); macOS shows it as the subtitle.
    detail: str = ""


@dataclass(frozen=True)
class ZellijPane:
    session: str
    tab: str
    title: str


def _short_notification_text(value: str) -> str:
    # Directory names are untrusted: remove escapes/control characters
    # and keep desktop banners to one short line.
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    text = " ".join("".join(char for char in value if char.isprintable() or char.isspace()).split())
    return text if len(text) <= 80 else text[:79].rstrip() + "…"


def _pane_title(value: str) -> str:
    # Harnesses prefix titles with a status glyph (Claude's ✳ or braille spinner); keep the topic.
    text = _short_notification_text(value)
    while text and (unicodedata.category(text[0]) == "So" or text[0].isspace()):
        text = text[1:]
    return text


def zellij_pane(runner: Runner) -> ZellijPane | None:
    """Find the Zellij pane that runs this hook; hooks inherit the harness pane's environment.

    Context is optional: outside Zellij, or when the lookup fails, the notification goes without it.
    """
    session, pane_id = os.environ.get("ZELLIJ_SESSION_NAME", ""), os.environ.get("ZELLIJ_PANE_ID", "")
    if not session or not pane_id.isdecimal() or runner.which("zellij") is None:
        return None
    try:
        result = runner.run(["zellij", "action", "list-panes", "--tab", "--json"], timeout=3, check=False)
        panes = json.loads(result.stdout) if result.returncode == 0 else []
    except DotError, OSError, ValueError, RecursionError:
        return None
    for pane in panes if isinstance(panes, list) else []:
        if isinstance(pane, dict) and pane.get("is_plugin") is False and pane.get("id") == int(pane_id):
            tab, title = pane.get("tab_name"), pane.get("title")
            return ZellijPane(
                _short_notification_text(session),
                _short_notification_text(tab) if isinstance(tab, str) else "",
                _pane_title(title) if isinstance(title, str) else "",
            )
    return None


def build_notification(
    agent: str,
    event: str,
    cwd: Path | None,
    *,
    pane: ZellijPane | None = None,
    tab: bool = False,
    title: bool = False,
) -> Notification:
    if not agent:
        raise DotError("agent name is required")
    try:
        icon, headline = _NOTIFY_EVENTS[event]
    except KeyError as error:
        choices = ", ".join(sorted(_NOTIFY_EVENTS))
        raise DotError(f"unknown agent notify event {event!r} (want one of: {choices})") from error
    adapter = AGENT_ADAPTERS.get(agent)
    label = adapter.notify_label if adapter else agent
    summary = f"{icon} {label}"
    if cwd is not None:
        # Hook payload workspaces are already resolved to absolute paths.
        summary += f" · {_short_notification_text(cwd.name)}"
    # The icon already states the event, so pane context replaces the status words when present.
    location = (pane.session + (f"/{pane.tab}" if pane.tab else "")) if pane and tab else ""
    topic = pane.title if pane and title else ""
    lines = [line for line in (location, topic) if line] or [headline]
    return Notification(summary, *lines)


def _apple_script_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notification_command(runner: Runner, notification: Notification, *, system: str, sound: bool = False) -> list[str]:
    host = system.lower()
    if host == "darwin":
        script = (
            f"display notification {_apple_script_string(notification.headline)} "
            f"with title {_apple_script_string(notification.summary)}"
        )
        if notification.detail:
            script += f" subtitle {_apple_script_string(notification.detail)}"
        if sound:
            script += f" sound name {_apple_script_string(_DARWIN_SOUND)}"
        return ["osascript", "-e", script]
    if host != "linux":
        raise DotError(f"desktop notifications are unsupported on {host}")
    body = "\n".join(line for line in (notification.headline, notification.detail) if line)
    if runner.which("notify-send") is None:
        raise DotError("install notify-send (libnotify-bin) to send desktop notifications")
    # dot plays its own chime on Linux (servers such as ChromeOS notificationd play none), so the
    # server's theme sound stays off and the setting behaves the same on every desktop.
    return [
        "notify-send",
        "--app-name=dot",
        f"--expire-time={_NOTIFY_EXPIRE_MS}",
        "--hint=boolean:suppress-sound:true",
        notification.summary,
        html.escape(body, quote=False),
    ]


def chime_path() -> Path:
    """Write dot's two-note chime once; the WAV is generated, so no sound theme is required."""
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    path = cache / "dot" / "notify.wav"
    if path.is_file():
        return path
    rate, frames = 44_100, bytearray()
    for frequency, seconds in ((880.0, 0.12), (1318.5, 0.24)):
        count = int(rate * seconds)
        for index in range(count):
            # A 5 ms attack avoids a click; the exponential decay sounds like a soft bell.
            envelope = min(1.0, index / (rate * 0.005)) * math.exp(-12 * index / rate)
            sample = 0.3 * envelope * math.sin(2 * math.pi * frequency * index / rate)
            frames += struct.pack("<h", round(sample * 32_767))
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}")
    with wave.open(str(partial), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(bytes(frames))
    partial.replace(path)
    return path


def play_chime(runner: Runner) -> None:
    player = next((name for name in _SOUND_PLAYERS if runner.which(name) is not None), None)
    if player is None:
        raise DotError(
            "install pw-play (PipeWire) or paplay (PulseAudio) to play notification sounds, "
            "or set agent.notify.sound: false with dot config edit"
        )
    result = runner.run([player, str(chime_path())], timeout=5, check=False)
    if result.returncode != 0:
        raise DotError(f"failed to play notification sound with {player}")


def read_hook_payload(stream: IO[str] | None) -> dict[str, Any] | None:
    """Decode the common hook envelope and reject ambiguous boolean guards."""
    if stream is None:
        return None
    try:
        if stream.isatty():
            return None
    except AttributeError, OSError:
        pass
    payload = stream.read()
    if not payload.strip():
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise DotError(f"failed to parse agent hook input: {error}") from error
    except RecursionError:
        # Hooks must exit 0: deep nesting is malformed input, never an uncaught crash.
        raise DotError("failed to parse agent hook input: JSON is nested too deeply") from None
    if not isinstance(decoded, dict):
        raise DotError("failed to parse agent hook input: expected a JSON object")
    for field in ("stop_hook_active", "stopHookActive", "fullyIdle"):
        if field in decoded and not isinstance(decoded[field], bool):
            raise DotError(f"failed to parse agent hook input: {field} must be a boolean")
    return decoded


def send_notification(state: State, notification: Notification, *, sound: bool = False) -> None:
    host = platform.system().lower()
    if host not in {"darwin", "linux"} or (host == "linux" and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")):
        return
    command = notification_command(state.runner, notification, system=host, sound=sound)
    try:
        result = state.runner.run(command, timeout=10, check=False)
    except (DotError, OSError) as error:
        raise DotError(f"failed to send desktop notification with {command[0]}") from error
    if result.returncode != 0:
        # A session bus can exist in a container without a desktop notification
        # service. Treat that like a headless session, not a failed agent turn.
        if result.stderr.startswith("GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown:"):
            state.stderr.write("Desktop notification skipped: no desktop notification service.\n")
            return
        raise DotError(f"failed to send desktop notification with {command[0]}")
    if sound and host == "linux":
        play_chime(state.runner)


def notification_workspace(stream: IO[str] | None, agent: str, event: str = "stop") -> str | None:
    """Return the payload workspace, or None when the event must stay quiet.

    Native idle notifications mean attention is due; Stop alone is only a proposal
    to finish. Keep legacy Stop invocations quiet when work can still continue.
    """
    payload = read_hook_payload(stream)
    if payload is None:
        return None
    if event in {"stop", "ready"}:
        if payload.get("stop_hook_active") is True or payload.get("stopHookActive") is True:
            return None
        if any(payload.get(key) for key in ("agent_id", "agentId", "subagentId", "subagentType")):
            return None
        # Claude and agy report only in-flight work. Malformed/unknown values must
        # not be interpreted as an empty list and announce a false handoff.
        for field in ("background_tasks", "backgroundTasks", "session_crons", "sessionCrons"):
            if field in payload and payload[field] != []:
                return None
        if agent == "agy" and payload.get("fullyIdle") is not True:
            return None
    # Headless agy runs (scheduled assistants, loops) end without anyone waiting for them.
    if agent == "agy" and agy_print_mode():
        return None
    if agent == "claude":
        kind = payload.get("notification_type", payload.get("notificationType"))
        if event == "ready" and kind != "idle_prompt":
            return None
        if event == "needs-input" and kind not in {
            "permission_prompt",
            "elicitation_dialog",
            "elicitation_url_dialog",
            "agent_needs_input",
        }:
            return None
    native_event = payload.get("hook_event_name", payload.get("hookEventName", ""))
    if native_event in {"SubagentStop", "subagentStop", "subagent_stop", "SubagentEnd"}:
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        paths = payload.get("workspacePaths")
        cwd = next((item for item in paths if isinstance(item, str) and item), "") if isinstance(paths, list) else ""
    return resolve_cwd(cwd)
