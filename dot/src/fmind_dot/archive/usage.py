"""Session usage record validation, API-equivalent pricing, and reporting."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime, timedelta
from typing import IO, Any

from fmind_dot.archive.store import (
    SessionManifest,
    discover_session_bundles,
    is_valid_session_id,
    parse_utc_instant,
    read_session_manifest,
)
from fmind_dot.config import ModelPrice, PricingConfig, default_pricing
from fmind_dot.reporting import write_report_line

_DURATION = re.compile(r"(?P<value>\d+)(?P<unit>h|m|s)")
_CLAUDE_DATE_SUFFIX = re.compile(r"-20\d{6}$")
USAGE_SCHEMA_VERSION = "dot.agent.usage/v3"
USAGE_EXTRACTOR_VERSION = "2"
# Providers whose reported input is the whole prompt, with cache buckets as subsets.
CACHE_INCLUSIVE_INPUT_HARNESSES = frozenset({"codex", "grok"})
_PRICED_HARNESSES = frozenset({"codex", "claude", "copilot", "grok", "pi"})
_VENDOR_PREFIXES = ("anthropic/", "google/", "openai/", "x-ai/")
RETIRED_AGENTS = ("codex", "copilot", "grok", "opencode")
_KINDS = {"", "provider-reported", "estimated", "context-only"}
_STRS = ("timestamp", "harness", "agent", "session_id", "model", "cwd", "parent_session_id")
_TOKENS = (
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "cache_write_1h_tokens",
    "reasoning_tokens",
    "total_tokens",
)
_INTS = (*_TOKENS, "turn_count")
_SAMPLE_KEYS = frozenset({"timestamp", "model", *_INTS})
_REQUIRED = frozenset(
    (*_STRS[:4], "input_tokens", "output_tokens", "total_tokens", "schema_version", "extractor_version")
)
_SUM_FIELDS = (
    "sessions",
    "total_tokens",
    "api_equivalent_usd",
    "measurements",
    "priced_measurements",
    "cost_usd",
    "cost_known_sessions",
)


def _parse_ts(value: object) -> datetime:
    if (parsed := parse_utc_instant(value)) is None:
        raise ValueError("usage record field 'timestamp' must be a valid ISO 8601 timestamp")
    return parsed


def _check_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"usage record field {name!r} must be a non-negative integer")
    return value


def _check_counts(obj: Any, *, extra: tuple[str, ...] = ()) -> None:
    for name in (*_INTS, *extra):
        _check_int(_val(obj, name, 0), name)
    if _val(obj, "cache_write_1h_tokens", 0) > _val(obj, "cache_write_tokens", 0):
        raise ValueError("usage record field 'cache_write_1h_tokens' must not exceed 'cache_write_tokens'")


def check_cost(value: object) -> float | None:
    if value is None:
        return None
    msg = "usage record field 'cost_usd' must be a non-negative finite number"
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(msg)
    try:
        cost = float(value)
    except OverflowError as error:
        raise ValueError(msg) from error
    if cost < 0 or not math.isfinite(cost):
        raise ValueError(msg)
    return cost


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
    cache_write_1h_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    turn_count: int = 0
    schema_version: str = USAGE_SCHEMA_VERSION
    extractor_version: str = USAGE_EXTRACTOR_VERSION
    cost_known: bool = False
    measurement_kind: str = ""
    source_bytes: int = 0
    sidechain: bool = False
    parent_session_id: str = ""
    samples: list[dict[str, Any]] = field(default_factory=list)

    def _validate(self, *, complete: bool = True) -> None:
        if self.schema_version != USAGE_SCHEMA_VERSION or self.extractor_version != USAGE_EXTRACTOR_VERSION:
            raise ValueError("unsupported usage format; recapture available sources with dot stats")
        for name in _STRS:
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"invalid usage record field {name!r}")
        for flag in ("cost_known", "sidechain"):
            if type(getattr(self, flag)) is not bool:
                raise ValueError(f"invalid usage record field {flag!r}")
        if self.measurement_kind not in _KINDS:
            raise ValueError("invalid usage record field 'measurement_kind'")
        _check_counts(self, extra=("source_bytes",))
        if (cost := check_cost(self.cost_usd)) is None:
            raise ValueError("invalid usage record field 'cost_usd'")
        self.cost_usd = cost
        if complete and any(not getattr(self, name) for name in _STRS[:4]):
            missing = next(n for n in _STRS[:4] if not getattr(self, n))
            raise ValueError(f"missing {missing} in usage record")
        if self.timestamp:
            _parse_ts(self.timestamp)
        if self.harness and not is_valid_session_id(self.harness):
            raise ValueError("invalid harness; expected an ASCII name without path separators")
        if not isinstance(self.samples, list):
            raise ValueError("invalid usage samples")
        for sample in self.samples:
            if (
                not isinstance(sample, dict)
                or not _SAMPLE_KEYS.issuperset(sample)
                or not isinstance(sample.get("model", ""), str)
            ):
                raise ValueError("invalid usage samples")
            try:
                _parse_ts(sample.get("timestamp"))
                _check_counts(sample)
            except ValueError as error:
                raise ValueError(f"{error} (samples)") from None
        if self.samples and any(sum(s.get(n, 0) for s in self.samples) != getattr(self, n) for n in _INTS):
            raise ValueError("usage samples do not reconcile with session totals")

    def set_samples(self, samples: list[UsageRecord], *, timed: bool = True) -> None:
        for name in _INTS:
            setattr(self, name, sum(getattr(s, name) for s in samples))
        self.model = ""
        for sample in samples:
            self.observe_model(sample.model)
        self.samples = (
            [{"timestamp": s.timestamp, "model": s.model, **{n: getattr(s, n) for n in _INTS}} for s in samples]
            if timed
            else []
        )

    def observe_model(self, model: str) -> None:
        if model:
            self.model = model if self.model in {"", model} else "mixed"

    def finalize(self, *, fallback_timestamp: str = "") -> UsageRecord:
        self._validate(complete=False)
        self.agent, self.timestamp = self.agent or self.harness, self.timestamp or fallback_timestamp
        if self.total_tokens == 0:
            cache = (
                0 if self.harness in CACHE_INCLUSIVE_INPUT_HARNESSES else self.cached_tokens + self.cache_write_tokens
            )
            self.total_tokens = self.input_tokens + self.output_tokens + cache
        self._validate(complete=True)
        return self

    def to_dict(self) -> dict[str, Any]:
        self._validate(complete=True)
        known = self.cost_known or self.cost_usd > 0
        out = {k: v for k, v in asdict(self).items() if k in _REQUIRED or v}
        return out | {"cost_usd": self.cost_usd if known else None, "cost_known": known}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> UsageRecord:
        if "cost_known" not in value:
            raise ValueError("missing cost_known in usage record")
        if missing := sorted(_REQUIRED - value.keys()):
            raise ValueError(f"missing {missing[0]} in usage record")
        data = {k: v for k, v in value.items() if k in {f.name for f in fields(cls)}}
        if data.get("cost_usd") is None:
            data["cost_usd"] = 0.0
        record = cls(**data)
        record._validate(complete=True)
        return record


def _lookup_rate(model: str, harness: str, pricing: PricingConfig) -> ModelPrice | None:
    if rate := pricing.models.get(model):
        return rate
    bare = next((model.removeprefix(p) for p in _VENDOR_PREFIXES if model.startswith(p)), model)
    if bare != model and (rate := pricing.models.get(bare)):
        return rate
    if harness == "grok" and bare.endswith("-build") and (rate := pricing.models.get(bare[:-6])):
        return rate
    return (
        pricing.models.get(_CLAUDE_DATE_SUFFIX.sub("", bare.replace(".", "-"))) if bare.startswith("claude-") else None
    )


def _val(obj: Any, key: str, default: Any = 0) -> Any:
    return obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)


def api_equivalent(
    record: Any, pricing: PricingConfig, *, harness: str = "", measurement_kind: str = ""
) -> float | None:
    """Apply exact model rates to known accounting conventions only."""
    if (measurement_kind or _val(record, "measurement_kind", "")) != "provider-reported":
        return None
    agent = harness or _val(record, "harness", "")
    if agent not in _PRICED_HARNESSES:
        return None
    inp, out, cached, write, write_1h, _, _total = (int(_val(record, k)) for k in _TOKENS)
    if not (inp or out or cached or write):
        # Absent/unreported breakdowns stay unpriced; Claude local <synthetic> turns are known zero.
        return 0.0 if _val(record, "model", "") == "<synthetic>" else None
    model = str(_val(record, "model", ""))
    if model in {"", "mixed", "unknown"} or (rate := _lookup_rate(model, agent, pricing)) is None:
        return None
    if agent in CACHE_INCLUSIVE_INPUT_HARNESSES:
        inp -= cached + write
        if inp < 0:
            return None
    parts = (
        (inp, rate.input),
        (out, rate.output),
        (cached, rate.cache_read),
        (write - write_1h, rate.cache_write),
        (write_1h, rate.cache_write_1h),
    )
    if any(tokens and price is None for tokens, price in parts):
        return None
    try:
        cost = sum(tokens * price for tokens, price in parts if price is not None) / 1_000_000
    except OverflowError:
        return None
    return cost if math.isfinite(cost) else None


@dataclass
class UsageStats:
    harness: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    cache_write_1h_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    sessions: int = 0
    measurement_kind: str = "unknown"
    cwd: str = ""
    cost_known_sessions: int = 0
    api_equivalent_usd: float = 0.0
    measurements: int = 0
    priced_measurements: int = 0
    first_timestamp: str = ""
    last_timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not self.model:
            data.pop("model")
        for key in ("first_timestamp", "last_timestamp"):
            data[key] = data[key] or None
        return data | {
            "cost_usd": self.cost_usd if self.cost_known_sessions else None,
            "api_equivalent_usd": self.api_equivalent_usd if self.priced_measurements else None,
            "pricing_complete": self.priced_measurements == self.measurements,
        }


def _family(manifest: SessionManifest) -> tuple[str, str]:
    return manifest.agent, (manifest.parent_session_id if manifest.sidechain else "") or manifest.session_id


def _overlaps(manifest: SessionManifest, since: datetime | None, until: datetime | None) -> bool:
    if not (manifest.usage_first_timestamp and manifest.usage_last_timestamp):
        return True
    first, last = _parse_ts(manifest.usage_first_timestamp), _parse_ts(manifest.usage_last_timestamp)
    return not ((since is not None and last < since) or (until is not None and first > until))


def iter_usage_records(*, since: datetime | None = None, until: datetime | None = None) -> Iterator[UsageRecord]:
    paths = discover_session_bundles()
    if since is not None or until is not None:
        headers = [read_session_manifest(path, usage=False) for path in paths]
        active = {_family(manifest) for manifest in headers if _overlaps(manifest, since, until)}
        paths = [path for path, manifest in zip(paths, headers, strict=True) if _family(manifest) in active]
    for path in paths:
        manifest = read_session_manifest(path, usage=True)
        if manifest.usage is None:
            continue
        record = UsageRecord.from_dict(manifest.usage)
        if record.harness != manifest.agent or record.session_id != manifest.session_id:
            raise ValueError(f"session usage does not match its session: {path}")
        record.sidechain, record.parent_session_id = manifest.sidechain, manifest.parent_session_id
        yield record


def parse_flexible_time(value: str, *, now: datetime | None = None, end_of_day: bool = False) -> datetime:
    value, now = value.strip(), now or datetime.now(UTC)
    pos, duration = 0, timedelta()
    while match := _DURATION.match(value, pos):
        duration += timedelta(**{{"h": "hours", "m": "minutes", "s": "seconds"}[match["unit"]]: int(match["value"])})
        pos = match.end()
    if pos == len(value) and duration:
        return now - duration
    if value.endswith("d") and value[:-1].isdigit() and int(value[:-1]) > 0:
        return now - timedelta(days=int(value[:-1]))
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"invalid time {value!r}; use a duration (24h), a day count (7d), or a date (2006-01-02)"
        ) from error
    if end_of_day and re.fullmatch(r"\d{4}-?\d{2}-?\d{2}", value):
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


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
) -> list[UsageStats]:
    rates, items = pricing if pricing is not None else default_pricing(), list(records)
    parents = {(r.harness, r.session_id): (i, r.cwd) for i, r in enumerate(items) if not r.sidechain}
    grouped: dict[tuple[str, str, str, str], UsageStats] = {}
    seen: dict[tuple[str, str, str, str], set[object]] = {}
    costs: dict[object, tuple[float, bool]] = {}
    cost_groups: dict[object, set[tuple[str, str, str, str]]] = {}
    partial: set[object] = set()

    for index, record in enumerate(items):
        if record.sidechain:
            session, project = parents.get(
                (record.harness, record.parent_session_id),
                ((record.harness, record.parent_session_id or record.session_id), record.cwd),
            )
        else:
            session, project = index, record.cwd
            costs[session] = (record.cost_usd, record.cost_known or record.cost_usd > 0)
        if (harness and harness not in {record.harness, record.agent}) or (cwd and project != cwd):
            partial.add(session)
            continue
        selected: set[tuple[str, str, str, str]] = set()
        kind, group = record.measurement_kind or "unknown", project if by_project else ""
        for sample in record.samples or [record]:
            ts = _parse_ts(_val(sample, "timestamp", ""))
            if (since and ts < since) or (until and ts > until):
                partial.add(session)
                continue
            model = (str(_val(sample, "model", "")) or "unknown") if by_model else ""
            key = (record.harness, model, kind, group)
            row = grouped.setdefault(key, UsageStats(record.harness, model, measurement_kind=kind, cwd=group))
            stamp = ts.isoformat()
            row.first_timestamp = min(row.first_timestamp, stamp) if row.first_timestamp else stamp
            row.last_timestamp = max(row.last_timestamp, stamp)
            row.measurements += 1
            eq = api_equivalent(sample, rates, harness=record.harness, measurement_kind=record.measurement_kind)
            if eq is not None:
                row.api_equivalent_usd += eq
                row.priced_measurements += 1
            for name in _TOKENS:
                setattr(row, name, getattr(row, name) + int(_val(sample, name, 0)))
            selected.add(key)
        cost_groups.setdefault(session, set()).update(selected)
        for key in selected:
            seen.setdefault(key, set()).add(session)

    for session, (cost, known) in costs.items():
        if session not in partial and len(keys := cost_groups.get(session, set())) == 1:
            row = grouped[next(iter(keys))]
            row.cost_usd += cost
            row.cost_known_sessions += known
    for key, ids in seen.items():
        grouped[key].sessions = len(ids)
    return [grouped[key] for key in sorted(grouped)]


def _ratio_cost(amount: float, numerator: int, denominator: int) -> str:
    return "unknown" if not numerator else f"${amount:.4f}" + (" (partial)" if numerator < denominator else "")


def write_usage_stats(
    output: IO[str], rows: list[UsageStats], *, by_model: bool, pricing: PricingConfig | None = None
) -> None:
    if not rows:
        output.write("No usage records found. Run 'dot stats' to archive existing sessions.\n")
        return

    def put(text: str = "") -> None:
        write_report_line(output, text)

    first = min((r.first_timestamp for r in rows if r.first_timestamp), default="unknown")
    last = max((r.last_timestamp for r in rows if r.last_timestamp), default="unknown")
    put()
    put("Token usage")
    put(f"Coverage: {first[:10]} to {last[:10]} (archived usage only).")
    put("API equivalent is an estimate in USD, separate from recorded cost.")
    if pricing is not None and pricing.as_of:
        put(f"Rate card: {pricing.as_of} · {pricing.basis}")
    total = UsageStats(harness="TOTAL", first_timestamp=first, last_timestamp=last)

    def write_row(row: UsageStats) -> None:
        api = _ratio_cost(row.api_equivalent_usd, row.priced_measurements, row.measurements)
        rec = _ratio_cost(row.cost_usd, row.cost_known_sessions, row.sessions)
        put()
        put(f"{row.harness} · {row.measurement_kind}")
        if by_model and row.model:
            put(f"  Model: {row.model}")
        if row.cwd:
            put(f"  Project: {row.cwd}")
        put(f"  Sessions: {row.sessions:,} · Total tokens: {row.total_tokens:,}")
        put(f"  API equivalent: {api} · Priced: {row.priced_measurements:,}/{row.measurements:,}")
        put(f"  Recorded cost: {rec}")
        if row.first_timestamp and row.harness != "TOTAL":
            put(f"  Coverage: {row.first_timestamp[:10]} to {row.last_timestamp[:10]}")

    for row in rows:
        write_row(row)
        for k in _SUM_FIELDS:
            setattr(total, k, getattr(total, k) + getattr(row, k))
    if len(kinds := {r.measurement_kind for r in rows}) > 1:
        put("No combined total: measurement kinds are not comparable.")
    elif by_model:
        put("Sessions using multiple models appear in each model row; no combined session total.")
    else:
        total.measurement_kind = next(iter(kinds))
        write_row(total)
