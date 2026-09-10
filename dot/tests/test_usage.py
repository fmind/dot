from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive.store import ingest_session
from fmind_dot.archive.usage import (
    UsageRecord,
    UsageStats,
    aggregate_usage,
    list_usage_records,
    load_usage_records,
    parse_flexible_time,
    show_usage_record,
    write_usage_stats,
)
from fmind_dot.cli import app
from fmind_dot.config import default_pricing


def test_usage_record_finalizes_defaults_and_computed_total() -> None:
    record = UsageRecord(
        harness="codex",
        session_id="session",
        input_tokens=1,
        output_tokens=2,
        cached_tokens=3,
        cache_write_tokens=4,
    )

    assert record.finalize() is record
    assert record.agent == "codex"
    assert datetime.fromisoformat(record.timestamp).tzinfo is not None
    assert record.total_tokens == 10


def test_usage_record_serializes_every_explicit_field() -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="worker",
        session_id="session",
        model="gpt",
        cwd="/repo",
        input_tokens=1,
        output_tokens=2,
        cached_tokens=3,
        cache_write_tokens=4,
        reasoning_tokens=5,
        total_tokens=20,
        cost_usd=0.25,
        turn_count=2,
        measurement_kind="provider-reported",
        source_bytes=123,
    )

    assert record.finalize().to_dict() == {
        "timestamp": "2026-09-06T10:00:00Z",
        "harness": "codex",
        "agent": "worker",
        "session_id": "session",
        "model": "gpt",
        "cwd": "/repo",
        "input_tokens": 1,
        "output_tokens": 2,
        "cached_tokens": 3,
        "cache_write_tokens": 4,
        "reasoning_tokens": 5,
        "total_tokens": 20,
        "cost_usd": 0.25,
        "turn_count": 2,
        "schema_version": "dot.agent.usage/v3",
        "extractor_version": "2",
        "cost_known": True,
        "measurement_kind": "provider-reported",
        "source_bytes": 123,
    }


def test_usage_record_rejects_unknown_measurement_kind() -> None:
    with pytest.raises(ValueError, match="measurement_kind"):
        UsageRecord(harness="codex", session_id="session", measurement_kind="magic").finalize()


def test_usage_record_from_dict_rejects_empty_object() -> None:
    with pytest.raises(ValueError, match="missing timestamp in usage record"):
        UsageRecord.from_dict({"schema_version": "dot.agent.usage/v3", "extractor_version": "2", "cost_known": False})


@pytest.mark.parametrize("field", ["timestamp", "harness", "agent", "session_id"])
def test_usage_record_from_dict_requires_complete_identity(field: str) -> None:
    value = {
        "timestamp": "2026-09-06T10:00:00Z",
        "harness": "codex",
        "agent": "codex",
        "session_id": "valid",
        "schema_version": "dot.agent.usage/v3",
        "extractor_version": "2",
        "cost_known": False,
    }
    del value[field]

    with pytest.raises(ValueError, match=f"missing {field} in usage record"):
        UsageRecord.from_dict(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [("input_tokens", -1), ("cost_usd", -0.01), ("cost_usd", float("inf"))],
    ids=["negative-tokens", "negative-cost", "infinite-cost"],
)
def test_usage_rejects_invalid_metrics_before_serialization(
    tmp_path: Path,
    field: str,
    value: int | float,
) -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="codex",
        session_id="invalid",
    )
    setattr(record, field, value)

    with pytest.raises(ValueError, match=field):
        record.to_dict()

    assert not list(tmp_path.rglob("*.json"))


def test_usage_rejects_malformed_timestamp_at_every_boundary(tmp_path: Path) -> None:
    record = UsageRecord(
        timestamp="not-a-time",
        harness="codex",
        agent="codex",
        session_id="invalid",
    )

    with pytest.raises(ValueError, match="timestamp"):
        record.finalize()
    with pytest.raises(ValueError, match="timestamp"):
        record.to_dict()
    with pytest.raises(ValueError, match="timestamp"):
        aggregate_usage([record], since=datetime(2026, 1, 1, tzinfo=UTC))

    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize(
    "timestamp",
    ["NaN", "Infinity", "10000-01-01T00:00:00Z", "0001-01-01T00:00:00+23:59"],
    ids=["nan", "infinity", "unparseable-year", "utc-underflow"],
)
def test_usage_rejects_non_finite_and_out_of_range_timestamps(timestamp: str) -> None:
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        agent="codex",
        session_id="invalid",
    )

    with pytest.raises(ValueError, match="timestamp"):
        record.to_dict()
    with pytest.raises(ValueError, match="timestamp"):
        aggregate_usage([record])


@pytest.mark.parametrize(
    "timestamp",
    ["2026-09-06T10:00:00.123456Z", "2026-09-06T12:00:00+02:00", "2026-09-06T10:00:00"],
    ids=["utc-z", "explicit-offset", "implicit-utc"],
)
def test_usage_preserves_accepted_iso_timestamp_formats(timestamp: str) -> None:
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        agent="codex",
        session_id="valid",
    )

    assert record.to_dict()["timestamp"] == timestamp
    assert aggregate_usage([record], since=datetime(2026, 9, 6, 9, 59, tzinfo=UTC))[0].sessions == 1


def test_aggregate_usage_projects_unknown_model_when_grouping_by_model() -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="codex",
        session_id="session",
    )

    row = aggregate_usage([record], by_model=True)[0]

    assert row.model == "unknown"
    assert row.to_dict()["model"] == "unknown"


def test_aggregate_usage_filters_and_sums_every_metric() -> None:
    records = [
        UsageRecord(
            timestamp="2026-09-06T09:00:00Z",
            harness="codex",
            agent="codex",
            session_id="early",
            model="gpt",
            input_tokens=1,
            total_tokens=1,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:00:00Z",
            harness="codex",
            agent="codex",
            session_id="included",
            model="gpt-mini",
            input_tokens=1,
            output_tokens=2,
            cached_tokens=3,
            cache_write_tokens=4,
            reasoning_tokens=5,
            total_tokens=15,
            cost_usd=0.25,
            turn_count=2,
        ),
        UsageRecord(
            timestamp="2026-09-06T11:00:00Z",
            harness="codex",
            agent="codex",
            session_id="late",
            model="gpt",
            output_tokens=10,
            total_tokens=10,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:15:00Z",
            harness="claude",
            agent="worker",
            session_id="other",
            model="sonnet",
            total_tokens=7,
        ),
    ]

    filtered = aggregate_usage(
        records,
        harness="codex",
        since=datetime(2026, 9, 6, 9, 30, tzinfo=UTC),
        until=datetime(2026, 9, 6, 10, 30, tzinfo=UTC),
        by_model=True,
    )

    assert [row.to_dict() for row in filtered] == [
        {
            "harness": "codex",
            "model": "gpt-mini",
            "input_tokens": 1,
            "output_tokens": 2,
            "cached_tokens": 3,
            "cache_write_tokens": 4,
            "reasoning_tokens": 5,
            "total_tokens": 15,
            "cost_usd": 0.25,
            "sessions": 1,
            "turns": 2,
            "cost_known_sessions": 1,
            "cost_complete": True,
            "measurement_kind": "unknown",
            "cwd": "",
            "time_basis": "whole session at recorded timestamp",
            "api_equivalent_usd": None,
            "priced_sessions": 0,
            "pricing_complete": False,
            "unpriced_reasons": {"measurement is not provider-reported": 1},
            "pricing_as_of": "2026-09-10",
            "pricing_basis": default_pricing().basis,
            "pricing_sources": default_pricing().sources,
        }
    ]

    combined = aggregate_usage(records)
    assert [(row.harness, row.sessions, row.total_tokens) for row in combined] == [
        ("claude", 1, 7),
        ("codex", 3, 26),
    ]
    assert aggregate_usage(records, harness="worker")[0].harness == "claude"


def test_list_usage_records_filters_sorts_and_applies_limit() -> None:
    records = [
        UsageRecord(timestamp="2026-09-06T09:00:00Z", harness="codex", agent="codex", session_id="old"),
        UsageRecord(timestamp="2026-09-06T11:00:00Z", harness="codex", agent="worker", session_id="new"),
        UsageRecord(timestamp="2026-09-06T10:00:00Z", harness="claude", agent="claude", session_id="other"),
    ]

    assert [record.session_id for record in list_usage_records(records, harness="codex", limit=1)] == ["new"]
    assert [record.session_id for record in list_usage_records(records, harness="worker", limit=0)] == ["new"]
    assert [record.session_id for record in list_usage_records(records, limit=-1)] == ["new", "other", "old"]


def test_write_usage_stats_renders_json_empty_and_text_contracts() -> None:
    rows = [
        UsageStats(
            harness="claude",
            model="sonnet",
            input_tokens=1000,
            output_tokens=2,
            cached_tokens=3,
            cache_write_tokens=4,
            reasoning_tokens=5,
            total_tokens=1014,
            cost_usd=0.5,
            cost_known_sessions=1,
            sessions=1,
            turns=2,
        ),
        UsageStats(
            harness="codex",
            model="gpt",
            input_tokens=1,
            output_tokens=2,
            reasoning_tokens=1,
            total_tokens=4,
            cost_usd=0.125,
            cost_known_sessions=2,
            sessions=2,
            turns=3,
        ),
    ]

    output = StringIO()
    write_usage_stats(output, rows, as_json=True, by_model=True)
    document = json.loads(output.getvalue())
    assert [row["model"] for row in document] == ["sonnet", "gpt"]
    assert document[0]["cache_write_tokens"] == 4

    output = StringIO()
    write_usage_stats(output, [], as_json=False, by_model=False)
    assert output.getvalue() == ("No usage records found. Run 'dot agent session sync' to archive existing sessions.\n")

    output = StringIO()
    write_usage_stats(output, rows, as_json=False, by_model=True)
    assert output.getvalue().splitlines() == [
        "Whole-session totals filtered by recorded timestamp; not interval billing.",
        "HARNESS\tMEASUREMENT\tPROJECT\tMODEL\tSESSIONS\tTURNS\tINPUT TOKENS\tOUTPUT TOKENS\tCACHED TOKENS\tREASONING\tTOTAL TOKENS\tCOST (USD)\tAPI EQUIV (USD)\tPRICED SESSIONS",
        "claude\tunknown\t-\tsonnet\t1\t2\t1,000\t2\t3\t5\t1,014\t$0.5000\tunknown\t0/1",
        "codex\tunknown\t-\tgpt\t2\t3\t1\t2\t0\t1\t4\t$0.1250\tunknown\t0/2",
        "TOTAL\tunknown\t-\t-\t3\t5\t1,001\t4\t3\t6\t1,018\t$0.6250\tunknown\t0/3",
    ]

    output = StringIO()
    write_usage_stats(output, rows[:1], as_json=False, by_model=False)
    assert output.getvalue().splitlines()[1].startswith("HARNESS\tMEASUREMENT\tPROJECT\tSESSIONS")
    assert output.getvalue().splitlines()[-1].startswith("TOTAL\tunknown\t-\t1\t2")


def test_usage_cli_lists_filters_aggregates_and_shows_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for record in (
        UsageRecord(
            timestamp="2026-09-06T09:00:00Z",
            harness="codex",
            session_id="old",
            model="gpt",
            total_tokens=2,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:00:00Z",
            harness="codex",
            session_id="new",
            model="gpt-mini",
            total_tokens=3,
            cost_usd=0.25,
        ),
    ):
        ingest_session(record.harness, record.session_id, [], usage=record.finalize().to_dict())

    runner = CliRunner()
    listed = runner.invoke(app, ["agent", "usage", "list", "--harness", "codex", "--limit", "1", "--json"])
    stats = runner.invoke(
        app,
        [
            "agent",
            "usage",
            "stats",
            "--since",
            "2026-09-06T09:30:00Z",
            "--until",
            "2026-09-06T10:30:00Z",
            "--by-model",
            "--json",
        ],
    )
    shown = runner.invoke(app, ["agent", "usage", "show", "codex", "new"])

    assert listed.exit_code == 0
    assert [record["session_id"] for record in json.loads(listed.stdout)] == ["new"]
    assert stats.exit_code == 0
    assert [(row["model"], row["total_tokens"]) for row in json.loads(stats.stdout)] == [("gpt-mini", 3)]
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["session_id"] == "new"


def test_parse_flexible_time_supports_durations_days_and_iso_values() -> None:
    now = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)

    assert parse_flexible_time(" 1h30m15s ", now=now) == now - timedelta(hours=1, minutes=30, seconds=15)
    assert parse_flexible_time("7d", now=now) == now - timedelta(days=7)
    assert parse_flexible_time("2026-09-01", now=now) == datetime(2026, 9, 1, tzinfo=UTC)
    assert parse_flexible_time("2026-09-06T14:00:00+02:00", now=now) == now


@pytest.mark.parametrize("value", ["", "0d", "1h-no"])
def test_parse_flexible_time_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="use a duration"):
        parse_flexible_time(value, now=datetime(2026, 9, 6, tzinfo=UTC))


@pytest.mark.parametrize("field", ["timestamp", "harness", "agent", "session_id", "model", "cwd"])
def test_usage_record_rejects_non_string_fields(field: str) -> None:
    value = UsageRecord(harness="codex", session_id="fixture").finalize().to_dict()
    value[field] = 1
    with pytest.raises(ValueError, match=field):
        UsageRecord.from_dict(value)


@pytest.mark.parametrize("cost", ["0.25", float("nan"), -0.25, True, 10**400])
def test_usage_record_rejects_invalid_cost(cost: object) -> None:
    value = UsageRecord(harness="codex", session_id="fixture").finalize().to_dict()
    value["cost_usd"] = cost
    with pytest.raises(ValueError, match="cost_usd"):
        UsageRecord.from_dict(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "dot.agent.usage/v2"),
        ("extractor_version", "1"),
        ("schema_version", None),
        ("extractor_version", None),
    ],
)
def test_usage_record_rejects_unsupported_formats(field: str, value: str | None) -> None:
    document = UsageRecord(harness="codex", session_id="fixture").finalize().to_dict()
    if value is None:
        del document[field]
    else:
        document[field] = value
    with pytest.raises(ValueError, match="unsupported usage format"):
        UsageRecord.from_dict(document)


def test_usage_show_validates_identity_and_reports_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for harness, session in [("", "fixture"), ("codex", "")]:
        with pytest.raises(ValueError, match="usage: dot agent usage show"):
            show_usage_record(harness, session)
    with pytest.raises(ValueError, match="usage record not found"):
        show_usage_record("codex", "missing")
    assert load_usage_records() == []
