"""Normalized per-session token usage records and aggregation."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO, Any

from fmind_dot.session_store import publish_owner_only

_DURATION = re.compile(r"(?P<value>\d+)(?P<unit>h|m|s)")
_USAGE_STRING_FIELDS = ("timestamp", "harness", "agent", "session_id", "model", "cwd")
_USAGE_IDENTITY_FIELDS = ("timestamp", "harness", "agent", "session_id")
_USAGE_INTEGER_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
    "turn_count",
)


def _parse_usage_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            # Keep the existing filter convention for ISO timestamps without an offset.
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError, OSError) as error:
        raise ValueError("usage record field 'timestamp' must be a valid ISO 8601 timestamp") from error


@dataclass
class UsageRecord:
    timestamp: str = ""
    harness: str = ""
    agent: str = ""
    session_id: str = ""
    model: str = ""
    cwd: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    turn_count: int = 0

    def finalize(self) -> UsageRecord:
        self._validate(complete=False)
        if not self.agent:
            self.agent = self.harness
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        if self.total_tokens == 0 and (self.input_tokens or self.output_tokens):
            self.total_tokens = self.input_tokens + self.output_tokens + self.cached_tokens + self.cache_write_tokens
        self._validate(complete=True)
        return self

    def to_dict(self) -> dict[str, Any]:
        self._validate(complete=True)
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "harness": self.harness,
            "agent": self.agent,
            "session_id": self.session_id,
        }
        if self.model:
            result["model"] = self.model
        if self.cwd:
            result["cwd"] = self.cwd
        result["input_tokens"] = self.input_tokens
        result["output_tokens"] = self.output_tokens
        if self.cached_tokens:
            result["cached_tokens"] = self.cached_tokens
        if self.cache_write_tokens:
            result["cache_write_tokens"] = self.cache_write_tokens
        if self.reasoning_tokens:
            result["reasoning_tokens"] = self.reasoning_tokens
        result["total_tokens"] = self.total_tokens
        if self.cost_usd:
            result["cost_usd"] = self.cost_usd
        if self.turn_count:
            result["turn_count"] = self.turn_count
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> UsageRecord:
        fields = cls.__dataclass_fields__
        arguments = {key: value[key] for key in fields if key in value}
        record = cls(**arguments)
        record._validate(complete=True)
        return record

    def _validate(self, *, complete: bool) -> None:
        for name in _USAGE_STRING_FIELDS:
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"usage record field {name!r} must be a string")
        if complete:
            for name in _USAGE_IDENTITY_FIELDS:
                if not getattr(self, name):
                    raise ValueError(f"missing {name} in usage record")
        if self.timestamp:
            _parse_usage_timestamp(self.timestamp)
        if self.harness and sanitize_filename(self.harness) != self.harness:
            raise ValueError(f"invalid harness {self.harness!r}; expected an ASCII name without path separators")
        for name in _USAGE_INTEGER_FIELDS:
            item = getattr(self, name)
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise ValueError(f"usage record field {name!r} must be a non-negative integer")
        cost = self.cost_usd
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise ValueError("usage record field 'cost_usd' must be a non-negative finite number")
        try:
            normalized_cost = float(cost)
        except OverflowError as error:
            raise ValueError("usage record field 'cost_usd' must be a non-negative finite number") from error
        if not math.isfinite(normalized_cost) or normalized_cost < 0:
            raise ValueError("usage record field 'cost_usd' must be a non-negative finite number")
        self.cost_usd = normalized_cost


@dataclass
class UsageStats:
    harness: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    sessions: int = 0
    turns: int = 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"harness": self.harness}
        if self.model:
            result["model"] = self.model
        result.update(
            {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cached_tokens": self.cached_tokens,
                "cache_write_tokens": self.cache_write_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "total_tokens": self.total_tokens,
                "cost_usd": self.cost_usd,
                "sessions": self.sessions,
                "turns": self.turns,
            }
        )
        return result


def usage_root() -> Path:
    return Path.home() / ".agents" / "usages"


def sanitize_filename(value: str) -> str:
    return "".join(
        character if character.isascii() and (character.isalnum() or character in "-_") else "_" for character in value
    )


def _harness_directory(root: Path, harness: str, *, create: bool) -> Path:
    if not harness or sanitize_filename(harness) != harness:
        raise ValueError(f"invalid harness {harness!r}; expected an ASCII name without path separators")
    if root.is_symlink():
        raise ValueError(f"usage root must not be a symbolic link: {root}")
    if root.exists() and not root.is_dir():
        raise ValueError(f"usage root must be a directory: {root}")
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
    elif not root.exists():
        return root / harness
    if not root.is_dir():
        raise ValueError(f"usage root must be a directory: {root}")
    directory = root / harness
    if directory.is_symlink():
        raise ValueError(f"usage harness directory must not be a symbolic link: {directory}")
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    elif directory.exists() and not directory.is_dir():
        raise ValueError(f"usage harness path must be a directory: {directory}")
    return directory


def write_usage_record(record: UsageRecord, *, root: Path | None = None) -> Path:
    if not record.harness:
        raise ValueError("missing harness in usage record")
    if not record.session_id:
        raise ValueError("missing session_id in usage record")
    record.finalize()
    directory = _harness_directory(root or usage_root(), record.harness, create=True)
    target = directory / f"{sanitize_filename(record.session_id)}.json"
    content = (json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n").encode()
    publish_owner_only(target, content)
    return target


def load_usage_records(*, root: Path | None = None) -> list[UsageRecord]:
    root = root or usage_root()
    if root.is_symlink():
        raise ValueError(f"failed to parse usage record {root}: usage root must not be a symbolic link")
    if not root.exists():
        return []
    records: list[UsageRecord] = []
    for path in root.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("usage record must be a JSON object")
            records.append(UsageRecord.from_dict(value))
        except FileNotFoundError:
            continue
        except (TypeError, ValueError) as error:
            raise ValueError(f"failed to parse usage record {path}: {error}") from error
    return records


def parse_flexible_time(value: str, *, now: datetime | None = None) -> datetime:
    value = value.strip()
    now = now or datetime.now(UTC)
    position = 0
    duration = timedelta()
    while match := _DURATION.match(value, position):
        amount = int(match.group("value"))
        unit = match.group("unit")
        if unit == "h":
            duration += timedelta(hours=amount)
        elif unit == "m":
            duration += timedelta(minutes=amount)
        else:
            duration += timedelta(seconds=amount)
        position = match.end()
    if position == len(value) and position > 0:
        return now - duration
    if value.endswith("d") and value[:-1].isdigit() and int(value[:-1]) > 0:
        return now - timedelta(days=int(value[:-1]))
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"invalid time {value!r}; use a duration (24h), a day count (7d), or a date (2006-01-02)"
        ) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def aggregate_usage(
    records: list[UsageRecord],
    *,
    harness: str = "",
    since: datetime | None = None,
    until: datetime | None = None,
    by_model: bool = False,
) -> list[UsageStats]:
    grouped: dict[tuple[str, str], UsageStats] = {}
    for record in records:
        if harness and harness not in {record.harness, record.agent}:
            continue
        timestamp = _parse_usage_timestamp(record.timestamp)
        if since and timestamp < since:
            continue
        if until and timestamp > until:
            continue
        model = (record.model or "unknown") if by_model else ""
        key = (record.harness, model)
        row = grouped.setdefault(key, UsageStats(harness=record.harness, model=model))
        row.sessions += 1
        row.turns += record.turn_count
        row.input_tokens += record.input_tokens
        row.output_tokens += record.output_tokens
        row.cached_tokens += record.cached_tokens
        row.cache_write_tokens += record.cache_write_tokens
        row.reasoning_tokens += record.reasoning_tokens
        row.total_tokens += record.total_tokens
        row.cost_usd += record.cost_usd
    return [grouped[key] for key in sorted(grouped)]


def list_usage_records(records: list[UsageRecord], *, harness: str = "", limit: int = 50) -> list[UsageRecord]:
    filtered = [record for record in records if not harness or harness in {record.harness, record.agent}]
    filtered.sort(key=lambda record: record.timestamp, reverse=True)
    return filtered[:limit] if limit > 0 else filtered


def show_usage_record(harness: str, session_id: str, *, root: Path | None = None) -> bytes:
    if not harness or not session_id:
        raise ValueError("usage: dot agent usage show <harness> <session-id>")
    path = _harness_directory(root or usage_root(), harness, create=False) / f"{sanitize_filename(session_id)}.json"
    if path.is_symlink():
        raise ValueError(f"usage record must not be a symbolic link: {path}")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError(f"usage record not found for {harness} session {session_id}: {error}") from error


def write_usage_stats(output: IO[str], rows: list[UsageStats], *, as_json: bool, by_model: bool) -> None:
    if as_json:
        json.dump([row.to_dict() for row in rows], output, ensure_ascii=False, indent=2)
        output.write("\n")
        return
    if not rows:
        output.write(
            "No usage records found in ~/.agents/usages. Run 'dot agent usage sync' to backfill existing sessions.\n"
        )
        return
    columns = ["HARNESS"]
    if by_model:
        columns.append("MODEL")
    columns.extend(
        [
            "SESSIONS",
            "TURNS",
            "INPUT TOKENS",
            "OUTPUT TOKENS",
            "CACHED TOKENS",
            "REASONING",
            "TOTAL TOKENS",
            "COST (USD)",
        ]
    )
    output.write("\t".join(columns) + "\n")
    total = UsageStats(harness="TOTAL")
    for row in rows:
        total.sessions += row.sessions
        total.turns += row.turns
        total.input_tokens += row.input_tokens
        total.output_tokens += row.output_tokens
        total.cached_tokens += row.cached_tokens
        total.cache_write_tokens += row.cache_write_tokens
        total.reasoning_tokens += row.reasoning_tokens
        total.total_tokens += row.total_tokens
        total.cost_usd += row.cost_usd
        values = [row.harness]
        if by_model:
            values.append(row.model)
        values.extend(
            [
                str(row.sessions),
                str(row.turns),
                f"{row.input_tokens:,}",
                f"{row.output_tokens:,}",
                f"{row.cached_tokens:,}",
                f"{row.reasoning_tokens:,}",
                f"{row.total_tokens:,}",
                f"${row.cost_usd:.4f}",
            ]
        )
        output.write("\t".join(values) + "\n")
    values = ["TOTAL"]
    if by_model:
        values.append("-")
    values.extend(
        [
            str(total.sessions),
            str(total.turns),
            f"{total.input_tokens:,}",
            f"{total.output_tokens:,}",
            f"{total.cached_tokens:,}",
            f"{total.reasoning_tokens:,}",
            f"{total.total_tokens:,}",
            f"${total.cost_usd:.4f}",
        ]
    )
    output.write("\t".join(values) + "\n")


__all__ = [
    "UsageRecord",
    "UsageStats",
    "aggregate_usage",
    "list_usage_records",
    "load_usage_records",
    "parse_flexible_time",
    "sanitize_filename",
    "show_usage_record",
    "usage_root",
    "write_usage_record",
    "write_usage_stats",
]
