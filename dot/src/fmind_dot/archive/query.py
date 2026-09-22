"""Validated queries for the normalized session archive."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionLog,
    SessionManifest,
    discover_session_bundles,
    read_session_bundle,
    read_session_manifest,
)

SESSION_EXPORT_SCHEMA = "dot.agent.sessions/v2"
SESSION_STATUSES = ("current", "invalid", "legacy", "partial")
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


@dataclass(frozen=True)
class SessionQuery:
    since: datetime | None = None
    until: datetime | None = None
    agent: str = ""
    cwd: str = ""
    identity: str = ""


@dataclass
class SessionSummary:
    agent: str
    session_id: str
    parser_version: str
    source_type: str
    ingested_at: str
    completeness: str
    record_count: int
    malformed_records: int
    skipped_records: int
    high_water_mark: str = ""
    cwd: str = ""
    records: list[SessionLog] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    path: Path = field(default_factory=Path, repr=False)

    @classmethod
    def from_manifest(cls, path: Path, manifest: SessionManifest) -> SessionSummary:
        return cls(
            agent=manifest.agent,
            session_id=manifest.session_id,
            parser_version=manifest.parser_version,
            source_type=manifest.source_type,
            ingested_at=manifest.ingested_at,
            completeness=manifest.completeness,
            record_count=manifest.record_count,
            malformed_records=manifest.malformed_records,
            skipped_records=manifest.skipped_records,
            high_water_mark=manifest.high_water_mark,
            cwd=manifest.cwd,
            path=path,
        )

    def to_dict(self, *, include_records: bool | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {"agent": self.agent, "session_id": self.session_id}
        if self.cwd:
            result["cwd"] = self.cwd
        result["parser_version"] = self.parser_version
        result["source_type"] = self.source_type
        result["ingested_at"] = self.ingested_at
        if self.high_water_mark:
            result["high_water_mark"] = self.high_water_mark
        result["completeness"] = self.completeness
        if self.records and (include_records if include_records is not None else True):
            result["records"] = [record.to_dict() for record in self.records]
        result.update(
            {
                "status": self.status,
                "record_count": self.record_count,
                "malformed_records": self.malformed_records,
                "skipped_records": self.skipped_records,
            }
        )
        return result


def discover_sessions(root: Path | None = None) -> list[SessionSummary]:
    """Read every manifest; one unreadable bundle fails the whole query rather than hiding a session."""
    return [SessionSummary.from_manifest(path, read_session_manifest(path)) for path in discover_session_bundles(root)]


def _manifest_matches(summary: SessionSummary, query: SessionQuery) -> bool:
    if query.agent and summary.agent != query.agent:
        return False
    if query.identity and query.identity != summary.session_id:
        return False
    if query.since is None and query.until is None:
        return True
    if not _RFC3339.fullmatch(summary.ingested_at):
        return False
    try:
        ingested = datetime.fromisoformat(summary.ingested_at).astimezone(UTC)
    except ValueError:
        return False
    return not (query.since and ingested < query.since) and not (query.until and ingested > query.until)


def query_session_summaries(
    query: SessionQuery | None = None,
    *,
    include_content: bool = False,
    validate_content: bool = False,
    statuses: set[str] | None = None,
    limit: int | None = None,
    root: Path | None = None,
) -> list[SessionSummary]:
    query = query or SessionQuery()
    summaries: list[SessionSummary] = []
    for summary in discover_sessions(root):
        # Discard known nonmatches before reading their transcripts; an absent
        # manifest cwd still needs the content-based fallback below.
        if not _manifest_matches(summary, query) or (query.cwd and summary.cwd and summary.cwd != query.cwd):
            continue
        if include_content or validate_content or (query.cwd and not summary.cwd):
            try:
                _, records = read_session_bundle(summary.path)
            except OSError, ValueError:
                summary.status.append("invalid")
            else:
                if include_content:
                    summary.records = records
                if not summary.cwd:
                    summary.cwd = next((record.cwd for record in records if record.cwd), "")
        if summary.completeness == "partial" or summary.malformed_records:
            summary.status.append("partial")
        if summary.parser_version != SESSION_PARSER_VERSION:
            summary.status.append("legacy")
        if not summary.status:
            summary.status.append("current")
        summary.status.sort()
        if statuses and not statuses.intersection(summary.status):
            continue
        if query.cwd and summary.cwd != query.cwd:
            continue
        summaries.append(summary)
    summaries.sort(key=lambda item: (item.agent, item.session_id))
    summaries.sort(key=lambda item: item.ingested_at, reverse=True)
    return summaries if limit is None else summaries[:limit]


def show_session(query: SessionQuery, *, include_content: bool = False) -> SessionSummary:
    summaries = query_session_summaries(query, include_content=include_content)
    if not summaries:
        raise ValueError("session not found")
    if len(summaries) > 1:
        agents = ", ".join(sorted(summary.agent for summary in summaries))
        raise ValueError(f"session identity is ambiguous across agents {agents}; add --agent")
    return summaries[0]


def export_sessions(
    output: IO[str],
    query: SessionQuery | None = None,
    *,
    format: str = "json",  # noqa: A002 - public CLI contract
    include_content: bool = False,
    redact_content: bool = False,
) -> None:
    if include_content and redact_content:
        raise ValueError("--content and --redact-content are mutually exclusive")
    summaries = query_session_summaries(query, include_content=include_content or redact_content)
    if redact_content:
        for summary in summaries:
            for record in summary.records:
                record.content = "[redacted]"
    if format == "json":
        value = {
            "schema": SESSION_EXPORT_SCHEMA,
            "sessions": [summary.to_dict(include_records=include_content or redact_content) for summary in summaries],
        }
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
        return
    if format == "ndjson":
        for summary in summaries:
            value = {
                "schema": SESSION_EXPORT_SCHEMA,
                "session": summary.to_dict(include_records=include_content or redact_content),
            }
            output.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        return
    raise ValueError(f"unsupported export format {format!r}: expected json or ndjson")


__all__ = [
    "SESSION_EXPORT_SCHEMA",
    "SESSION_STATUSES",
    "SessionQuery",
    "SessionSummary",
    "discover_sessions",
    "export_sessions",
    "query_session_summaries",
    "show_session",
]
