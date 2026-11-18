"""Shared session parser dataclasses, read-only SQLite helper, and counter utilities."""

from __future__ import annotations

import math
import sqlite3
import stat
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fmind_dot.archive.store import SessionLog, format_utc_z, parse_utc_instant
from fmind_dot.archive.usage import UsageRecord


@dataclass(slots=True)
class ParsedSession:
    logs: list[SessionLog]
    fingerprint: str
    source_type: str
    malformed: int = 0
    skipped: int = 0
    usage: UsageRecord | None = None
    usage_error: Exception | None = None
    sidechain: bool = False
    parent_session_id: str = ""


SessionParser = Callable[[Path, str, str], ParsedSession]
SessionCandidate = tuple[str, str, Path]


@dataclass(frozen=True, slots=True)
class AgentAdapter:
    name: str
    label: str
    parser: SessionParser
    enumerate: Callable[[Path], list[SessionCandidate]]
    external_cwd: bool = False
    database: bool = False


@contextmanager
def connect_read_only(path: Path) -> Generator[sqlite3.Connection]:
    resolved = path.resolve()
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError(f"SQLite source is not a regular file: {path}")
    with closing(sqlite3.connect(f"file:{quote(str(resolved))}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        yield conn


def db_mtime(path: Path) -> str:
    resolved = path.resolve()
    mtime_ns = resolved.stat().st_mtime_ns
    with suppress(OSError):
        wal_info = resolved.with_name(f"{resolved.name}-wal").stat()
        # Read-only opens on WAL-mode DBs create an empty 0-byte -wal file; ignore it so read-only scans don't bump mtime.
        if wal_info.st_size > 0:
            mtime_ns = max(mtime_ns, wal_info.st_mtime_ns)
    return format_utc_z(datetime.fromtimestamp(mtime_ns / 1_000_000_000, UTC), seconds=True)


def sqlite_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {str(r[0]) for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def sqlite_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")}


def resolve_cwd(value: str) -> str:
    if not value:
        return ""
    try:
        return str(Path(value).expanduser().resolve(strict=False))
    except RuntimeError:
        raise ValueError("cannot expand a home directory in the project path") from None


def token_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or value < 0
        or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()))
    ):
        raise ValueError(f"usage record field {field!r} must be a non-negative integer")
    return int(value)


def mapping(value: object, field: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"usage record field {field!r} must be an object")
    return value


def apply_counters(
    record: UsageRecord, counters: Mapping[str, object], fields: Mapping[str, str], *, accumulate: bool = False
) -> None:
    for source, target in fields.items():
        if (count := token_int(counters.get(source), target)) is not None:
            setattr(record, target, getattr(record, target) + count if accumulate else count)
            if target in {"input_tokens", "output_tokens", "total_tokens"} or (
                count > 0 and target in {"cached_tokens", "cache_write_tokens"}
            ):
                record.measurement_kind = "provider-reported"


def build_sample(
    harness: str, session_id: str, counters: Mapping[str, object], fields: Mapping[str, str], mtime: str, **init: Any
) -> tuple[UsageRecord, bool]:
    sample = UsageRecord(harness=harness, session_id=session_id, **init)
    apply_counters(sample, counters, fields)
    has_ts = bool(sample.timestamp)
    sample.finalize(fallback_timestamp=mtime)
    return sample, has_ts


def latest_ts(values: Iterable[str]) -> str:
    dated = [(instant, v) for v in values if (instant := parse_utc_instant(v)) is not None]
    return max(dated, key=lambda item: item[0])[1] if dated else ""


def finalize_usage(
    record: UsageRecord, error: Exception | None, logs: Sequence[SessionLog], mtime: str
) -> tuple[UsageRecord | None, Exception | None]:
    if error is not None:
        return None, error
    try:
        return record.finalize(fallback_timestamp=latest_ts(log.ts for log in logs) or mtime), None
    except ValueError as usage_error:
        return None, usage_error


def apply_samples(usage: UsageRecord, samples: Sequence[UsageRecord], *, timed: bool) -> None:
    usage.measurement_kind = "provider-reported"
    usage.set_samples(samples, timed=timed)
    usage.timestamp = latest_ts(s.timestamp for s in samples) if timed else ""


def text_blocks(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        p["text"]
        for p in content
        if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str) and p["text"]
    )
