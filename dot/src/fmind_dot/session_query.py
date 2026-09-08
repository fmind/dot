"""Validated queries for the normalized session archive."""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from pathlib import Path
from typing import IO, Any

from fmind_dot.session_store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SessionLog,
    SessionManifest,
    delete_session_generation,
    read_session_manifest,
    session_digest,
    session_lineage_id,
    session_store_root,
    validate_session_generation,
)

SESSION_EXPORT_SCHEMA = "dot.agent.sessions/v1"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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
    lineage_id: str
    generation_id: str
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
    source_fingerprint: str = field(default="", repr=False)

    def to_dict(self, *, include_records: bool | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "agent": self.agent,
            "session_id": self.session_id,
            "lineage_id": self.lineage_id,
            "generation_id": self.generation_id,
        }
        if self.cwd:
            result["cwd"] = self.cwd
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


@dataclass
class _Generation:
    path: Path
    manifest: SessionManifest
    summary: SessionSummary


@dataclass(frozen=True)
class SessionCompactionResult:
    lineages: int
    generations: int
    retained: int
    removable: int
    removed: int
    reclaimable_bytes: int


def parse_session_date(value: str, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        if _DATE.fullmatch(value):
            day = datetime.strptime(value, "%Y-%m-%d").date()
            return datetime.combine(day, time.max if end_of_day else time.min, tzinfo=UTC)
        if not _RFC3339.fullmatch(value):
            raise ValueError
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("expected RFC3339 or YYYY-MM-DD") from error
    return parsed.astimezone(UTC)


def _require_owner_only(path: Path) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"session store contains a symbolic link: {path}")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError(f"session store path is not owner-only: {path}")


def _walk_private_tree(root: Path, context: str) -> Iterator[tuple[Path, list[str], list[str]]]:
    """Walk a private archive without following or silently skipping entries."""
    try:
        root_metadata = root.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise OSError(f"{context} {root}: {error}") from error
    if stat.S_ISLNK(root_metadata.st_mode):
        raise ValueError(f"session store contains a symbolic link: {root}")
    _require_owner_only(root)

    def fail(error: OSError) -> None:
        raise OSError(f"{context} {root}: {error}") from error

    for current, directories, files in os.walk(root, followlinks=False, onerror=fail):
        current_path = Path(current)
        try:
            _require_owner_only(current_path)
            directories.sort()
            files.sort()
            for name in [*directories, *files]:
                _require_owner_only(current_path / name)
        except OSError as error:
            fail(error)
        yield current_path, directories, files


def discover_session_generations(root: Path | None = None) -> list[_Generation]:
    root = root or session_store_root()
    generations: list[_Generation] = []
    for current_path, _, files in _walk_private_tree(root, "failed to scan session store"):
        if "manifest.json" not in files:
            continue
        generation_path = current_path
        try:
            manifest = read_session_manifest(generation_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"failed to read session manifest {generation_path / 'manifest.json'}: {error}") from error
        generations.append(
            _Generation(
                generation_path,
                manifest,
                SessionSummary(
                    agent=manifest.agent,
                    session_id=manifest.session_id,
                    lineage_id=manifest.lineage_id,
                    generation_id=generation_path.name,
                    source_type=manifest.source_type,
                    ingested_at=manifest.ingested_at,
                    high_water_mark=manifest.high_water_mark,
                    completeness=manifest.completeness,
                    record_count=manifest.record_count,
                    malformed_records=manifest.malformed_records,
                    skipped_records=manifest.skipped_records,
                    cwd=manifest.cwd,
                    source_fingerprint=manifest.source_fingerprint,
                ),
            )
        )
    return generations


def _allocated_bytes(path: Path) -> int:
    return sum(entry.lstat().st_blocks * 512 for entry in (path, *path.iterdir()))


def _validate_compaction_generation(root: Path, generation: _Generation) -> tuple[int, list[SessionLog]]:
    manifest = generation.manifest
    try:
        parts = generation.path.relative_to(root).parts
    except ValueError as error:
        raise ValueError(f"session generation is outside the archive: {generation.path}") from error
    expected_generation = session_digest(manifest.parser_version, manifest.source_fingerprint)
    if (
        len(parts) != 3
        or parts != (manifest.agent, manifest.lineage_id, expected_generation)
        or manifest.lineage_id != session_lineage_id(manifest.agent, manifest.session_id)
    ):
        raise ValueError(f"session generation does not match its immutable identity: {generation.path}")
    records = validate_session_generation(generation.path, manifest)
    entries = {entry.name for entry in generation.path.iterdir()}
    if entries != {"manifest.json", "transcript.jsonl"}:
        raise ValueError(f"session generation contains unexpected entries: {generation.path}")
    return _allocated_bytes(generation.path), records


def _compaction_sort_key(generation: _Generation) -> tuple[bool, int, str, str, str]:
    manifest = generation.manifest
    return (
        manifest.completeness == "complete",
        manifest.record_count,
        manifest.high_water_mark,
        manifest.ingested_at,
        generation.path.name,
    )


def compact_session_generations(
    output: IO[str], *, apply: bool = False, agent: str = "", root: Path | None = None
) -> SessionCompactionResult:
    """Retain the best verified generation per lineage and parser version."""
    root = root or session_store_root()
    generations = [item for item in discover_session_generations(root) if not agent or item.manifest.agent == agent]
    verified = {item.path: _validate_compaction_generation(root, item) for item in generations}
    groups: dict[tuple[str, str, str], list[_Generation]] = {}
    for generation in generations:
        manifest = generation.manifest
        groups.setdefault((manifest.agent, manifest.lineage_id, manifest.parser_version), []).append(generation)

    retained: set[Path] = set()
    for group in groups.values():
        # Unknown schemas remain untouched because their completeness semantics
        # cannot be safely ranked by this implementation.
        if any(item.manifest.schema_version != SESSION_SCHEMA_VERSION for item in group):
            retained.update(item.path for item in group)
            continue
        kept: list[_Generation] = []
        for candidate in sorted(group, key=_compaction_sort_key, reverse=True):
            candidate_records = verified[candidate.path][1]
            covered = any(candidate_records == verified[item.path][1][: len(candidate_records)] for item in kept)
            if not covered:
                # Divergent histories are not superseded merely because another
                # generation has more records or a later timestamp.
                kept.append(candidate)
                retained.add(candidate.path)

    removable = sorted((item for item in generations if item.path not in retained), key=lambda item: str(item.path))
    reclaimable = sum(verified[item.path][0] for item in removable)
    removed = 0
    if apply:
        for item in removable:
            manifest = item.manifest
            delete_session_generation(manifest.agent, manifest.lineage_id, item.path.name, manifest)
            removed += 1
    mode = "apply" if apply else "dry-run"
    output.write(
        f"session-compact: mode={mode} lineages={len(groups)} generations={len(generations)} "
        f"retained={len(retained)} removable={len(removable)} removed={removed} "
        f"reclaimable_bytes={reclaimable}\n"
    )
    return SessionCompactionResult(
        lineages=len(groups),
        generations=len(generations),
        retained=len(retained),
        removable=len(removable),
        removed=removed,
        reclaimable_bytes=reclaimable,
    )


def _manifest_matches(summary: SessionSummary, query: SessionQuery) -> bool:
    if query.agent and summary.agent != query.agent:
        return False
    if query.identity and query.identity not in {summary.session_id, summary.lineage_id, summary.generation_id}:
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
    latest_only: bool = False,
    statuses: set[str] | None = None,
    limit: int | None = None,
    root: Path | None = None,
) -> list[SessionSummary]:
    query = query or SessionQuery()
    if query.since and query.until and query.since > query.until:
        raise ValueError("--since must not be after --until")
    generations = discover_session_generations(root)

    newest: dict[tuple[str, str], tuple[str, str]] = {}
    fingerprints: dict[tuple[str, str, str], int] = {}
    for generation in generations:
        summary = generation.summary
        lineage = (summary.agent, summary.lineage_id)
        candidate = (summary.ingested_at, summary.generation_id)
        if lineage not in newest or candidate[0] > newest[lineage][0]:
            newest[lineage] = candidate
        key = (*lineage, summary.source_fingerprint)
        fingerprints[key] = fingerprints.get(key, 0) + 1

    summaries: list[SessionSummary] = []
    for generation in generations:
        if not _manifest_matches(generation.summary, query):
            continue
        summary = generation.summary
        manifest = generation.manifest
        records: list[SessionLog] = []
        lineage = (summary.agent, summary.lineage_id)
        is_latest = newest[lineage][1] == summary.generation_id
        if manifest.schema_version != SESSION_SCHEMA_VERSION or manifest.parser_version != SESSION_PARSER_VERSION:
            summary.status.append("unsupported")
        elif include_content or validate_content:
            try:
                records = validate_session_generation(generation.path, manifest)
            except OSError, ValueError, json.JSONDecodeError:
                summary.status.append("invalid")
            else:
                if include_content:
                    summary.records = records
                if not summary.cwd:
                    summary.cwd = next((record.cwd for record in records if record.cwd), "")
        if manifest.completeness == "partial" or manifest.malformed_records or manifest.skipped_records:
            summary.status.append("partial")
        if not is_latest:
            summary.status.append("stale")
        if fingerprints[(*lineage, summary.source_fingerprint)] > 1:
            summary.status.append("duplicate")
        if not summary.status:
            summary.status.append("current")
        summary.status.sort()
        if latest_only and not is_latest:
            continue
        if statuses and not statuses.intersection(summary.status):
            continue
        if query.cwd and summary.cwd != query.cwd:
            continue
        summaries.append(summary)
    summaries.sort(key=lambda item: item.lineage_id + item.generation_id)
    summaries.sort(key=lambda item: item.ingested_at, reverse=True)
    return summaries if limit is None else summaries[:limit]


def show_session(query: SessionQuery, *, include_content: bool = False) -> SessionSummary:
    summaries = query_session_summaries(query, include_content=include_content)
    if not summaries:
        raise ValueError("session not found")
    if len(summaries) > 1:
        agents = sorted({summary.agent for summary in summaries})
        if len(agents) > 1:
            raise ValueError(
                f"session identity is ambiguous: {len(summaries)} matches across agents {', '.join(agents)}; "
                "add --agent or use a generation identity"
            )
        generations = [summary.generation_id for summary in summaries]
        sample = ", ".join(generations[:3])
        suffix = f" ({len(generations) - 3} more)" if len(generations) > 3 else ""
        raise ValueError(
            f"session identity is ambiguous: {len(summaries)} generations of this {agents[0]} session; "
            f"pass --session with a generation identity, e.g. {sample}{suffix}"
        )
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
    "SessionCompactionResult",
    "SessionQuery",
    "SessionSummary",
    "compact_session_generations",
    "discover_session_generations",
    "export_sessions",
    "parse_session_date",
    "query_session_summaries",
    "show_session",
]
