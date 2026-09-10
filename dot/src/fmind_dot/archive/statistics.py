"""Content-free statistics derived from existing normalized archives."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from statistics import median
from typing import Any

from fmind_dot.archive.query import SessionQuery, discover_session_generations, query_session_summaries
from fmind_dot.archive.store import generation_files, validate_session_generation


def session_statistics(query: SessionQuery) -> dict[str, Any]:
    """Count current sessions separately from retained immutable generations."""
    summaries = query_session_summaries(query, latest_only=True)
    identities = {(item.agent, item.lineage_id) for item in summaries}
    generations = [
        item for item in discover_session_generations() if (item.manifest.agent, item.manifest.lineage_id) in identities
    ]
    return {
        "schema": "dot.agent.sessions.stats/v1",
        "time_basis": "latest generation ingestion timestamp",
        "sessions": len(summaries),
        "generations": len(generations),
        "superseded_generations": len(generations) - len(summaries),
        "archive_bytes": sum(
            (item.path / name).lstat().st_size for item in generations for name in generation_files(item.manifest)
        ),
        "conversation_records": sum(item.record_count for item in summaries),
        "malformed_records": sum(item.malformed_records for item in summaries),
        "ignored_records": sum(item.skipped_records for item in summaries),
        "agents": dict(sorted(Counter(item.agent for item in summaries).items())),
        "statuses": dict(sorted(Counter(status for item in summaries for status in item.status).items())),
        "content_validated": False,
    }


def prompt_statistics(query: SessionQuery, *, by_project: bool = False) -> dict[str, Any]:
    """Aggregate user-message lengths without returning any conversation text."""
    if query.since and query.until and query.since > query.until:
        raise ValueError("--since must not be after --until")
    # A historical conversation may have been ingested today. Prompt date filters
    # therefore apply to record timestamps, never to archive ingestion time.
    summaries = query_session_summaries(
        SessionQuery(agent=query.agent, cwd=query.cwd, identity=query.identity),
        latest_only=True,
    )
    generations = {
        (item.summary.agent, item.summary.lineage_id, item.summary.generation_id): item
        for item in discover_session_generations()
    }
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    excluded = 0
    invalid_timestamps = 0
    for summary in summaries:
        if "invalid" in summary.status:
            excluded += 1
            continue
        generation = generations.get((summary.agent, summary.lineage_id, summary.generation_id))
        if generation is None:
            excluded += 1
            continue
        try:
            # Keep only one conversation in memory, not the entire private corpus.
            records = validate_session_generation(generation.path, generation.manifest)
        except OSError, ValueError:
            excluded += 1
            continue
        key = (summary.agent, summary.cwd if by_project else "")
        row = groups.setdefault(
            key,
            {
                "agent": key[0],
                "project": key[1],
                "sessions": 0,
                "prompts": 0,
                "responses": 0,
                "words": 0,
                "characters": 0,
                "active_days": set(),
                "lengths": [],
                "partial_sessions": 0,
            },
        )
        included = False
        for record in records:
            try:
                timestamp = datetime.fromisoformat(record.ts)
                if timestamp.tzinfo is None:
                    raise ValueError("timestamp requires a timezone")
                timestamp = timestamp.astimezone(UTC)
            except ValueError:
                invalid_timestamps += 1
                if query.since or query.until:
                    continue
                timestamp = None
            if timestamp and ((query.since and timestamp < query.since) or (query.until and timestamp > query.until)):
                continue
            if record.role not in {"user", "assistant"}:
                continue
            included = True
            if record.role == "assistant":
                row["responses"] += 1
                continue
            row["prompts"] += 1
            row["characters"] += len(record.content)
            row["words"] += len(record.content.split())
            row["lengths"].append(len(record.content))
            if timestamp:
                row["active_days"].add(timestamp.date().isoformat())
        if included:
            row["sessions"] += 1
            row["partial_sessions"] += "partial" in summary.status
    rows = []
    for key in sorted(groups):
        row = groups[key]
        lengths = sorted(row.pop("lengths"))
        row["active_days"] = len(row["active_days"])
        row["median_characters"] = median(lengths) if lengths else 0
        row["p95_characters"] = lengths[max(0, (95 * len(lengths) + 99) // 100 - 1)] if lengths else 0
        if row["sessions"]:
            rows.append(row)
    return {
        "schema": "dot.agent.prompts.stats/v2",
        "time_basis": "conversation timestamp (UTC)",
        "unit": "archived user message; may include injected context",
        "complete": excluded == 0
        and not (invalid_timestamps and (query.since or query.until))
        and not any(row["partial_sessions"] for row in rows),
        "excluded_sessions": excluded,
        "invalid_timestamps": invalid_timestamps,
        "prompts": sum(row["prompts"] for row in rows),
        "rows": rows,
    }
