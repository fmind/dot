"""Render agy's state payload as a compact status line or plain terminal title."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections.abc import Mapping
from pathlib import PurePath

ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))")


def clean(value: object) -> str:
    """Strip terminal controls and constrain each untrusted display field."""
    if not isinstance(value, str):
        return ""
    return " ".join("".join(c for c in ANSI.sub("", value[:2048]) if c.isprintable()).split())[:80]


def record(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def number(value: object, maximum: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) and 0 <= result <= maximum else None


def char_columns(char: str) -> int:
    return 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def columns(text: str) -> int:
    return sum(char_columns(c) for c in text)


def clip(text: str, width: int) -> str:
    """Fit terminal columns, including wide characters and combining marks."""
    if columns(text) <= width:
        return text
    if width < 1:
        return ""
    kept, used = [], 0
    for char in text:
        used += char_columns(char)
        if used > width - 1:
            break
        kept.append(char)
    return "".join(kept) + "…"


def fit(segments: list[tuple[str, str, int]], width: int) -> list[tuple[str, str, int]]:
    """Drop optional details before shortening the project or activity."""
    while sum(columns(s[0]) for s in segments) + 2 * (len(segments) - 1) > width:
        optional = [(s[2], i) for i, s in enumerate(segments) if s[2] > 0]
        if not optional:
            break
        segments.pop(max(optional)[1])
    if len(segments) == 2 and sum(columns(s[0]) for s in segments) + 2 > width:
        project, activity = segments
        available = width - columns(activity[0]) - 2
        if available > 0:
            segments[0] = (clip(project[0], available), project[1], 0)
        else:
            return [(clip(activity[0], width), activity[1], 0)]
    return segments


def render(payload: Mapping[str, object], mode: str, *, color: bool = False) -> str:
    workspace = record(payload.get("workspace"))
    paths = [workspace.get("project_dir"), workspace.get("current_dir"), payload.get("cwd")]
    path = next((p for p in paths if isinstance(p, str) and p), "")
    project = clean(PurePath(path).name) or "agy"
    vcs = record(payload.get("vcs"))
    branch = clean(vcs.get("branch"))
    dirty = vcs.get("dirty") is True
    state = "needs input" if payload.get("tool_confirmation_pending") is True else clean(payload.get("agent_state"))
    tasks = number(payload.get("task_count"), 10000)
    if state == "idle" and tasks:
        state = "background"
    state = state.replace("tool_use", "working").replace("initializing", "starting") or "starting"
    if mode == "title":
        title = project + ("*" if dirty else "") + " — " + state
        if tasks:
            title += f" · {tasks:.0f} tasks"
        return clip(title, 80)
    # ANSI slots inherit fmind/theme through Ghostty; avoid hard-coded RGB colors.
    activity_color = "33" if state in {"needs input", "thinking", "background"} else "32" if state == "idle" else "34"
    segments = [(clip(project, 28), "1;34", 0)]
    if branch:
        segments.append((clip(branch, 20) + ("*" if dirty else ""), "90", 5))
    elif dirty:
        segments[0] = (segments[0][0] + "*", "1;34", 0)
    segments.append((state, activity_color, 0))
    model = record(payload.get("model"))
    name = clean(model.get("display_name")) or clean(model.get("id"))
    if name:
        segments.append((clip(name, 48), "35", 3))
    execution_mode = clean(payload.get("execution_mode"))
    if execution_mode:
        segments.append((clip(execution_mode, 16), "90", 6))
    context = number(record(payload.get("context_window")).get("used_percentage"), 100)
    if context is not None:
        shade = "31" if context >= 95 else "33" if context >= 80 else "36"
        segments.append((f"context {context:.0f}%", shade, 2))
    if tasks:
        segments.append((f"{tasks:.0f} tasks", "36", 1))
    queued = number(payload.get("pending_input_count"), 10000)
    if queued:
        segments.append((f"{queued:.0f} queued", "33", 1))
    artifacts = number(payload.get("artifact_count"), 10000)
    if artifacts:
        segments.append((f"{artifacts:.0f} artifacts", "90", 7))
    quotas = [
        fraction
        for bucket in record(payload.get("quota")).values()
        if (fraction := number(record(bucket).get("remaining_fraction"), 1)) is not None
    ]
    # Multiple buckets need not belong to the selected model; label the minimum explicitly.
    if quotas:
        remaining = min(quotas) * 100
        segments.append(
            (f"quota min {remaining:.0f}% left", "31" if remaining <= 5 else "33" if remaining <= 20 else "90", 4)
        )
    vim_mode = clean(record(payload.get("vim")).get("mode"))
    if vim_mode:
        segments.append((f"vim {vim_mode}", "90", 6))
    if record(payload.get("sandbox")).get("enabled") is True:
        segments.append(("sandbox", "32", 1))
    width = number(payload.get("terminal_width"), 10000)
    fitted = fit(segments, max(1, int(width) - 1) if width else 120)
    return "  ".join(f"\x1b[{shade}m{text}\x1b[0m" if color else text for text, shade, _priority in fitted)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in {"statusline", "title"}:
        sys.stderr.write("Usage: display.py statusline|title\n")
        raise SystemExit(2)
    # Display failures stay quiet and cannot leak input, account details, or exception locals.
    try:
        raw = sys.stdin.read(131073)
        payload = json.loads(raw) if len(raw) <= 131072 else None
    except (ValueError, RecursionError, OSError):
        payload = None
    color = "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    sys.stdout.write(render(record(payload), mode, color=color) + "\n")


if __name__ == "__main__":
    main()
