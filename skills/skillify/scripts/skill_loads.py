"""Count the sessions that loaded each skill, from local agy, Claude Code, and Pi transcripts.

A load is a tool call that reads a catalog skill's SKILL.md (or Claude's Skill tool); catalog text
injected at startup and quoted prompts are not tool calls, so they never count. Only names and
counts leave the transcripts: no prompt, path, or message text is printed.
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

_SKILL_PATH = re.compile(r"(?:^|[/\"'])skills/([a-z0-9][a-z0-9-]*)/SKILL\.md")
_AGY_READS = {"read_file", "view_file"}


def _records(path: Path, marker: str) -> Iterator[dict[str, object]]:
    """Yield the JSON object lines that contain `marker`; transcripts can hold megabytes of other records."""
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if marker not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError, RecursionError:
                continue
            if isinstance(record, dict):
                yield record


def _dicts(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _paths(value: object) -> set[str]:
    return set(_SKILL_PATH.findall(json.dumps(value)))


def agy_loads(path: Path) -> set[str]:
    """Skills read through agy's file tools in one conversation transcript."""
    return {
        name
        for record in _records(path, "tool_calls")
        for call in _dicts(record.get("tool_calls"))
        if call.get("name") in _AGY_READS
        for name in _paths(call.get("args"))
    }


def claude_loads(path: Path) -> set[str]:
    """Skills invoked with Claude's Skill tool or read with its Read tool in one session transcript."""
    loads: set[str] = set()
    for record in _records(path, '"tool_use"'):
        message = record.get("message")
        for part in _dicts(message.get("content") if isinstance(message, dict) else None):
            if part.get("type") != "tool_use" or not isinstance(tool_input := part.get("input"), dict):
                continue
            if part.get("name") == "Skill" and isinstance(skill := tool_input.get("skill"), str):
                loads.add(skill)
            elif part.get("name") == "Read":
                loads |= _paths(tool_input.get("file_path"))
    return loads


def pi_loads(path: Path) -> set[str]:
    """Skills read through Pi's read tool in one session file."""
    loads: set[str] = set()
    for record in _records(path, '"toolCall"'):
        message = record.get("message")
        for part in _dicts(message.get("content") if isinstance(message, dict) else None):
            if part.get("type") == "toolCall" and part.get("name") == "read":
                loads |= _paths(part.get("arguments"))
    return loads


def agy_transcripts(root: Path) -> Iterator[Path]:
    for directory in root.iterdir() if root.is_dir() else ():
        logs = directory / ".system_generated" / "logs"
        found = next(
            (logs / name for name in ("transcript_full.jsonl", "transcript.jsonl") if (logs / name).is_file()), None
        )
        if found is not None:
            yield found


def session_files(root: Path) -> Iterator[Path]:
    # Claude subagent transcripts belong to their parent session's task; count top-level sessions.
    return (path for path in root.rglob("*.jsonl") if "subagents" not in path.parts) if root.is_dir() else iter(())


AGENTS = ("agy", "claude", "pi")


def count(
    home: Path, catalog: set[str], *, since: float, audit: int
) -> tuple[dict[str, int], dict[str, int], list[tuple[str, dict[str, int]]]]:
    """Return sessions seen, audit sessions excluded, and per-skill session counts, most loaded first.

    A session that loads `audit` skills or more is a catalog review, not a task.
    """
    sources = {
        "agy": (agy_transcripts(home / ".gemini/antigravity-cli/brain"), agy_loads),
        "claude": (session_files(home / ".claude/projects"), claude_loads),
        "pi": (session_files(home / ".pi/agent/sessions"), pi_loads),
    }
    loads = {agent: Counter[str]() for agent in AGENTS}
    sessions, audits = dict.fromkeys(AGENTS, 0), dict.fromkeys(AGENTS, 0)
    for agent, (paths, parse) in sources.items():
        for path in paths:
            try:
                if path.stat().st_mtime < since:
                    continue
                found = parse(path) & catalog
            except OSError:
                continue
            sessions[agent] += 1
            if len(found) >= audit:
                audits[agent] += 1
            else:
                loads[agent].update(found)
    rows = [(name, {agent: loads[agent][name] for agent in AGENTS}) for name in catalog]
    rows.sort(key=lambda row: (-sum(row[1].values()), row[0]))
    return sessions, audits, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("--days", type=int, default=30, metavar="N", help="Observation window in days (default: 30)")
    parser.add_argument(
        "--skills",
        type=Path,
        default=Path.home() / ".agents/skills",
        metavar="DIR",
        help="Catalog to measure: each <name>/SKILL.md below it (default: ~/.agents/skills)",
    )
    parser.add_argument(
        "--audit",
        type=int,
        default=8,
        metavar="N",
        help="Exclude a session that loaded N skills or more: a catalog review, not a task (default: 8)",
    )
    parser.add_argument("-j", "--json", action="store_true", help="Emit one JSON document")
    args = parser.parse_args()
    if args.days < 1 or args.audit < 2:
        parser.error("--days must be at least 1 and --audit at least 2")
    catalog = {path.parent.name for path in args.skills.glob("*/SKILL.md")}
    if not catalog:
        parser.error(f"no skills found under {args.skills}")
    sessions, audits, rows = count(Path.home(), catalog, since=time.time() - args.days * 86400, audit=args.audit)
    if args.json:
        document = {
            "schema": "skillify.skill-loads/v1",
            "days": args.days,
            "sessions": sessions,
            "audit_sessions_excluded": audits,
            "skills": [{"skill": name, **counts, "total": sum(counts.values())} for name, counts in rows],
        }
        sys.stdout.write(json.dumps(document, separators=(",", ":")) + "\n")
        return 0

    def summary(counts: dict[str, int]) -> str:
        return " ".join(f"{agent}={counts[agent]}" for agent in AGENTS)

    sys.stdout.write(
        f"Skill loads over {args.days} days · sessions: {summary(sessions)} · audits excluded: {summary(audits)}\n"
    )
    loaded = [(name, counts) for name, counts in rows if sum(counts.values())]
    width = max((len(name) for name, _ in loaded), default=0)
    for name, counts in loaded:
        sys.stdout.write(f"{name:<{width}}  {summary(counts)}\n")
    unloaded = [name for name, counts in rows if not sum(counts.values())]
    sys.stdout.write(f"No observed load ({len(unloaded)}): {' '.join(unloaded) or '-'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
