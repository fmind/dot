"""Native hook payloads and desktop notifications for agent events."""

import html
import json
import os
import platform
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from fmind_dot.archive.parsers import resolve_cwd
from fmind_dot.errors import DotError
from fmind_dot.process import PROBE_OUTPUT_LIMIT_BYTES, Runner
from fmind_dot.state import State

_NOTIFY_EVENTS = {
    "stop": ("✅", "Turn finished"),
    "session-end": ("🏁", "Session ended"),
    "needs-input": ("⏳", "Needs your input"),
}
_NOTIFY_AGENTS = {
    "agy": "Antigravity",
    "antigravity": "Antigravity",
    "claude": "Claude Code",
    "codex": "Codex",
    "copilot": "Copilot",
    "grok": "Grok Build",
}
_NOTIFY_EXPIRE_MS = "10000"


@dataclass(frozen=True)
class Notification:
    summary: str
    headline: str = ""
    details: tuple[str, ...] = ()


def notification_title(runner: Runner, getenv: Callable[[str], str | None] = os.environ.get) -> str:
    """Read only the originating terminal title; unavailable metadata is optional."""
    pane = getenv("ZELLIJ_PANE_ID") or ""
    if not getenv("ZELLIJ_SESSION_NAME") or not pane.isascii() or not pane.isdecimal() or not runner.which("zellij"):
        return ""
    try:
        result = runner.run_bounded(
            ["zellij", "action", "list-panes", "--json"],
            max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
            timeout=1,
            check=False,
        )
        if result.returncode or result.stdout_truncated:
            return ""
        panes = json.loads(result.stdout)
    except DotError, OSError, ValueError:
        return ""
    if not isinstance(panes, list):
        return ""
    for item in panes:
        if not isinstance(item, dict) or item.get("is_plugin") is not False or item.get("id") != int(pane):
            continue
        title = item.get("title")
        if not isinstance(title, str):
            return ""
        # Codex titles include a changing status and project around the task.
        parts = title.split(" | ")
        if len(parts) >= 3 and re.match(r"^\[[^\]]+\] ", parts[0]):
            title = " | ".join(parts[1:-1])
        return title
    return ""


def _short_notification_text(value: str) -> str:
    # Titles are untrusted terminal metadata: remove escapes/control characters
    # and keep desktop banners to one short line per field.
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    text = " ".join("".join(char for char in value if char.isprintable() or char.isspace()).split())
    return text if len(text) <= 80 else text[:79].rstrip() + "…"


def build_notification(
    agent: str,
    event: str,
    cwd: Path | None,
    *,
    title: str = "",
) -> Notification:
    if not agent:
        raise DotError("agent name is required")
    try:
        icon, headline = _NOTIFY_EVENTS[event]
    except KeyError as error:
        choices = ", ".join(sorted(_NOTIFY_EVENTS))
        raise DotError(f"unknown agent notify event {event!r} (want one of: {choices})") from error
    label = _NOTIFY_AGENTS.get(agent, agent)
    summary = f"{icon} {label}"
    project = ""
    if cwd is not None:
        expanded = cwd.expanduser()
        resolved = expanded if expanded.is_absolute() else (Path.cwd() / expanded).absolute()
        project = _short_notification_text(resolved.name)
        summary += f" · {project}"
    title = _short_notification_text(title)
    details = (
        (title,) if title and title.casefold() not in {agent.casefold(), label.casefold(), project.casefold()} else ()
    )
    return Notification(summary, headline, details)


def _notification_body(notification: Notification) -> str:
    return "\n".join((notification.headline, *notification.details)).strip()


def _apple_script_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notification_command(runner: Runner, notification: Notification, *, system: str | None = None) -> list[str]:
    host = (system or platform.system()).lower()
    if host == "darwin":
        details = " · ".join(notification.details)
        if details:
            script = (
                f"display notification {_apple_script_string(details)} "
                f"with title {_apple_script_string(notification.summary)} "
                f"subtitle {_apple_script_string(notification.headline)}"
            )
        else:
            script = (
                f"display notification {_apple_script_string(notification.headline)} "
                f"with title {_apple_script_string(notification.summary)}"
            )
        return ["osascript", "-e", script]
    if host != "linux":
        raise DotError(f"desktop notifications are unsupported on {host}")
    body = html.escape(_notification_body(notification), quote=False)
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


def notification_workspace(stream: IO[str] | None, agent: str) -> str | None:
    """Return the payload workspace, or None when the event must stay quiet.

    A re-entrant stop hook, or an Antigravity turn that is not fully idle, is not a finished turn.
    """
    payload = read_hook_payload(stream)
    if payload is None:
        return ""
    if payload.get("stop_hook_active") is True or payload.get("stopHookActive") is True:
        return None
    if agent == "agy" and payload.get("fullyIdle") is not True:
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        paths = payload.get("workspacePaths")
        cwd = next((item for item in paths if isinstance(item, str) and item), "") if isinstance(paths, list) else ""
    return resolve_cwd(cwd)
