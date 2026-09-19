"""Native hook payloads for desktop notifications."""

from typing import IO

from fmind_dot.archive.parsers import resolve_cwd
from fmind_dot.system import read_hook_payload


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
