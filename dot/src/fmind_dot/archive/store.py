"""Latest normalized transcript and usage for each agent session.

Each session is one owner-only JSONL bundle, ``sessions/v3/<agent>/<session_id>.jsonl``: its first
line is the manifest (provenance, counts, and usage), and each following line is one normalized
record. Publication replaces the whole file atomically, so transcript and usage never diverge.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, StrictStr, TypeAdapter, ValidationError

from fmind_dot.errors import DotError
from fmind_dot.private_files import private_directory, write_private_file

SESSION_SCHEMA_VERSION = 3
SESSION_PARSER_VERSION = "5"
# Parsers 3 and 4 remain in stores migrated from v2; their usage is flagged as legacy accounting.
READABLE_PARSER_VERSIONS = ("3", "4", SESSION_PARSER_VERSION)
SESSION_STORE_VERSION = "v3"
LEGACY_STORE_VERSION = "v2"
_LAST_MIGRATING_RELEASE = "7.0.4"
BUNDLE_SUFFIX = ".jsonl"
_COMPONENT = re.compile(r"^[A-Za-z0-9_-]+$")

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
NonEmptyStr = Annotated[str, Field(strict=True, min_length=1)]

Completeness = Literal["complete", "partial"]
IngestionStatus = Literal["ingested", "unchanged", "retained", "skipped"]


def is_valid_session_id(value: str) -> bool:
    """Accept only one safe path component: no separators, dots, or traversal."""
    return bool(_COMPONENT.fullmatch(value))


@dataclass
class SessionLog:
    """One source-neutral conversation record."""

    ts: StrictStr
    agent: StrictStr
    sid: StrictStr
    role: StrictStr
    content: StrictStr
    cwd: StrictStr = ""
    model: StrictStr = ""

    def to_dict(self) -> dict[str, Any]:
        return _LOG_ADAPTER.dump_python(self, exclude_defaults=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionLog:
        try:
            return _LOG_ADAPTER.validate_python(value)
        except ValidationError:
            raise ValueError("invalid normalized transcript record") from None


_LOG_ADAPTER = TypeAdapter(SessionLog)


@dataclass
class SessionSource:
    """Evidence retained about the raw source of one capture."""

    type: str = ""
    fingerprint: str = ""
    # Cheap stat evidence (sizes and modification times) that lets sync skip an unchanged source.
    signature: str = ""
    malformed: int = 0
    skipped: int = 0


@dataclass
class SessionManifest:
    """Provenance, counts, and usage for the stored copy of one session."""

    agent: NonEmptyStr
    session_id: NonEmptyStr
    parser_version: NonEmptyStr
    source_type: NonEmptyStr
    source_fingerprint: NonEmptyStr
    ingested_at: NonEmptyStr
    completeness: Completeness
    record_count: NonNegativeInt
    malformed_records: NonNegativeInt = 0
    skipped_records: NonNegativeInt = 0
    high_water_mark: StrictStr = ""
    cwd: StrictStr = ""
    source_signature: StrictStr = ""
    usage: Annotated[dict[str, Any], Field(strict=True)] | None = None
    schema_version: int = SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "agent": self.agent,
            "session_id": self.session_id,
            "parser_version": self.parser_version,
            "source_type": self.source_type,
            "source_fingerprint": self.source_fingerprint,
            "source_signature": self.source_signature,
            "ingested_at": self.ingested_at,
            "high_water_mark": self.high_water_mark,
            "cwd": self.cwd,
            "completeness": self.completeness,
            "record_count": self.record_count,
            "malformed_records": self.malformed_records,
            "skipped_records": self.skipped_records,
            "usage": self.usage,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionManifest:
        if (
            value.get("schema_version") != SESSION_SCHEMA_VERSION
            or value.get("parser_version") not in READABLE_PARSER_VERSIONS
        ):
            raise ValueError("unsupported session format; recapture available sources with dot agent session sync")
        # Constructor defaults support new captures; all three counters are required on disk.
        if not {"record_count", "malformed_records", "skipped_records"} <= value.keys():
            raise ValueError("invalid session manifest")
        try:
            manifest = _MANIFEST_ADAPTER.validate_python(value)
        except ValidationError as error:
            field = error.errors(include_input=False, include_context=False, include_url=False)[0]["loc"][0]
            raise ValueError(f"invalid manifest field {field}") from None
        if not is_valid_session_id(manifest.agent) or not is_valid_session_id(manifest.session_id):
            raise ValueError("invalid session manifest identity")
        return manifest


_MANIFEST_ADAPTER = TypeAdapter(SessionManifest)


@dataclass
class SessionIngestionResult:
    status: IngestionStatus
    manifest: SessionManifest


def fingerprint_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fingerprint_json(value: object) -> str:
    """Fingerprint structured source data with canonical native JSON."""
    return fingerprint_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    )


def _json_line(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()


def marshal_session_logs(logs: list[SessionLog]) -> bytes:
    return b"".join(_json_line(log.to_dict()) for log in logs)


def fingerprint_logs(logs: list[SessionLog]) -> str:
    return fingerprint_bytes(marshal_session_logs(logs))


def session_high_water(logs: list[SessionLog]) -> str:
    return max((log.ts for log in logs), default="")


def propagate_models(logs: list[SessionLog]) -> None:
    """Fill records without a model from the nearest earlier, then later, model."""
    for ordered in (logs, reversed(logs)):
        active = ""
        for log in ordered:
            if log.model:
                active = log.model
            elif active:
                log.model = active


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def session_store_root() -> Path:
    return Path.home() / ".agents" / "sessions" / SESSION_STORE_VERSION


def session_bundle_path(agent: str, session_id: str, root: Path | None = None) -> Path:
    if not is_valid_session_id(agent):
        raise ValueError(f"invalid agent format: {agent!r}")
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid session_id format: {session_id!r}")
    return (root or session_store_root()) / agent / f"{session_id}{BUNDLE_SUFFIX}"


def _parse_manifest(header: bytes, path: Path) -> SessionManifest:
    try:
        value = json.loads(header)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid session manifest in {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"invalid session manifest in {path}")
    try:
        manifest = SessionManifest.from_dict(value)
    except ValueError as error:
        raise ValueError(f"{error}: {path}") from error
    if manifest.agent != path.parent.name or f"{manifest.session_id}{BUNDLE_SUFFIX}" != path.name:
        raise ValueError(f"session manifest does not match its path: {path}")
    return manifest


def read_session_manifest(path: Path) -> SessionManifest:
    """Read only the first line: metadata and usage queries never decode transcript content."""
    with path.open("rb") as stream:
        return _parse_manifest(stream.readline(), path)


def _parse_records(lines: list[bytes], manifest: SessionManifest, path: Path) -> list[SessionLog]:
    logs: list[SessionLog] = []
    for number, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError
            log = SessionLog.from_dict(value)
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError(f"invalid normalized transcript record {number} in {path}") from error
        if log.agent != manifest.agent or log.sid != manifest.session_id:
            raise ValueError(f"normalized transcript record {number} does not match its session in {path}")
        logs.append(log)
    if len(logs) != manifest.record_count:
        raise ValueError(
            f"normalized transcript contains {len(logs)} records, expected {manifest.record_count}: {path}"
        )
    return logs


def read_session_bundle(path: Path) -> tuple[SessionManifest, list[SessionLog]]:
    # Records end at LF only: JSON strings may contain Unicode line separators.
    header, *lines = path.read_bytes().split(b"\n")
    manifest = _parse_manifest(header, path)
    return manifest, _parse_records([line for line in lines if line.strip()], manifest, path)


def discover_session_bundles(root: Path | None = None) -> list[Path]:
    """List bundle files; hidden names are temporary files or sync state."""
    root = root or ensure_session_store()
    if not root.is_dir():
        return []
    return sorted(
        path
        for agent in root.iterdir()
        if agent.is_dir() and is_valid_session_id(agent.name)
        for path in agent.iterdir()
        if path.suffix == BUNDLE_SUFFIX and is_valid_session_id(path.stem)
    )


def _bundle_content(manifest: SessionManifest, logs: list[SessionLog]) -> bytes:
    return _json_line(manifest.to_dict()) + marshal_session_logs(logs)


def _write_bundle(root: Path, manifest: SessionManifest, logs: list[SessionLog]) -> None:
    directory = private_directory(private_directory(root) / manifest.agent)
    write_private_file(directory / f"{manifest.session_id}{BUNDLE_SUFFIX}", _bundle_content(manifest, logs))


def ingest_session(
    agent: str,
    session_id: str,
    logs: list[SessionLog],
    source: SessionSource | None = None,
    *,
    usage: dict[str, Any] | None = None,
    preserve_existing: bool = False,
) -> SessionIngestionResult:
    """Keep the latest copy of a session, but never replace it with a shorter transcript."""
    source = source or SessionSource()
    path = session_bundle_path(agent, session_id)
    for number, log in enumerate(logs, start=1):
        if log.agent != agent or log.sid != session_id:
            raise ValueError(f"session record {number} does not match its session")
    propagate_models(logs)
    fingerprint = source.fingerprint or fingerprint_logs(logs)
    manifest = SessionManifest(
        agent=agent,
        session_id=session_id,
        parser_version=SESSION_PARSER_VERSION,
        source_type=source.type or "normalized",
        source_fingerprint=fingerprint,
        source_signature=source.signature,
        ingested_at=_utc_now(),
        high_water_mark=session_high_water(logs),
        cwd=next((log.cwd for log in logs if log.cwd), ""),
        completeness="partial" if source.malformed else "complete",
        record_count=len(logs),
        malformed_records=source.malformed,
        skipped_records=source.skipped,
        usage=usage,
    )
    if not logs and usage is None:
        return SessionIngestionResult("skipped", manifest)
    root = ensure_session_store()
    # Atomic replacement protects readers; the lock also protects the read/compare/write
    # decision against another sync process. Keep the lock inode stable between writers.
    lock = private_directory(root) / ".write.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stored = read_session_manifest(path) if path.exists() else None
        if stored is not None:
            if preserve_existing:
                return SessionIngestionResult("retained", stored)
            if (stored.parser_version, stored.source_fingerprint) == (
                manifest.parser_version,
                manifest.source_fingerprint,
            ) and (stored.usage == manifest.usage or stored.source_type == manifest.source_type == "copilot-db"):
                # Copilot's fingerprint includes usage; whole-database source_bytes
                # can grow for unrelated sessions without changing this measurement.
                # Same content: keep its capture time, refresh only the source signature.
                if stored.source_signature != manifest.source_signature:
                    manifest.ingested_at = stored.ingested_at
                    _write_bundle(root, manifest, logs)
                return SessionIngestionResult("unchanged", stored)
            if len(logs) < stored.record_count:
                # A truncated or rotated source must not shrink the archived conversation.
                return SessionIngestionResult("retained", stored)
        _write_bundle(root, manifest, logs)
        return SessionIngestionResult("ingested", manifest)


def report_ingestion(result: SessionIngestionResult) -> str:
    manifest = result.manifest
    return (
        f"agent-session: {result.status} {manifest.agent} records={manifest.record_count} "
        f"malformed={manifest.malformed_records} skipped={manifest.skipped_records} "
        f"completeness={manifest.completeness}"
    )


def ensure_session_store() -> Path:
    """Return the active store root; a store that only exists in the retired v2 layout fails closed."""
    root = session_store_root()
    if not root.exists() and (root.parent / LEGACY_STORE_VERSION).is_dir():
        # v2 migration shipped through dot 7.0.4; the v2 files are never modified or removed here.
        raise DotError(
            f"session archive ~/.agents/sessions/{LEGACY_STORE_VERSION} predates sessions/{SESSION_STORE_VERSION}; "
            f"migrate it once with dot v{_LAST_MIGRATING_RELEASE} (check out that tag in a separate worktree and "
            f"run 'uv run --frozen --project dot dot agent session list'), then retry"
        )
    return root


__all__ = [
    "SESSION_PARSER_VERSION",
    "SESSION_SCHEMA_VERSION",
    "SESSION_STORE_VERSION",
    "SessionIngestionResult",
    "SessionLog",
    "SessionManifest",
    "SessionSource",
    "discover_session_bundles",
    "ensure_session_store",
    "fingerprint_bytes",
    "fingerprint_json",
    "fingerprint_logs",
    "ingest_session",
    "is_valid_session_id",
    "marshal_session_logs",
    "propagate_models",
    "read_session_bundle",
    "read_session_manifest",
    "report_ingestion",
    "session_bundle_path",
    "session_high_water",
    "session_store_root",
]
