"""Normalized per-session token usage records and aggregation."""

from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO, Annotated, Any, Literal, Required, TypedDict
from zoneinfo import ZoneInfo

from pydantic import AfterValidator, Field, StrictBool, StrictStr, TypeAdapter, ValidationError, with_config

from fmind_dot.archive.pricing import CACHE_INCLUSIVE_INPUT_HARNESSES, api_equivalent
from fmind_dot.archive.store import NonNegativeInt, is_valid_session_id
from fmind_dot.config import PricingConfig, SubscriptionConfig, default_pricing
from fmind_dot.reporting import write_report_line

_DURATION = re.compile(r"(?P<value>\d+)(?P<unit>h|m|s)")
USAGE_SCHEMA_VERSION = "dot.agent.usage/v3"
USAGE_EXTRACTOR_VERSION = "2"
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


def _sample_timestamp(value: str) -> str:
    _parse_usage_timestamp(value)
    return value


@with_config(extra="forbid", strict=True)
class UsageSample(TypedDict, total=False):
    """Only request timing, model, and counters may enter compact measurements."""

    timestamp: Required[Annotated[str, AfterValidator(_sample_timestamp)]]
    model: str
    input_tokens: NonNegativeInt
    output_tokens: NonNegativeInt
    cached_tokens: NonNegativeInt
    cache_write_tokens: NonNegativeInt
    reasoning_tokens: NonNegativeInt
    total_tokens: NonNegativeInt
    turn_count: NonNegativeInt


@with_config(revalidate_instances="always")
@dataclass
class UsageRecord:
    timestamp: StrictStr = ""
    harness: StrictStr = ""
    agent: StrictStr = ""
    session_id: StrictStr = ""
    model: StrictStr = ""
    cwd: StrictStr = ""
    input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0
    cached_tokens: NonNegativeInt = 0
    cache_write_tokens: NonNegativeInt = 0
    reasoning_tokens: NonNegativeInt = 0
    total_tokens: NonNegativeInt = 0
    cost_usd: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] = 0.0
    cost_known: StrictBool = False
    turn_count: NonNegativeInt = 0
    schema_version: StrictStr = USAGE_SCHEMA_VERSION
    extractor_version: StrictStr = USAGE_EXTRACTOR_VERSION
    measurement_kind: Literal["", "provider-reported", "estimated", "context-only"] = ""
    source_bytes: NonNegativeInt = 0
    legacy_accounting: StrictBool = False
    # Compact request measurements: timestamp, model, and token counters only.
    samples: Annotated[list[UsageSample], Field(strict=True)] = field(default_factory=list)

    def set_samples(self, samples: list[UsageRecord], *, timed: bool = True) -> None:
        """Reconcile a session to deduplicated request measurements."""
        for name in _USAGE_INTEGER_FIELDS:
            setattr(self, name, sum(getattr(sample, name) for sample in samples))
        self.model = ""
        for sample in samples:
            self.observe_model(sample.model)
        self.samples = (
            [
                {
                    "timestamp": sample.timestamp,
                    "model": sample.model,
                    **{name: getattr(sample, name) for name in _USAGE_INTEGER_FIELDS},
                }
                for sample in samples
            ]
            if timed
            else []
        )

    def observe_model(self, model: str) -> None:
        if model:
            self.model = model if not self.model or self.model == model else "mixed"

    def finalize(self, *, fallback_timestamp: str = "") -> UsageRecord:
        """Complete derived fields; an undated measurement takes the caller's source evidence, never the clock."""
        self._validate(complete=False)
        if not self.agent:
            self.agent = self.harness
        if not self.timestamp:
            # A capture-time stamp would move usage between periods and change on every recapture.
            self.timestamp = fallback_timestamp
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
            if self.harness not in CACHE_INCLUSIVE_INPUT_HARNESSES:
                self.total_tokens += self.cached_tokens + self.cache_write_tokens
        self._validate(complete=True)
        return self

    def to_dict(self) -> dict[str, Any]:
        self._validate(complete=True)
        optional = {
            "model",
            "cwd",
            "cached_tokens",
            "cache_write_tokens",
            "reasoning_tokens",
            "turn_count",
            "measurement_kind",
            "source_bytes",
        }
        result = _USAGE_ADAPTER.dump_python(
            self, exclude={name for name in optional if not getattr(self, name)} | {"legacy_accounting", "samples"}
        )
        result["cost_usd"] = self.cost_usd if self.cost_known or self.cost_usd > 0 else None
        result["cost_known"] = self.cost_known or self.cost_usd > 0
        if self.samples:
            result["samples"] = self.samples
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> UsageRecord:
        arguments = {item.name: value[item.name] for item in fields(cls) if item.name in value}
        if arguments.get("cost_usd") is None:
            arguments.pop("cost_usd", None)
        if (
            value.get("schema_version") != USAGE_SCHEMA_VERSION
            or value.get("extractor_version") != USAGE_EXTRACTOR_VERSION
        ):
            raise ValueError("unsupported usage format; recapture available sources with dot agent session sync")
        if "cost_known" not in value:
            raise ValueError("missing cost_known in usage record")
        record = cls(**arguments)
        record._validate(complete=True)
        return record

    def _validate(self, *, complete: bool) -> None:
        try:
            validated = _USAGE_ADAPTER.validate_python(self)
        except ValidationError as error:
            # Only expose the declared top-level field, never source values or nested keys.
            field = error.errors(include_input=False, include_context=False, include_url=False)[0]["loc"][0]
            if field in {*_USAGE_INTEGER_FIELDS, "source_bytes"}:
                raise ValueError(f"usage record field {field!r} must be a non-negative integer") from None
            raise ValueError(f"invalid usage record field {field!r}") from None
        except OverflowError:
            raise ValueError("usage record field 'cost_usd' must be a non-negative finite number") from None
        self.cost_usd = validated.cost_usd
        if complete:
            for name in _USAGE_IDENTITY_FIELDS:
                if not getattr(self, name):
                    raise ValueError(f"missing {name} in usage record")
        if self.schema_version != USAGE_SCHEMA_VERSION or self.extractor_version != USAGE_EXTRACTOR_VERSION:
            raise ValueError("unsupported usage format")
        if self.timestamp:
            _parse_usage_timestamp(self.timestamp)
        if self.harness and not is_valid_session_id(self.harness):
            raise ValueError("invalid harness; expected an ASCII name without path separators")
        if self.samples and any(
            sum(sample.get(name, 0) for sample in self.samples) != getattr(self, name) for name in _USAGE_INTEGER_FIELDS
        ):
            raise ValueError("usage samples do not reconcile with session totals")


_USAGE_ADAPTER = TypeAdapter(UsageRecord)


def _sample_record(record: UsageRecord, sample: UsageSample) -> UsageRecord:
    return UsageRecord(
        harness=record.harness,
        agent=record.agent or record.harness,
        session_id=record.session_id,
        cwd=record.cwd,
        measurement_kind=record.measurement_kind,
        **sample,
    )


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
    measurement_kind: str = "unknown"
    cwd: str = ""
    cost_known_sessions: int = 0
    api_equivalent_usd: float = 0.0
    priced_sessions: int = 0
    unpriced_reasons: dict[str, int] = field(default_factory=dict)
    pricing_as_of: str = ""
    pricing_basis: str = ""
    pricing_sources: list[str] = field(default_factory=list)
    first_timestamp: str = ""
    last_timestamp: str = ""
    period_start: str = ""
    period_end: str = ""
    subscription_usd: float | None = None
    legacy_accounting_sessions: int = 0
    session_timestamp_sessions: int = 0
    measurements: int = 0
    priced_measurements: int = 0

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
                "cost_usd": self.cost_usd if self.cost_known_sessions else None,
                "cost_known_sessions": self.cost_known_sessions,
                "cost_complete": self.cost_known_sessions == self.sessions,
                "measurement_kind": self.measurement_kind,
                "cwd": self.cwd,
                "time_basis": "request timestamps where available; otherwise whole session at recorded timestamp",
                "first_timestamp": self.first_timestamp or None,
                "last_timestamp": self.last_timestamp or None,
                "period_start": self.period_start or None,
                "period_end": self.period_end or None,
                "subscription_usd": self.subscription_usd,
                "api_value_ratio": self.api_equivalent_usd / self.subscription_usd
                if self.subscription_usd and self.priced_measurements == self.measurements
                else None,
                "session_timestamp_sessions": self.session_timestamp_sessions,
                "legacy_accounting_sessions": self.legacy_accounting_sessions,
                "measurements": self.measurements,
                "priced_measurements": self.priced_measurements,
                "api_equivalent_usd": self.api_equivalent_usd if self.priced_measurements else None,
                "priced_sessions": self.priced_sessions,
                "pricing_complete": self.priced_measurements == self.measurements,
                "unpriced_reasons": self.unpriced_reasons,
                "pricing_as_of": self.pricing_as_of,
                "pricing_basis": self.pricing_basis,
                "pricing_sources": self.pricing_sources,
                "sessions": self.sessions,
                "turns": self.turns,
            }
        )
        return result


def iter_usage_records(*, root: Path | None = None) -> Iterator[UsageRecord]:
    """Yield the usage measured for each archived session."""
    from fmind_dot.archive.store import SESSION_PARSER_VERSION, discover_session_bundles, read_session_manifest

    for path in discover_session_bundles(root):
        manifest = read_session_manifest(path)
        if manifest.usage is None:
            continue
        record = UsageRecord.from_dict(manifest.usage)
        if record.harness != manifest.agent or record.session_id != manifest.session_id:
            raise ValueError(f"session usage does not match its session: {path}")
        record.legacy_accounting = manifest.parser_version != SESSION_PARSER_VERSION
        yield record


def load_usage_records(*, root: Path | None = None) -> list[UsageRecord]:
    return list(iter_usage_records(root=root))


def parse_flexible_time(value: str, *, now: datetime | None = None, end_of_day: bool = False) -> datetime:
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
    if end_of_day and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _period(timestamp: datetime, day: int, zone: ZoneInfo) -> tuple[str, str]:
    local = timestamp.astimezone(zone)

    def boundary(year: int, month: int) -> datetime:
        return datetime(year, month, min(day, monthrange(year, month)[1]), tzinfo=zone)

    start = boundary(local.year, local.month)
    if local < start:
        start = boundary(local.year - (local.month == 1), (local.month - 2) % 12 + 1)
    end = boundary(start.year + (start.month == 12), start.month % 12 + 1)
    return start.isoformat(), end.isoformat()


def aggregate_usage(
    records: Iterable[UsageRecord],
    *,
    harness: str = "",
    since: datetime | None = None,
    until: datetime | None = None,
    by_model: bool = False,
    cwd: str = "",
    by_project: bool = False,
    pricing: PricingConfig | None = None,
    monthly: bool = False,
    billing: bool = False,
    subscriptions: dict[str, SubscriptionConfig] | None = None,
) -> list[UsageStats]:
    if monthly and billing:
        raise ValueError("choose --monthly or --billing, not both")
    pricing = pricing if pricing is not None else default_pricing()
    grouped: dict[tuple[str, str, str, str, str], UsageStats] = {}
    for record in records:
        if (harness and harness not in {record.harness, record.agent}) or (cwd and record.cwd != cwd):
            continue
        subscription = (subscriptions or {}).get(record.harness)
        zone = ZoneInfo(subscription.timezone) if billing and subscription else ZoneInfo("UTC")
        day = subscription.renewal_day if billing and subscription else 1
        selected: dict[tuple[str, str, str, str, str], list[UsageRecord]] = {}
        samples = [_sample_record(record, sample) for sample in record.samples] or [record]
        for sample in samples:
            timestamp = _parse_usage_timestamp(sample.timestamp)
            if (since and timestamp < since) or (until and timestamp > until):
                continue
            if billing and subscription is None:
                raise ValueError(
                    f"configure agent.subscriptions.{record.harness} before using --billing, or filter --harness"
                )
            period_start, period_end = _period(timestamp, day, zone) if monthly or billing else ("", "")
            model = (sample.model or "unknown") if by_model else ""
            kind = record.measurement_kind or "unknown"
            project = record.cwd if by_project else ""
            key = (period_start, record.harness, model, kind, project)
            row = grouped.setdefault(
                key, UsageStats(harness=record.harness, model=model, measurement_kind=kind, cwd=project)
            )
            row.period_start, row.period_end = period_start, period_end
            row.subscription_usd = (
                subscription.monthly_usd if billing and subscription and not by_model and not by_project else None
            )
            row.pricing_as_of, row.pricing_basis, row.pricing_sources = pricing.as_of, pricing.basis, pricing.sources
            stamp = timestamp.isoformat()
            row.first_timestamp = min(row.first_timestamp, stamp) if row.first_timestamp else stamp
            row.last_timestamp = max(row.last_timestamp, stamp)
            selected.setdefault(key, []).append(sample)
            equivalent, reason = api_equivalent(sample, pricing)
            row.measurements += 1
            if equivalent is None:
                row.unpriced_reasons[reason] = row.unpriced_reasons.get(reason, 0) + 1
            else:
                row.api_equivalent_usd += equivalent
                row.priced_measurements += 1
            for name in _USAGE_INTEGER_FIELDS:
                if name != "turn_count":
                    setattr(row, name, getattr(row, name) + getattr(sample, name))
            row.turns += sample.turn_count
        for key, included in selected.items():
            row = grouped[key]
            row.sessions += 1
            row.session_timestamp_sessions += not bool(record.samples)
            row.legacy_accounting_sessions += record.legacy_accounting
            row.priced_sessions += all(api_equivalent(sample, pricing)[0] is not None for sample in included)
            # A provider's session cost cannot be apportioned between dates/models.
            if len(selected) == 1 and len(included) == len(samples):
                row.cost_usd += record.cost_usd
                row.cost_known_sessions += record.cost_known or record.cost_usd > 0
    return [grouped[key] for key in sorted(grouped)]


def list_usage_records(records: list[UsageRecord], *, harness: str = "", limit: int = 50) -> list[UsageRecord]:
    filtered = [record for record in records if not harness or harness in {record.harness, record.agent}]
    filtered.sort(key=lambda record: _parse_usage_timestamp(record.timestamp), reverse=True)
    return filtered[:limit] if limit > 0 else filtered


def show_usage_record(harness: str, session_id: str, *, root: Path | None = None) -> UsageRecord:
    if not harness or not session_id:
        raise ValueError("usage: dot agent usage show <harness> <session-id>")
    for record in iter_usage_records(root=root):
        if record.harness == harness and record.session_id == session_id:
            return record
    raise ValueError(f"usage record not found for {harness} session {session_id}")


def write_usage_stats(output: IO[str], rows: list[UsageStats], *, by_model: bool) -> None:
    if not rows:
        output.write("No usage records found. Run 'dot agent session sync' to archive existing sessions.\n")
        return

    def write(text: str = "") -> None:
        write_report_line(output, text)

    write()
    write("Token usage")
    first = min((row.first_timestamp for row in rows if row.first_timestamp), default="unknown")
    last = max((row.last_timestamp for row in rows if row.last_timestamp), default="unknown")
    write(f"Coverage: {first[:10]} to {last[:10]} (archived usage only).")
    write("API equivalent is an estimate in USD, separate from recorded cost and subscriptions.")
    if rows[0].pricing_as_of:
        write(f"Rate card: {rows[0].pricing_as_of} · {rows[0].pricing_basis}")
    periods = any(row.period_start for row in rows)
    total = UsageStats(harness="TOTAL", first_timestamp=first, last_timestamp=last)

    def write_row(row: UsageStats) -> None:
        write()
        write(f"{row.harness} · {row.measurement_kind}")
        if by_model and row.model:
            write(f"  Model: {row.model}")
        if row.cwd:
            write(f"  Project: {row.cwd}")
        if row.period_start:
            write(f"  Period: {row.period_start[:10]} to {row.period_end[:10]} (end exclusive)")
        write(f"  Sessions: {row.sessions:,} · Total tokens: {row.total_tokens:,}")
        write(
            f"  API equivalent: {_equivalent_display(row)} · Priced: {row.priced_measurements:,}/{row.measurements:,}"
        )
        write(f"  Recorded cost: {_cost_display(row)}")
        if row.first_timestamp and row.harness != "TOTAL":
            write(f"  Coverage: {row.first_timestamp[:10]} to {row.last_timestamp[:10]}")

    for row in rows:
        write_row(row)
        for name in (
            "sessions",
            "total_tokens",
            "api_equivalent_usd",
            "priced_sessions",
            "measurements",
            "priced_measurements",
            "cost_usd",
            "cost_known_sessions",
        ):
            setattr(total, name, getattr(total, name) + getattr(row, name))
    if any(row.legacy_accounting_sessions for row in rows):
        write(
            "Legacy accounting present: recapture available sources with 'dot agent session sync'; old Claude totals may count repeated response blocks."
        )
    if any(row.session_timestamp_sessions for row in rows):
        write("Some usage has only a session timestamp; its monthly allocation is approximate.")
    if periods:
        write("Period ends are exclusive; sessions spanning periods may appear in more than one row.")
        for row in rows:
            if row.subscription_usd:
                ratio = row.to_dict()["api_value_ratio"]
                value = f"{ratio:.2f}x" if ratio is not None else "unknown (partial pricing)"
                write(
                    f"{row.harness} {row.period_start[:10]}: ${row.subscription_usd:.2f}/cycle; API value {value}. Coverage may be partial."
                )
        return
    kinds = {row.measurement_kind for row in rows}
    if len(kinds) > 1:
        write("No combined total: measurement kinds are not comparable.")
        return
    if by_model:
        write("Sessions using multiple models appear in each model row; no combined session total.")
        return
    total.measurement_kind = next(iter(kinds))
    write_row(total)


def _equivalent_display(row: UsageStats) -> str:
    if not row.priced_measurements:
        return "unknown"
    suffix = " (partial)" if row.priced_measurements < row.measurements else ""
    return f"${row.api_equivalent_usd:.4f}{suffix}"


def _cost_display(row: UsageStats) -> str:
    if not row.cost_known_sessions:
        return "unknown"
    suffix = " (partial)" if row.cost_known_sessions < row.sessions else ""
    return f"${row.cost_usd:.4f}{suffix}"


__all__ = [
    "UsageRecord",
    "UsageStats",
    "aggregate_usage",
    "iter_usage_records",
    "list_usage_records",
    "load_usage_records",
    "parse_flexible_time",
    "show_usage_record",
    "write_usage_stats",
]
