from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from fmind_dot.archive.store import SessionLog, SessionSource, ingest_session
from fmind_dot.archive.usage import (
    CACHE_INCLUSIVE_INPUT_HARNESSES,
    USAGE_EXTRACTOR_VERSION,
    USAGE_SCHEMA_VERSION,
    UsageRecord,
    UsageStats,
    aggregate_usage,
    api_equivalent,
    check_cost,
    iter_usage_records,
    parse_flexible_time,
    write_usage_stats,
)
from fmind_dot.config import ModelPrice, PricingConfig, default_pricing


def _pricing() -> PricingConfig:
    return PricingConfig(
        as_of="2026-11-15",
        basis="test",
        sources=[],
        models={
            "claude-sonnet-4-5": ModelPrice(
                input=3.0, output=15.0, cache_read=0.3, cache_write=3.75, cache_write_1h=6.0
            ),
            "gpt-5": ModelPrice(input=1.25, output=10.0, cache_read=0.125),
            "grok-code": ModelPrice(input=2.0, output=8.0, cache_read=0.5),
        },
    )


def _rec(harness: str = "claude", sid: str = "s1", model: str = "claude-sonnet-4-5", **kw: Any) -> UsageRecord:
    defaults: dict[str, Any] = {
        "timestamp": "2026-11-15T12:00:00Z",
        "harness": harness,
        "agent": harness,
        "session_id": sid,
        "model": model,
        "input_tokens": 100,
        "output_tokens": 50,
        "measurement_kind": "provider-reported",
    }
    return UsageRecord(**(defaults | kw)).finalize()


def test_usage_record_validation_roundtrip_and_check_cost() -> None:
    assert frozenset({"codex", "grok"}) == CACHE_INCLUSIVE_INPUT_HARNESSES
    assert check_cost(None) is None
    for bad in (-1, True, float("inf"), "nope"):
        with pytest.raises(ValueError, match="cost_usd"):
            check_cost(bad)

    grok = _rec("grok", "g1", "grok-code", input_tokens=100, cached_tokens=40, output_tokens=10)
    assert grok.total_tokens == 110
    d = grok.to_dict()
    assert UsageRecord.from_dict(d) == grok

    for mutate, pat in (
        ({"schema_version": "old", "cost_known": False}, "unsupported usage format"),
        ({"timestamp": "bad", "cost_known": False}, "timestamp"),
        ({"cache_write_1h_tokens": 5, "cache_write_tokens": 2, "cost_known": False}, "cache_write_1h_tokens"),
        (
            {"samples": [{"timestamp": "2026-11-15T00:00:00Z", "model": "m", "input_tokens": 1}], "cost_known": False},
            "samples",
        ),
    ):
        with pytest.raises(ValueError, match=pat):
            UsageRecord.from_dict(d | mutate)

    for req in ("input_tokens", "output_tokens", "total_tokens", "schema_version", "extractor_version"):
        truncated = dict(d)
        del truncated[req]
        with pytest.raises(ValueError, match=f"missing {req}"):
            UsageRecord.from_dict(truncated)
    with pytest.raises(ValueError, match="cost_known"):
        UsageRecord.from_dict({"harness": "pi"})
    assert (
        UsageRecord(
            harness="pi",
            agent="pi",
            session_id="s",
            timestamp="2026-11-15T00:00:00Z",
            schema_version=USAGE_SCHEMA_VERSION,
            extractor_version=USAGE_EXTRACTOR_VERSION,
        )
        .finalize()
        .total_tokens
        == 0
    )


def test_parse_flexible_time_and_api_equivalent() -> None:
    now = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
    assert parse_flexible_time("1h30m", now=now) == datetime(2026, 11, 15, 10, 30, tzinfo=UTC)
    assert parse_flexible_time("7d", now=now) == datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
    assert parse_flexible_time("2026-11-15", end_of_day=True).hour == 23
    with pytest.raises(ValueError, match="invalid time"):
        parse_flexible_time("not-time")

    p = _pricing()
    c_rec = _rec(
        "claude",
        model="anthropic/claude-sonnet-4-5-20260101",
        input_tokens=1_000_000,
        output_tokens=0,
        cache_write_tokens=1_000_000,
        cache_write_1h_tokens=500_000,
    )
    assert api_equivalent(c_rec, p) == pytest.approx(3.0 + 1.875 + 3.0)
    assert api_equivalent(
        _rec("opencode", model="openrouter/anthropic/claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0), p
    ) == pytest.approx(3.0)
    assert (
        api_equivalent(
            _rec("opencode", model="openrouter/qwen/qwen3-coder", input_tokens=1_000_000, output_tokens=0), p
        )
        is None
    )
    assert api_equivalent(
        _rec("copilot", model="gpt-5", input_tokens=1_000_000, cached_tokens=1_000_000, output_tokens=0), p
    ) == pytest.approx(1.25 + 0.125)
    assert api_equivalent(
        _rec("grok", model="grok-code-build", input_tokens=1_000_000, cached_tokens=500_000, output_tokens=0), p
    ) == pytest.approx(1.25)
    assert api_equivalent(_rec("codex", model="gpt-5", input_tokens=10, cached_tokens=20, output_tokens=0), p) is None
    assert api_equivalent(_rec("agy", model="gpt-5", measurement_kind="estimated"), p) is None
    assert api_equivalent(_rec("pi", model="unknown"), p) is None
    assert api_equivalent(_rec("claude", model="<synthetic>", input_tokens=0, output_tokens=0), p) == 0.0
    assert api_equivalent(_rec("claude", model="claude-sonnet-4-5", input_tokens=0, output_tokens=0), p) is None
    bundled_cost = api_equivalent(
        _rec("claude", model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0), default_pricing()
    )
    assert bundled_cost is not None
    assert bundled_cost > 0


def test_iter_usage_aggregate_sidechains_and_write_stats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    p_u = _rec("claude", "parent", cwd="/proj", cost_usd=1.0, cost_known=True).to_dict()
    s_u = _rec(
        "claude", "child", timestamp="2026-11-14T10:00:00Z", sidechain=True, parent_session_id="parent"
    ).to_dict()
    ingest_session(
        "claude",
        "parent",
        [SessionLog("2026-11-15T12:00:00Z", "claude", "parent", "user", "hi", "/proj")],
        SessionSource("claude-jsonl", "f1"),
        usage=p_u,
    )
    ingest_session(
        "claude",
        "child",
        [SessionLog("2026-11-14T10:00:00Z", "claude", "child", "user", "sub")],
        SessionSource("claude-jsonl", "f2", sidechain=True, parent_session_id="parent"),
        usage=s_u,
    )

    loaded = list(iter_usage_records(since=datetime(2026, 11, 15, 0, 0, tzinfo=UTC)))
    assert len(loaded) == 2

    bad_bundle = tmp_path / ".agents/sessions/v3/claude/corrupt.jsonl"
    bad_bundle.write_text("{bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid session manifest"):
        list(iter_usage_records())
    bad_bundle.unlink()

    rows = aggregate_usage(loaded, by_model=True, by_project=True, pricing=_pricing())
    assert len(rows) == 1
    assert rows[0].sessions == 1
    assert rows[0].cost_usd == pytest.approx(1.0)
    assert rows[0].cwd == "/proj"

    partial = aggregate_usage(loaded, since=datetime(2026, 11, 15, 0, 0, tzinfo=UTC), pricing=_pricing())
    assert partial[0].cost_known_sessions == 0

    buf = io.StringIO()
    write_usage_stats(buf, [], by_model=False)
    assert "No usage records found" in buf.getvalue()

    buf = io.StringIO()
    write_usage_stats(
        buf,
        [
            UsageStats(
                "claude",
                "claude-sonnet-4-5",
                10,
                5,
                total_tokens=15,
                sessions=1,
                measurement_kind="provider-reported",
                cost_usd=0.2,
                cost_known_sessions=1,
                first_timestamp="2026-11-15T00:00:00Z",
                last_timestamp="2026-11-15T00:00:00Z",
            )
        ],
        by_model=False,
        pricing=_pricing(),
    )
    assert "TOTAL" in buf.getvalue()

    mixed = io.StringIO()
    write_usage_stats(
        mixed,
        [UsageStats("claude", measurement_kind="provider-reported"), UsageStats("agy", measurement_kind="estimated")],
        by_model=False,
    )
    assert "not comparable" in mixed.getvalue()
