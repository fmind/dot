"""Latest normalized transcript and usage for each schema-4 agent session."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fmind_dot.private_files import private_directory, write_private_file

SESSION_SCHEMA_VERSION = 4
READABLE_SCHEMA_VERSIONS = (SESSION_SCHEMA_VERSION,)
SESSION_PARSER_VERSION = "16"
READABLE_PARSER_VERSIONS = tuple(str(v) for v in range(7, 17))
SESSION_STORE_VERSION = "v3"
BUNDLE_SUFFIX = ".jsonl"
_COMPONENT = re.compile(r"^[A-Za-z0-9_-]+$")
Completeness = Literal["complete", "partial"]
IngestionStatus = Literal["ingested", "unchanged", "retained", "skipped"]


def is_valid_session_id(value: str) -> bool:
    """Accept only one safe path component without separators, dots, or traversal."""
    return bool(_COMPONENT.fullmatch(value))


@dataclass(slots=True)
class SessionLog:
    ts: str
    agent: str
    sid: str
    role: str
    content: str
    cwd: str = ""
    model: str = ""
    meta: bool = False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ts": self.ts,
            "agent": self.agent,
            "sid": self.sid,
            "role": self.role,
            "content": self.content,
        }
        return out | {k: v for k, v in (("cwd", self.cwd), ("model", self.model), ("meta", self.meta)) if v}


@dataclass(slots=True)
class SessionSource:
    type: str = ""
    fingerprint: str = ""
    signature: str = ""
    malformed: int = 0
    skipped: int = 0
    sidechain: bool = False
    parent_session_id: str = ""


def _non_empty_str(raw: object) -> str:
    if type(raw) is not str or not raw:
        raise ValueError("invalid session manifest")
    return raw


def _opt_str(value: dict[str, Any], key: str) -> str:
    if key not in value:
        return ""
    if type(raw := value[key]) is not str:
        raise ValueError("invalid session manifest")
    return raw


def _non_neg_int(value: dict[str, Any], key: str, *, required: bool = False) -> int:
    if key not in value:
        if required:
            raise ValueError("invalid session manifest")
        return 0
    if type(raw := value[key]) is not int or raw < 0:
        raise ValueError("invalid session manifest")
    return raw


@dataclass(slots=True)
class SessionManifest:
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
    usage: dict[str, Any] | None = field(default=None, repr=False)
    sidechain: bool = False
    parent_session_id: str = ""
    usage_parser_version: str = ""
    usage_first_timestamp: str = ""
    usage_last_timestamp: str = ""
    schema_version: int = SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "session_id": self.session_id,
            "parser_version": self.parser_version,
            "source_type": self.source_type,
            "source_fingerprint": self.source_fingerprint,
            "ingested_at": self.ingested_at,
            "completeness": self.completeness,
            "record_count": self.record_count,
            "malformed_records": self.malformed_records,
            "skipped_records": self.skipped_records,
            "high_water_mark": self.high_water_mark,
            "cwd": self.cwd,
            "source_signature": self.source_signature,
            "sidechain": self.sidechain,
            "parent_session_id": self.parent_session_id,
            "usage_parser_version": self.usage_parser_version,
            "usage_first_timestamp": self.usage_first_timestamp,
            "usage_last_timestamp": self.usage_last_timestamp,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionManifest:
        if not isinstance(value, dict):
            raise ValueError("invalid session manifest")
        sv, pv, upv = value.get("schema_version"), value.get("parser_version"), value.get("usage_parser_version")
        if (
            type(sv) is not int
            or sv not in READABLE_SCHEMA_VERSIONS
            or type(pv) is not str
            or pv not in READABLE_PARSER_VERSIONS
            or (upv is not None and upv != "" and (type(upv) is not str or upv not in READABLE_PARSER_VERSIONS))
        ):
            bad_pv = upv if upv and sv in READABLE_SCHEMA_VERSIONS and pv in READABLE_PARSER_VERSIONS else pv
            newer = (type(sv) is int and sv > SESSION_SCHEMA_VERSION) or (
                isinstance(bad_pv, str) and bad_pv.isdigit() and int(bad_pv) > int(SESSION_PARSER_VERSION)
            )
            raise ValueError(
                "session format written by a newer dot; install that dot version to read this archive"
                if newer
                else "unsupported session format; recapture available sources with dot stats"
            )
        if "usage" in value:
            raise ValueError("invalid session manifest")
        completeness = value.get("completeness")
        if completeness == "complete":
            parsed_completeness: Completeness = "complete"
        elif completeness == "partial":
            parsed_completeness = "partial"
        else:
            raise ValueError("invalid session manifest")
        sidechain = value.get("sidechain", False)
        if type(sidechain) is not bool:
            raise ValueError("invalid session manifest")
        manifest = cls(
            agent=_non_empty_str(value.get("agent")),
            session_id=_non_empty_str(value.get("session_id")),
            parser_version=_non_empty_str(pv),
            source_type=_non_empty_str(value.get("source_type")),
            source_fingerprint=_non_empty_str(value.get("source_fingerprint")),
            ingested_at=_non_empty_str(value.get("ingested_at")),
            completeness=parsed_completeness,
            record_count=_non_neg_int(value, "record_count", required=True),
            malformed_records=_non_neg_int(value, "malformed_records"),
            skipped_records=_non_neg_int(value, "skipped_records"),
            high_water_mark=_opt_str(value, "high_water_mark"),
            cwd=_opt_str(value, "cwd"),
            source_signature=_opt_str(value, "source_signature"),
            sidechain=sidechain,
            parent_session_id=_opt_str(value, "parent_session_id"),
            usage_parser_version=_opt_str(value, "usage_parser_version"),
            usage_first_timestamp=_opt_str(value, "usage_first_timestamp"),
            usage_last_timestamp=_opt_str(value, "usage_last_timestamp"),
            schema_version=sv,
        )
        if (
            not is_valid_session_id(manifest.agent)
            or not is_valid_session_id(manifest.session_id)
            or (manifest.parent_session_id and not is_valid_session_id(manifest.parent_session_id))
        ):
            raise ValueError("invalid session manifest identity")
        return manifest


@dataclass(slots=True)
class SessionIngestionResult:
    status: IngestionStatus
    manifest: SessionManifest
    current_transcript: bool = False


def fingerprint_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: object, *, sort_keys: bool = False) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=sort_keys, allow_nan=False, separators=(",", ":")).encode()


def fingerprint_json(value: object) -> str:
    return fingerprint_bytes(_json_bytes(value, sort_keys=True))


def propagate_models(logs: list[SessionLog]) -> None:
    """Fill records without a model from the nearest earlier, then later, model."""
    for ordered in (logs, reversed(logs)):
        active = ""
        for log in ordered:
            if log.model:
                active = log.model
            elif active:
                log.model = active


def format_utc_z(value: datetime | None = None, *, seconds: bool = False) -> str:
    instant = datetime.now(UTC) if value is None else value.astimezone(UTC)
    return instant.isoformat(timespec="seconds" if seconds else "auto").replace("+00:00", "Z")


def session_store_root() -> Path:
    return Path.home() / ".agents/sessions" / SESSION_STORE_VERSION


def session_bundle_path(agent: str, session_id: str) -> Path:
    if not is_valid_session_id(agent) or not is_valid_session_id(session_id):
        raise ValueError(f"invalid session target: {agent!r}/{session_id!r}")
    return session_store_root() / agent / f"{session_id}{BUNDLE_SUFFIX}"


def parse_utc_instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    except ValueError, OverflowError, OSError:
        return None


def usage_window(usage: dict[str, Any] | None) -> tuple[str, str]:
    """Return earliest and latest usage instants, or empty strings when any are unknown."""
    if usage is None:
        return "", ""
    samples = usage.get("samples")
    raw = (
        [s.get("timestamp") if isinstance(s, dict) else None for s in samples] if samples else [usage.get("timestamp")]
    )
    instants = [parse_utc_instant(v) for v in raw]
    if not instants or any(i is None for i in instants):
        return "", ""
    known = [i for i in instants if i is not None]
    return min(known).isoformat(), max(known).isoformat()


def _parse_json_object(line: bytes, label: str, path: Path, *, allow_none: bool = False) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"invalid session {label} in {path}: {error}") from error
    if value is None and allow_none:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"invalid session {label} in {path}")
    return value


def read_session_manifest(path: Path, *, usage: bool = True) -> SessionManifest:
    with path.open("rb") as stream:
        if (value := _parse_json_object(stream.readline(), "manifest", path)) is None:
            raise ValueError(f"invalid session manifest in {path}")
        try:
            manifest = SessionManifest.from_dict(value)
        except ValueError as error:
            raise ValueError(f"{error}: {path}") from error
        if manifest.agent != path.parent.name or f"{manifest.session_id}{BUNDLE_SUFFIX}" != path.name:
            raise ValueError(f"session manifest does not match its path: {path}")
        if usage:
            manifest.usage = _parse_json_object(stream.readline(), "usage", path, allow_none=True)
    return manifest


def agent_bundle_paths(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix == BUNDLE_SUFFIX and is_valid_session_id(p.stem))


def discover_session_bundles() -> list[Path]:
    root = session_store_root()
    try:
        mode = root.stat().st_mode
    except FileNotFoundError:
        return []
    if not stat.S_ISDIR(mode):
        raise NotADirectoryError(f"session archive is not a directory: {root}")
    return sorted(
        p
        for agent in root.iterdir()
        if is_valid_session_id(agent.name) and stat.S_ISDIR(agent.stat().st_mode)
        for p in agent_bundle_paths(agent)
    )


def _loses_measurement(previous: dict[str, Any], current: dict[str, Any] | None) -> bool:
    if current is None:
        return True
    prev_cost = bool(previous.get("cost_known") or previous.get("cost_usd"))
    curr_cost = bool(current.get("cost_known") or current.get("cost_usd"))
    return (
        previous.get("measurement_kind") == "provider-reported"
        and current.get("measurement_kind") != "provider-reported"
    ) or (prev_cost and not curr_cost)


@contextmanager
def _write_lock(root: Path) -> Generator[None]:
    fd = os.open(private_directory(root) / ".write.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _write_bundle(root: Path, agent: str, name: str, manifest: SessionManifest, raw_logs: bytes) -> None:
    manifest.usage_first_timestamp, manifest.usage_last_timestamp = usage_window(manifest.usage)
    write_private_file(
        private_directory(root / agent) / name,
        _json_bytes(manifest.to_dict()) + b"\n" + _json_bytes(manifest.usage) + b"\n" + raw_logs,
    )


def ingest_session(
    agent: str,
    session_id: str,
    logs: list[SessionLog],
    source: SessionSource | None = None,
    *,
    usage: dict[str, Any] | None = None,
) -> SessionIngestionResult:
    """Keep the latest copy of a session without replacing it with a shorter transcript or losing usage."""
    source, path = source or SessionSource(), session_bundle_path(agent, session_id)
    for number, log in enumerate(logs, start=1):
        if log.agent != agent or log.sid != session_id:
            raise ValueError(f"session record {number} does not match its session")
    propagate_models(logs)
    raw_logs = b"".join(_json_bytes(log.to_dict()) + b"\n" for log in logs)
    usage_cwd = raw_cwd if isinstance(usage, dict) and isinstance(raw_cwd := usage.get("cwd"), str) else ""
    manifest = SessionManifest(
        agent=agent,
        session_id=session_id,
        parser_version=SESSION_PARSER_VERSION,
        source_type=source.type or "normalized",
        source_fingerprint=source.fingerprint or fingerprint_bytes(raw_logs),
        ingested_at=format_utc_z(),
        completeness="partial" if source.malformed else "complete",
        record_count=len(logs),
        malformed_records=source.malformed,
        skipped_records=source.skipped,
        high_water_mark=max((log.ts for log in logs), default=""),
        cwd=next((log.cwd for log in logs if log.cwd), usage_cwd),
        source_signature=source.signature,
        usage=usage,
        sidechain=source.sidechain,
        parent_session_id=source.parent_session_id,
    )
    if not logs and usage is None and not path.exists():
        return SessionIngestionResult("skipped", manifest)
    root = session_store_root()
    with _write_lock(root):
        try:
            stored = read_session_manifest(path)
        except FileNotFoundError:
            stored = None
        if stored is None and not logs and usage is None:
            return SessionIngestionResult("skipped", manifest)
        retain_usage = False
        if stored is not None:
            same = (
                stored.parser_version == manifest.parser_version
                and stored.source_fingerprint == manifest.source_fingerprint
            )
            retain_usage = stored.usage is not None and _loses_measurement(stored.usage, usage)
            if retain_usage:
                manifest.usage = stored.usage
                manifest.usage_parser_version = stored.usage_parser_version or stored.parser_version
                manifest.cwd = manifest.cwd or stored.cwd
                manifest.source_signature = ""
            elif same and stored.usage == manifest.usage:
                if stored.source_signature != manifest.source_signature:
                    manifest.ingested_at = stored.ingested_at
                    _write_bundle(root, agent, path.name, manifest, raw_logs)
                return SessionIngestionResult("unchanged", stored)
            if len(logs) < stored.record_count:
                return SessionIngestionResult("retained", stored)
            if retain_usage and same and (stored.completeness == "complete" or manifest.completeness != "complete"):
                complete = stored.completeness == manifest.completeness == "complete"
                return SessionIngestionResult("retained", stored, current_transcript=complete)
        _write_bundle(root, agent, path.name, manifest, raw_logs)
        status = "retained" if retain_usage else "ingested"
        return SessionIngestionResult(
            status, manifest, current_transcript=retain_usage and manifest.completeness == "complete"
        )
