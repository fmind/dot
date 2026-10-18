"""Native hook payloads and desktop notifications for agent events."""

import html
import json
import os
import platform
import re
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


@dataclass(frozen=True)
class Notification:
    summary: str
    headline: str = ""


def _short_notification_text(value: str) -> str:
    # Directory names are untrusted: remove escapes/control characters
    # and keep desktop banners to one short line.
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    text = " ".join("".join(char for char in value if char.isprintable() or char.isspace()).split())
    return text if len(text) <= 80 else text[:79].rstrip() + "…"


def build_notification(
    agent: str,
    event: str,
    cwd: Path | None,
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
    project = ""
    if cwd is not None:
        expanded = cwd.expanduser()
        resolved = expanded if expanded.is_absolute() else (Path.cwd() / expanded).absolute()
        project = _short_notification_text(resolved.name)
        summary += f" · {project}"
    return Notification(summary, headline)


def _apple_script_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notification_command(runner: Runner, notification: Notification, *, system: str | None = None) -> list[str]:
    host = (system or platform.system()).lower()
    if host == "darwin":
        script = (
            f"display notification {_apple_script_string(notification.headline)} "
            f"with title {_apple_script_string(notification.summary)}"
        )
        return ["osascript", "-e", script]
    if host != "linux":
        raise DotError(f"desktop notifications are unsupported on {host}")
    body = html.escape(notification.headline, quote=False)
    if runner.which("notify-send") is not None:
        return [
            "notify-send",
            "--app-name=dot",
            f"--expire-time={_NOTIFY_EXPIRE_MS}",
            notification.summary,
            body,
        ]
    if runner.which("gdbus") is not None:
        return [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.freedesktop.Notifications",
            "--object-path",
            "/org/freedesktop/Notifications",
            "--method",
            "org.freedesktop.Notifications.Notify",
            "dot",
            "uint32 0",
            "dialog-information",
            notification.summary,
            body,
            "@as []",
            "@a{sv} {}",
            f"int32 {_NOTIFY_EXPIRE_MS}",
        ]
    raise DotError("install notify-send or gdbus to send desktop notifications")


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


def send_notification(state: State, notification: Notification) -> None:
    host = platform.system().lower()
    if host not in {"darwin", "linux"} or (host == "linux" and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")):
        return
    command = notification_command(state.runner, notification, system=host)
    try:
        result = state.runner.run(command, timeout=10, check=False)
    except (DotError, OSError) as error:
        raise DotError(f"failed to send desktop notification with {command[0]}") from error
    if result.returncode != 0:
        # A session bus can exist in a container without a desktop notification
        # service. Treat that like a headless session, not a failed agent turn.
        if command[0] == "gdbus" and result.stderr.startswith(
            "Error: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown:"
        ):
            state.stderr.write("Desktop notification skipped: no desktop notification service.\n")
            return
        raise DotError(f"failed to send desktop notification with {command[0]}")


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
        # Both hosts report only in-flight work. Malformed/unknown values must
        # not be interpreted as an empty list and announce a false handoff.
        for field in ("background_tasks", "backgroundTasks", "session_crons", "sessionCrons"):
            if field in payload and payload[field] != []:
                return None
        if agent == "agy" and payload.get("fullyIdle") is not True:
            return None
    if agent in {"claude", "grok"}:
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
