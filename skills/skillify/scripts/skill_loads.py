"""Count the sessions that loaded each skill from local agy transcripts.

A load is a file-read tool call touching a catalog skill's SKILL.md, references/, scripts/, assets/, or templates/;
catalog text injected at startup and quoted prompts are not tool calls, so they never count. Only names and counts
leave the transcripts: no prompt, path, or message text is printed.

Limits: path matching also counts repo edits reading `skills/<name>/...` inside a dotfiles checkout (not only
`~/.agents/skills/`), and only local `agy` transcripts are scanned (Copilot CLI sessions are not counted).
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

_SKILL_PATH = re.compile(
    r"(?:^|[/\"'])skills/([a-z0-9][a-z0-9-]*)/(?:SKILL\.md|references/|scripts/|assets/|templates/)"
)
_CREATED_RE = re.compile(r"^\s*created:\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?\s*$", re.MULTILINE)
_AGY_READS = frozenset({"read_file", "view_file"})


def _loads_line(line: bytes) -> dict[str, object] | None:
    try:
        record = json.loads(line)
    except UnicodeDecodeError:
        try:
            record = json.loads(line.decode("utf-8", errors="replace"))
        except (ValueError, RecursionError):  # fmt: skip
            return None
    except (ValueError, RecursionError):  # fmt: skip
        return None
    return record if isinstance(record, dict) else None


def agy_loads(path: Path) -> set[str]:
    """Skills read through agy's file tools in one conversation transcript."""
    loads: set[str] = set()
    with path.open("rb") as stream:
        for line in stream:
            if b"skills" not in line or b"tool_calls" not in line:
                continue
            if (record := _loads_line(line)) is None or not isinstance(calls := record.get("tool_calls"), list):
                continue
            for call in calls:
                if isinstance(call, dict) and call.get("name") in _AGY_READS:
                    loads.update(_SKILL_PATH.findall(json.dumps(call.get("args"))))
    return loads


def agy_transcripts(root: Path) -> Iterator[Path]:
    try:
        directories = list(root.iterdir()) if root.is_dir() else []
    except OSError:
        return
    for directory in directories:
        logs = directory / ".system_generated" / "logs"
        try:
            found = next(
                (logs / name for name in ("transcript.jsonl", "transcript_full.jsonl") if (logs / name).is_file()),
                None,
            )
        except OSError:
            continue
        if found is not None:
            yield found


def _agy_parents(db_path: Path) -> dict[str, str]:
    if not db_path.is_file():
        return {}
    try:
        with closing(sqlite3.connect(f"file:{quote(str(db_path))}?mode=ro", uri=True)) as conn:
            rows = conn.execute(
                "SELECT conversation_id, parent_conversation_id FROM conversation_summaries "
                "WHERE parent_conversation_id IS NOT NULL AND parent_conversation_id != ''"
            ).fetchall()
    except (sqlite3.Error, OSError):  # fmt: skip
        return {}
    return {
        cid: pid for cid, pid in rows if isinstance(cid, str) and isinstance(pid, str) and cid and pid and cid != pid
    }


def _agy_groups(app_dir: Path, *, since: float) -> list[list[Path]]:
    parents = _agy_parents(app_dir / "conversation_summaries.db")
    groups: dict[str, list[tuple[float, Path]]] = {}
    for path in agy_transcripts(app_dir / "brain"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        cid = path.parents[2].name
        seen = {cid}
        while (parent := parents.get(cid)) and parent not in seen:
            seen.add(parent)
            cid = parent
        groups.setdefault(cid, []).append((mtime, path))
    return [[path for _, path in entries] for entries in groups.values() if max(mtime for mtime, _ in entries) >= since]


def count(home: Path, catalog: set[str], *, since: float, audit: int) -> tuple[int, int, list[tuple[str, int]]]:
    """Return sessions seen, audit sessions excluded, and per-skill session counts, most loaded first."""
    loads: Counter[str] = Counter()
    sessions = audits = 0
    for group in _agy_groups(home / ".gemini/antigravity-cli", since=since):
        found: set[str] = set()
        readable = False
        for path in group:
            try:
                found |= agy_loads(path)
                readable = True
            except OSError:
                continue
        if not readable:
            continue
        matched = found & catalog
        sessions += 1
        if len(matched) >= audit:
            audits += 1
        else:
            loads.update(matched)
    rows = [(name, loads[name]) for name in catalog]
    rows.sort(key=lambda row: (-row[1], row[0]))
    return sessions, audits, rows


def _created_dates(skills_dir: Path, days: int) -> tuple[dict[str, str], set[str]]:
    """Return all `{skill_name: YYYY-MM-DD}` created dates and the subset created within `days` days."""
    today = datetime.now(tz=timezone.utc).date()  # noqa: UP017 - keep Python 3.10 runtime compatibility
    all_dates: dict[str, str] = {}
    recent: set[str] = set()
    for skill_md in skills_dir.glob("*/SKILL.md"):
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")[:1500]
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        match = _CREATED_RE.search(text[3:end] if end != -1 else text)
        if not match:
            continue
        try:
            created = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        name = skill_md.parent.name
        all_dates[name] = match.group(1)
        if (today - created).days <= days:
            recent.add(name)
    return all_dates, recent


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
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
    catalog = {path.parent.name for path in args.skills.glob("*/SKILL.md") if path.is_file()}
    if not catalog:
        parser.error(f"no skills found under {args.skills}")
    sessions, audits, rows = count(Path.home(), catalog, since=time.time() - args.days * 86400, audit=args.audit)
    all_created, recent = _created_dates(args.skills, args.days)
    if args.json:
        document = {
            "schema": "skillify.skill-loads/v2",
            "days": args.days,
            "sessions": sessions,
            "audit_sessions_excluded": audits,
            "skills": [
                {"skill": name, "loads": total, "created": all_created.get(name), "is_new": name in recent}
                for name, total in rows
            ],
        }
        sys.stdout.write(json.dumps(document, separators=(",", ":")) + "\n")
        return 0

    sys.stdout.write(f"Skill loads over {args.days} days · sessions: {sessions} · audits excluded: {audits}\n")
    loaded = [(name, total) for name, total in rows if total]
    width = max((len(name) for name, _ in loaded), default=0)
    for name, total in loaded:
        sys.stdout.write(f"{name:<{width}}  {total}\n")
    unloaded = [name for name, total in rows if not total]
    unloaded_labels = [f"{name}(new:{all_created[name]})" if name in recent else name for name in unloaded]
    sys.stdout.write(f"No observed load ({len(unloaded)}): {' '.join(unloaded_labels) or '-'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
