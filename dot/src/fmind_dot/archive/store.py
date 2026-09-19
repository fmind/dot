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
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Literal

from fmind_dot.private_files import private_directory, write_private_file

SESSION_SCHEMA_VERSION = 3
SESSION_PARSER_VERSION = "5"
# Parsers 3 and 4 arrive only through the v2 migration; their usage is flagged as legacy accounting.
READABLE_PARSER_VERSIONS = {"3", "4", SESSION_PARSER_VERSION}
SESSION_STORE_VERSION = "v3"
LEGACY_STORE_VERSION = "v2"
BUNDLE_SUFFIX = ".jsonl"
_COMPONENT = re.compile(r"^[A-Za-z0-9_-]+$")

Completeness = Literal["complete", "partial"]
IngestionStatus = Literal["ingested", "unchanged", "retained", "skipped"]


def is_valid_session_id(value: str) -> bool:
    """Accept only one safe path component: no separators, dots, or traversal."""
    return bool(_COMPONENT.fullmatch(value))


@dataclass
class SessionLog:
    """One source-neutral conversation record."""

    ts: str
    agent: str
    sid: str
    role: str
    content: str
    cwd: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "ts": self.ts,
            "agent": self.agent,
            "sid": self.sid,
            "role": self.role,
            "content": self.content,
        }
        if self.cwd:
            value["cwd"] = self.cwd
        if self.model:
            value["model"] = self.model
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionLog:
        required = ("ts", "agent", "sid", "role", "content")
        if any(not isinstance(value.get(key), str) for key in required):
            raise ValueError("invalid normalized transcript record")
        cwd = value.get("cwd", "")
        model = value.get("model", "")
        if not isinstance(cwd, str) or not isinstance(model, str):
            raise ValueError("invalid normalized transcript record")
        return cls(*(value[key] for key in required), cwd=cwd, model=model)


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

    agent: str
    session_id: str
    parser_version: str
    source_type: str
    source_fingerprint: str
    ingested_at: str
    completeness: Completeness
    record_count: int
    malformed_records: int = 0
    skipped_records: int = 0
    high_water_mark: str = ""
    cwd: str = ""
    source_signature: str = ""
    usage: dict[str, Any] | None = None
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
        try:
            if value.get("schema_version") != SESSION_SCHEMA_VERSION or (
                value.get("parser_version") not in READABLE_PARSER_VERSIONS
            ):
                raise ValueError("unsupported session format; recapture available sources with dot agent session sync")
            completeness = value["completeness"]
            if completeness not in {"complete", "partial"}:
                raise ValueError("invalid manifest field completeness")
            usage = value.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise ValueError("invalid manifest field usage")
            manifest = cls(
                agent=_string(value, "agent"),
                session_id=_string(value, "session_id"),
                parser_version=_string(value, "parser_version"),
                source_type=_string(value, "source_type"),
                source_fingerprint=_string(value, "source_fingerprint"),
                ingested_at=_string(value, "ingested_at"),
                completeness=completeness,
                record_count=_integer(value, "record_count"),
                malformed_records=_integer(value, "malformed_records"),
                skipped_records=_integer(value, "skipped_records"),
                high_water_mark=_string(value, "high_water_mark", required=False),
                cwd=_string(value, "cwd", required=False),
                source_signature=_string(value, "source_signature", required=False),
                usage=usage,
            )
        except (KeyError, TypeError) as error:
            raise ValueError("invalid session manifest") from error
        if not is_valid_session_id(manifest.agent) or not is_valid_session_id(manifest.session_id):
            raise ValueError("invalid session manifest identity")
        return manifest


@dataclass
class SessionIngestionResult:
    status: IngestionStatus
    manifest: SessionManifest


def _string(value: dict[str, Any], key: str, *, required: bool = True) -> str:
    item = value.get(key, "")
    if not isinstance(item, str) or (required and not item):
        raise ValueError(f"invalid manifest field {key}")
    return item


def _integer(value: dict[str, Any], key: str) -> int:
    item = value[key]
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"invalid manifest field {key}")
    return item


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
            if (stored.parser_version, stored.source_fingerprint, stored.usage) == (
                manifest.parser_version,
                manifest.source_fingerprint,
                manifest.usage,
            ):
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


# --- v2 migration -------------------------------------------------------------------------------------------------


@dataclass
class _LegacyGeneration:
    path: Path
    manifest: dict[str, Any]

    @property
    def order(self) -> tuple[int, str]:
        return self.manifest["record_count"], self.manifest["ingested_at"]

    @property
    def usage_order(self) -> tuple[int, str]:
        return int(self.manifest["parser_version"]), self.manifest["ingested_at"]


def _legacy_generations(legacy: Path) -> tuple[dict[tuple[str, str], list[_LegacyGeneration]], int]:
    sessions: dict[tuple[str, str], list[_LegacyGeneration]] = {}
    skipped = 0
    for path in sorted(legacy.glob("*/*/*/manifest.json")):
        try:
            value = json.loads(path.read_bytes())
            if (
                not isinstance(value, dict)
                or value.get("schema_version") != 2
                or value.get("parser_version") not in READABLE_PARSER_VERSIONS
                or value.get("agent") != path.parent.parent.parent.name
                or not is_valid_session_id(str(value.get("session_id")))
            ):
                raise ValueError("unsupported legacy manifest")
            _integer(value, "record_count")
            _string(value, "ingested_at")
        except OSError, ValueError, TypeError, KeyError:
            skipped += 1
            continue
        sessions.setdefault((value["agent"], value["session_id"]), []).append(_LegacyGeneration(path.parent, value))
    return sessions, skipped


def _legacy_usage(generation: _LegacyGeneration) -> dict[str, Any] | None:
    # Load the boundary model on demand to avoid a store/model import cycle.
    from fmind_dot.archive.usage import UsageRecord

    content = (generation.path / "usage.json").read_bytes()
    if fingerprint_bytes(content) != generation.manifest.get("usage_sha256"):
        raise ValueError("legacy usage fingerprint mismatch")
    value = json.loads(content)
    record = value.get("record") if isinstance(value, dict) else None
    if not isinstance(record, dict) or value.get("status") != "available":
        return None
    UsageRecord.from_dict(record)
    return record


def _legacy_bundle(generation: _LegacyGeneration) -> tuple[SessionManifest, list[SessionLog]]:
    value = generation.manifest
    transcript = (generation.path / "transcript.jsonl").read_bytes()
    if fingerprint_bytes(transcript) != value.get("transcript_sha256"):
        raise ValueError("legacy transcript fingerprint mismatch")
    manifest = SessionManifest.from_dict(
        {
            **value,
            "schema_version": SESSION_SCHEMA_VERSION,
            "source_signature": "",
            "malformed_records": value.get("malformed_records", 0),
            "skipped_records": value.get("skipped_records", 0),
            "usage": _legacy_usage(generation),
        }
    )
    lines = [line for line in transcript.split(b"\n") if line.strip()]
    return manifest, _parse_records(lines, manifest, generation.path / "transcript.jsonl")


def _migrate_session(root: Path, generations: list[_LegacyGeneration]) -> bool:
    """Keep the generation with the most records (then newest), carrying the best available usage."""
    for candidate in sorted(generations, key=lambda item: item.order, reverse=True):
        try:
            manifest, logs = _legacy_bundle(candidate)
        except OSError, ValueError, TypeError, KeyError:
            continue
        if manifest.usage is None:
            # A failed extraction archived no usage: the newest earlier measurement still counts.
            for other in sorted(generations, key=lambda item: item.usage_order, reverse=True):
                try:
                    usage = _legacy_usage(other)
                except OSError, ValueError, TypeError, KeyError:
                    continue
                if usage is not None:
                    manifest.usage = usage
                    break
        _write_bundle(root, manifest, logs)
        return True
    return False


def migrate_legacy_store(sessions: Path) -> tuple[int, int] | None:
    """Build v3 from v2 in a staging directory, then publish it with one rename; v2 is never modified."""
    target = sessions / SESSION_STORE_VERSION
    legacy = sessions / LEGACY_STORE_VERSION
    if target.exists() or not legacy.is_dir():
        return None
    staging = Path(tempfile.mkdtemp(prefix=f".{SESSION_STORE_VERSION}-migration-", dir=sessions))
    try:
        generations, skipped = _legacy_generations(legacy)
        migrated = 0
        for key in sorted(generations):
            if _migrate_session(staging, generations[key]):
                migrated += 1
            else:
                skipped += len(generations[key])
        try:
            staging.rename(target)
        except OSError:
            if target.exists():
                # A concurrent process published the same migration first.
                return None
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return migrated, skipped


def ensure_session_store(report: IO[str] | None = None) -> Path:
    """Return the active store root, migrating the v2 store on first access."""
    root = session_store_root()
    if not root.exists():
        result = migrate_legacy_store(root.parent)
        if result is not None and report is not None:
            migrated, skipped = result
            report.write(
                f"agent-session: migrated {migrated} sessions from sessions/{LEGACY_STORE_VERSION} to "
                f"sessions/{SESSION_STORE_VERSION} ({skipped} unreadable generations skipped); "
                f"sessions/{LEGACY_STORE_VERSION} is unchanged and can be removed after verification\n"
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
    "migrate_legacy_store",
    "propagate_models",
    "read_session_bundle",
    "read_session_manifest",
    "report_ingestion",
    "session_bundle_path",
    "session_high_water",
    "session_store_root",
]
