"""Render agy's state payload as a compact status line or plain terminal title."""

from __future__ import annotations

import json
import math
import os
import posixpath
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


# Ghostty supplies GoogleSansCode Nerd Font Mono, so private-use glyphs render one column wide.
SEPARATOR = " \ue0b1 "
ICONS = {
    "project": "\uf07b",
    "branch": "\ue0a0",
    "model": "\uf2db",
    "mode": "\uf013",
    "context": "\uf0e4",
    "tasks": "\uf0ae",
    "queued": "\uf086",
    "artifacts": "\uf15b",
    "sandbox": "\uf023",
    "vim": "\ue62b",
}
# Activity icon and ANSI color; unknown states fall back to the working spinner.
STATES = {
    "needs input": ("\uf071", "1;33"),
    "thinking": ("\uf0eb", "33"),
    "background": ("\uf017", "33"),
    "idle": ("\uf00c", "32"),
}
# Keyed by the first letter so labels such as "-- V-LINE --" share the visual color.
VIM_COLORS = {"N": "34", "I": "32", "V": "35"}


def fit(segments: list[tuple[str, str, int]], width: int) -> list[tuple[str, str, int]]:
    """Drop optional details before shortening the project or activity."""
    gap = columns(SEPARATOR)
    while sum(columns(s[0]) for s in segments) + gap * (len(segments) - 1) > width:
        optional = [(s[2], i) for i, s in enumerate(segments) if s[2] > 0]
        if not optional:
            break
        segments.pop(max(optional)[1])
    if len(segments) == 2 and sum(columns(s[0]) for s in segments) + gap > width:
        project, activity = segments
        available = width - columns(activity[0]) - gap
        if available > 0:
            segments[0] = (clip(project[0], available), project[1], 0)
        else:
            return [(clip(activity[0], width), activity[1], 0)]
    return segments


def tokens(count: float) -> str:
    if count >= 999_500:
        return f"{count / 1_000_000:.1f}".removesuffix(".0") + "M"
    return f"{count / 1000:.0f}k" if count >= 999.5 else f"{count:.0f}"


def duration(seconds: float) -> str:
    minutes = math.ceil(seconds / 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"


def location(workspace: Mapping[str, object], cwd: object) -> tuple[str, str]:
    """Return the project name and the subdirectory when agy runs below its root."""
    project_dir, current_dir = workspace.get("project_dir"), workspace.get("current_dir")
    path = next((p for p in (project_dir, current_dir, cwd) if isinstance(p, str) and p), "")
    name = clean(PurePath(path).name) or "agy"
    if isinstance(project_dir, str) and project_dir and isinstance(current_dir, str):
        try:
            relative = PurePath(posixpath.normpath(current_dir)).relative_to(posixpath.normpath(project_dir))
        except ValueError:
            return name, ""
        if relative.parts:
            return name, "/" + clean(relative.as_posix())
    return name, ""


def render(payload: Mapping[str, object], mode: str, *, color: bool = False) -> str:
    workspace = record(payload.get("workspace"))
    vcs = record(payload.get("vcs"))
    branch = clean(vcs.get("branch"))
    dirty = vcs.get("dirty") is True
    state = "needs input" if payload.get("tool_confirmation_pending") is True else clean(payload.get("agent_state"))
    tasks = number(payload.get("task_count"), 10000)
    if state == "idle" and tasks:
        state = "background"
    state = state.replace("tool_use", "working").replace("initializing", "starting") or "starting"
    name, subdirectory = location(workspace, payload.get("cwd"))
    if mode == "title":
        title = name + ("*" if dirty else "") + " — " + state
        if tasks:
            title += f" · {tasks:.0f} tasks"
        return clip(title, 80)
    # ANSI slots inherit fmind/theme through Ghostty; avoid hard-coded RGB colors.
    icon, activity_color = STATES.get(state, ("\uf110", "34"))
    project = ICONS["project"] + " " + clip(name + subdirectory, 40)
    segments = [(project, "1;34", 0)]
    if branch:
        segments.append((f"{ICONS['branch']} {clip(branch, 20)}{'*' if dirty else ''}", "33" if dirty else "90", 5))
    elif dirty:
        segments[0] = (project + "*", "1;34", 0)
    segments.append((f"{icon} {state}", activity_color, 0))
    model = record(payload.get("model"))
    model_name = clean(model.get("display_name")) or clean(model.get("id"))
    if model_name:
        segments.append((f"{ICONS['model']} {clip(model_name, 48)}", "35", 3))
    execution_mode = clean(payload.get("execution_mode"))
    if execution_mode:
        segments.append((f"{ICONS['mode']} {clip(execution_mode, 16)}", "90", 6))
    window = record(payload.get("context_window"))
    context = number(window.get("used_percentage"), 100)
    if context is not None:
        shade = "31" if context >= 95 else "33" if context >= 80 else "36"
        text = f"{ICONS['context']} context {context:.0f}%"
        size = number(window.get("context_window_size"), 10**9)
        if size:
            text += f" · {tokens(size * context / 100)}/{tokens(size)}"
        segments.append((text, shade, 2))
    if tasks:
        segments.append((f"{ICONS['tasks']} {tasks:.0f} tasks", "36", 1))
    queued = number(payload.get("pending_input_count"), 10000)
    if queued:
        segments.append((f"{ICONS['queued']} {queued:.0f} queued", "33", 1))
    artifacts = number(payload.get("artifact_count"), 10000)
    if artifacts:
        segments.append((f"{ICONS['artifacts']} {artifacts:.0f} artifacts", "90", 7))
    quotas = [
        (fraction, number(record(bucket).get("reset_in_seconds"), 10**8))
        for bucket in record(payload.get("quota")).values()
        if (fraction := number(record(bucket).get("remaining_fraction"), 1)) is not None
    ]
    # Multiple buckets need not belong to the selected model; label the minimum explicitly.
    if quotas:
        fraction, reset = min(quotas, key=lambda q: q[0])
        remaining = fraction * 100
        # Battery glyphs run full (U+F240) to empty (U+F244).
        text = f"{chr(0xF244 - round(fraction * 4))} quota min {remaining:.0f}% left"
        if reset:
            text += f" ↻ {duration(reset)}"
        segments.append((text, "31" if remaining <= 5 else "33" if remaining <= 20 else "90", 4))
    vim_mode = clean(record(payload.get("vim")).get("mode"))
    if vim_mode:
        segments.append((f"{ICONS['vim']} {vim_mode}", VIM_COLORS.get(vim_mode.strip("- ")[:1], "90"), 6))
    sandbox = record(payload.get("sandbox"))
    if sandbox.get("enabled") is True:
        network = sandbox.get("allow_network") is True
        segments.append((f"{ICONS['sandbox']} sandbox{' +net' if network else ''}", "33" if network else "32", 1))
    width = number(payload.get("terminal_width"), 10000)
    fitted = fit(segments, max(1, int(width) - 1) if width else 120)
    if not color:
        return SEPARATOR.join(text for text, _shade, _priority in fitted)
    return f"\x1b[90m{SEPARATOR}\x1b[0m".join(f"\x1b[{shade}m{text}\x1b[0m" for text, shade, _priority in fitted)


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
