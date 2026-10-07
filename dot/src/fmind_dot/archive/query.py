"""Validated queries for the normalized session archive."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionLog,
    SessionManifest,
    discover_session_bundles,
    read_session_bundle,
    read_session_manifest,
)

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
    sidechain: bool = False
    parent_session_id: str = ""
    records: list[SessionLog] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    path: Path = field(default_factory=Path, repr=False)

    @classmethod
    def from_manifest(cls, path: Path, manifest: SessionManifest) -> SessionSummary:
        # Summary metadata fields share the manifest's names; records, status and path are query state.
        copied = {item.name: getattr(manifest, item.name) for item in fields(cls) if hasattr(manifest, item.name)}
        return cls(**copied, path=path)

    def to_dict(self, *, include_records: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {"agent": self.agent, "session_id": self.session_id}
        if self.cwd:
            result["cwd"] = self.cwd
        if self.sidechain:
            result["sidechain"] = True
            if self.parent_session_id:
                result["parent_session_id"] = self.parent_session_id
        result["parser_version"] = self.parser_version
        result["source_type"] = self.source_type
        result["ingested_at"] = self.ingested_at
        if self.high_water_mark:
            result["high_water_mark"] = self.high_water_mark
        result["completeness"] = self.completeness
        if self.records and include_records:
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


def discover_sessions() -> list[SessionSummary]:
    """Read every manifest; one unreadable bundle fails the whole query rather than hiding a session."""
    return [SessionSummary.from_manifest(path, read_session_manifest(path)) for path in discover_session_bundles()]


def _ingestion_timestamp(value: str) -> datetime | None:
    if not _RFC3339.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError, OverflowError:
        return None


def _manifest_matches(summary: SessionSummary, query: SessionQuery) -> bool:
    if query.agent and summary.agent != query.agent:
        return False
    if query.identity and query.identity != summary.session_id:
        return False
    if query.since is None and query.until is None:
        return True
    ingested = _ingestion_timestamp(summary.ingested_at)
    if ingested is None:
        return False
    return not (query.since and ingested < query.since) and not (query.until and ingested > query.until)


def query_session_summaries(
    query: SessionQuery | None = None,
    *,
    include_content: bool = False,
    validate_content: bool = False,
    statuses: set[str] | None = None,
    limit: int | None = None,
) -> list[SessionSummary]:
    query = query or SessionQuery()
    summaries: list[SessionSummary] = []
    for summary in discover_sessions():
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
    summaries.sort(
        key=lambda item: _ingestion_timestamp(item.ingested_at) or datetime.min.replace(tzinfo=UTC), reverse=True
    )
    return summaries if limit is None else summaries[:limit]


def show_session(query: SessionQuery, *, include_content: bool = False) -> SessionSummary:
    summaries = query_session_summaries(query, include_content=include_content)
    if not summaries:
        raise ValueError("session not found")
    if len(summaries) > 1:
        agents = ", ".join(sorted(summary.agent for summary in summaries))
        raise ValueError(f"session identity is ambiguous across agents {agents}; add --agent")
    return summaries[0]


__all__ = [
    "SESSION_STATUSES",
    "SessionQuery",
    "SessionSummary",
    "discover_sessions",
    "query_session_summaries",
    "show_session",
]
