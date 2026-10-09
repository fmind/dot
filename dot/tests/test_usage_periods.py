"""Usage reports reconcile request events, immutable history, and billing boundaries."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive.parsers import parse_claude_session, parse_codex_session
from fmind_dot.archive.store import ingest_session
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, load_usage_records, write_usage_stats
from fmind_dot.cli import app
from fmind_dot.config import SubscriptionConfig


def request(timestamp: str, *, model: str = "gpt-5.4", tokens: int = 1_000_000) -> UsageRecord:
    return UsageRecord(
        timestamp=timestamp,
        harness="codex",
        session_id="one",
        model=model,
        measurement_kind="provider-reported",
        input_tokens=tokens,
        turn_count=1,
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")


def session(*samples: UsageRecord) -> UsageRecord:
    record = request(samples[-1].timestamp)
    record.set_samples(list(samples))
    return record.finalize(fallback_timestamp="2026-09-01T00:00:00Z")


def test_monthly_splits_one_session_and_prices_each_model() -> None:
    record = session(request("2026-08-31T23:59:59Z"), request("2026-09-01T00:00:00Z", model="gpt-5.5"))
    rows = aggregate_usage([record], monthly=True)
    assert [(r.period_start[:10], r.total_tokens, r.sessions) for r in rows] == [
        ("2026-08-01", 1_000_000, 1),
        ("2026-09-01", 1_000_000, 1),
    ]
    assert [r.api_equivalent_usd for r in rows] == [2.5, 5]
    assert all(r.to_dict()["pricing_complete"] for r in rows)
    total = aggregate_usage([record])[0]
    assert total.sessions == 1
    assert total.total_tokens == 2_000_000
    assert total.api_equivalent_usd == 7.5
    assert total.first_timestamp == "2026-08-31T23:59:59+00:00"
    assert total.last_timestamp == "2026-09-01T00:00:00+00:00"
    assert len(aggregate_usage([record], by_model=True)) == 2
    assert aggregate_usage([record], since=datetime(2026, 9, 1, tzinfo=UTC))[0].total_tokens == 1_000_000


def test_model_breakdown_does_not_sum_overlapping_sessions() -> None:
    record = session(request("2026-09-01T00:00:00Z"), request("2026-09-01T01:00:00Z", model="gpt-5.5"))
    output = io.StringIO()
    write_usage_stats(output, aggregate_usage([record], by_model=True), by_model=True)
    assert output.getvalue().count("Sessions: 1") == 2
    assert "TOTAL" not in output.getvalue()
    assert "Sessions using multiple models appear in each model row" in output.getvalue()


def test_billing_clamps_month_end_and_respects_timezone_and_dst() -> None:
    record = session(request("2026-02-28T22:59:59Z"), request("2026-03-30T22:00:00Z"))
    subscriptions = {"codex": SubscriptionConfig(renewal_day=31, timezone="Europe/Paris", monthly_usd=20)}
    rows = aggregate_usage([record], billing=True, subscriptions=subscriptions)
    assert [(r.period_start, r.period_end) for r in rows] == [
        ("2026-02-28T00:00:00+01:00", "2026-03-31T00:00:00+02:00"),
        ("2026-03-31T00:00:00+02:00", "2026-04-30T00:00:00+02:00"),
    ]
    assert rows[0].to_dict()["api_value_ratio"] == 0.125
    previous = aggregate_usage([request("2026-02-27T22:00:00Z")], billing=True, subscriptions=subscriptions)[0]
    assert previous.period_start.startswith("2026-01-31")
    with pytest.raises(ValueError, match=r"configure agent\.subscriptions\.codex"):
        aggregate_usage([record], billing=True)
    with pytest.raises(ValueError, match="choose --monthly or --billing"):
        aggregate_usage([record], monthly=True, billing=True)


def test_partial_model_pricing_is_not_free_and_session_cost_cannot_be_split() -> None:
    record = session(request("2026-08-31T23:59:59Z"), request("2026-09-01T00:00:00Z", model="unknown"))
    record.cost_usd, record.cost_known = 12, True
    row = aggregate_usage([record])[0]
    assert row.to_dict()["api_equivalent_usd"] == 2.5
    assert row.priced_sessions == 0
    assert row.priced_measurements == 1
    assert not row.to_dict()["pricing_complete"]
    assert row.to_dict()["cost_usd"] == 12
    assert all(r.to_dict()["cost_usd"] is None for r in aggregate_usage([record], monthly=True))
    output = io.StringIO()
    write_usage_stats(output, [row], by_model=False)
    assert "$2.5000 (partial)" in output.getvalue()


def test_compact_sample_missing_counter_does_not_inherit_session_total() -> None:
    record = session(request("2026-09-01T00:00:00Z"), request("2026-09-02T00:00:00Z", tokens=0))
    del record.samples[1]["input_tokens"]
    restored = UsageRecord.from_dict(record.to_dict())
    assert aggregate_usage([restored])[0].input_tokens == 1_000_000
    record.samples[0]["input_tokens"] = 1
    with pytest.raises(ValueError, match="reconcile"):
        record.to_dict()


def test_claude_streamed_blocks_count_one_request_and_keep_peak_output(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    rows = [
        {
            "timestamp": "2026-08-31T23:59:59Z",
            "type": "assistant",
            "requestId": "request",
            "message": {
                "id": "message",
                "model": "claude-sonnet-4-6",
                "content": [],
                "usage": {"input_tokens": 100, "output_tokens": output, "cache_read_input_tokens": 200},
            },
        }
        for output in [1, 30, 20]
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows))
    parsed = parse_claude_session(path, "one")
    assert parsed.usage_error is None
    assert parsed.usage is not None
    assert (
        parsed.usage.input_tokens,
        parsed.usage.output_tokens,
        parsed.usage.total_tokens,
        parsed.usage.turn_count,
    ) == (100, 30, 330, 1)
    assert len(parsed.usage.samples) == 1


def test_codex_repeated_counters_and_model_switches(tmp_path: Path) -> None:
    rows = []
    for date, model, count in [
        ("2026-08-31", "gpt-5.4", 100),
        ("2026-08-31", "gpt-5.4", 100),
        ("2026-09-01", "gpt-5.5", 300),
    ]:
        rows.extend(
            [
                {"type": "turn_context", "payload": {"model": model}},
                {
                    "type": "event_msg",
                    "timestamp": date + "T23:00:00Z",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": count,
                                "cached_input_tokens": count // 2,
                                "output_tokens": 0,
                                "total_tokens": count,
                            }
                        },
                    },
                },
            ]
        )
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    parsed = parse_codex_session(path, "one")
    assert parsed.usage_error is None
    assert parsed.usage is not None
    assert parsed.usage.total_tokens == 300
    assert len(parsed.usage.samples) == 2
    assert [row.input_tokens for row in aggregate_usage([parsed.usage], monthly=True)] == [100, 200]
    assert [row.model for row in aggregate_usage([parsed.usage], by_model=True)] == ["gpt-5.4", "gpt-5.5"]
    # A corrected/decreasing cumulative count cannot yield trustworthy request deltas.
    rows.append(
        {
            "type": "event_msg",
            "timestamp": "2026-09-02T00:00:00Z",
            "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 50, "total_tokens": 50}}},
        }
    )
    path.write_text("\n".join(json.dumps(row) for row in rows))
    corrected = parse_codex_session(path, "one").usage
    assert corrected is not None
    assert not corrected.samples
    assert corrected.total_tokens == 50


def test_public_monthly_and_subscription_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    record = session(request("2026-08-31T23:00:00Z"), request("2026-09-01T23:00:00Z"))
    ingest_session("codex", "one", [], usage=record.to_dict())
    runner = CliRunner()
    report = runner.invoke(app, ["agent", "stats", "--tokens-only", "--monthly", "--json"])
    assert report.exit_code == 0, report.output
    result = json.loads(report.output)
    assert result["prompts"] is None
    assert len(result["usage"]) == 2
    config = tmp_path / "config.yaml"
    config.write_text(
        "agent:\n  subscriptions:\n    codex:\n      renewal_day: 15\n      timezone: Europe/Paris\n      monthly_usd: 20\n"
    )
    billed = runner.invoke(app, ["--config", str(config), "agent", "stats", "--tokens-only", "--billing", "--json"])
    assert billed.exit_code == 0, billed.output
    assert json.loads(billed.stdout)["usage"][0]["period_start"].startswith("2026-08-15")
    config.write_text("agent:\n  subscriptions:\n    codex:\n      renewal_day: 32\n")
    assert runner.invoke(app, ["--config", str(config), "config", "validate"]).exit_code != 0
    config.write_text("agent:\n  subscriptions:\n    codex:\n      renewal_day: 1\n      timezone: Invalid/Zone\n")
    assert runner.invoke(app, ["--config", str(config), "config", "validate"]).exit_code != 0


def test_usage_query_rejects_invalid_usage_and_mismatched_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fmind_dot.archive import store

    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "one", [], usage=request("2026-09-01T00:00:00Z").to_dict())
    assert len(load_usage_records()) == 1
    path = store.session_bundle_path("codex", "one")
    manifest = json.loads(path.read_text())
    path.write_text(json.dumps(manifest | {"usage": manifest["usage"] | {"input_tokens": -1}}) + "\n")
    with pytest.raises(ValueError, match="non-negative integer"):
        load_usage_records()
    path.write_text(json.dumps(manifest | {"usage": manifest["usage"] | {"session_id": "two"}}) + "\n")
    with pytest.raises(ValueError, match="does not match its session"):
        load_usage_records()


@pytest.mark.parametrize(("parser", "legacy"), [("9", False), ("3", True)], ids=["older", "legacy"])
def test_recapture_replaces_older_parser_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parser: str, legacy: bool
) -> None:
    from fmind_dot.archive import store

    monkeypatch.setenv("HOME", str(tmp_path))
    original = request("2026-09-01T00:00:00Z", tokens=200)
    source = store.SessionSource(type="fixture", fingerprint=store.fingerprint_bytes(b"same source"))
    with monkeypatch.context() as previous:
        previous.setattr(store, "SESSION_PARSER_VERSION", parser)
        ingest_session("codex", "one", [], source, usage=original.to_dict())
    assert load_usage_records()[0].legacy_accounting is legacy
    corrected = session(request("2026-09-01T00:00:00Z", tokens=100))
    ingest_session("codex", "one", [], source, usage=corrected.to_dict())
    records = load_usage_records()
    assert len(records) == 1
    assert records[0].total_tokens == 100
    assert not records[0].legacy_accounting
    assert [path.name for path in store.discover_session_bundles()] == ["one.jsonl"]


_CODEX_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


def _codex_usage(input_tokens: int, *, cached: int = 0, output: int = 0) -> dict[str, int]:
    return dict(zip(_CODEX_FIELDS, (input_tokens, cached, 0, output, 0, input_tokens + output), strict=True))


def _codex_sum(*usages: dict[str, int]) -> dict[str, int]:
    return {field: sum(usage[field] for usage in usages) for field in _CODEX_FIELDS}


def _codex_record(timestamp: str, response: str, usage: dict[str, int], thread: dict[str, int]) -> dict:
    payload = {"response_id": response, "usage": usage, "turn_token_usage": usage, "thread_token_usage": thread}
    return {"timestamp": timestamp, "type": "token_usage_record", "payload": payload}


def test_codex_response_records_include_compaction_requests(tmp_path: Path) -> None:
    first = _codex_usage(100, cached=40, output=10)
    compaction = _codex_usage(300, output=50)
    second = _codex_usage(200, cached=150, output=20)
    rows = [
        {"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
        _codex_record("2026-09-30T23:00:00Z", "resp-1", first, first),
        {
            "timestamp": "2026-09-30T23:00:01Z",
            "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": first}},
        },
        # Cumulative snapshots omit the compaction request recorded here.
        {"timestamp": "2026-09-30T23:30:00Z", "type": "compacted", "payload": {}},
        _codex_record("2026-09-30T23:30:00Z", "resp-compact", compaction, _codex_sum(first, compaction)),
        {"type": "turn_context", "payload": {"model": "gpt-6-astra"}},
        _codex_record("2026-10-01T00:30:00Z", "resp-2", second, _codex_sum(first, compaction, second)),
        # A response recorded twice counts once.
        _codex_record("2026-10-01T00:30:01Z", "resp-2", second, _codex_sum(first, compaction, second)),
        {
            "timestamp": "2026-10-01T00:31:00Z",
            "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": _codex_sum(first, second)}},
        },
    ]
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))

    usage = parse_codex_session(path, "one").usage

    assert usage is not None
    assert (usage.input_tokens, usage.cached_tokens, usage.output_tokens, usage.total_tokens) == (600, 190, 80, 680)
    assert usage.turn_count == 3
    assert [(sample["timestamp"], sample["model"], sample["total_tokens"]) for sample in usage.samples] == [
        ("2026-09-30T23:00:00Z", "gpt-6.1-sol", 110),
        ("2026-09-30T23:30:00Z", "gpt-6.1-sol", 350),
        ("2026-10-01T00:30:00Z", "gpt-6-astra", 220),
    ]
    assert [row.total_tokens for row in aggregate_usage([usage], monthly=True)] == [460, 220]


def test_codex_records_disagreeing_with_the_thread_total_keep_the_provider_total(tmp_path: Path) -> None:
    recorded = _codex_usage(100, output=10)
    # The thread counter also includes usage from before this rollout recorded responses.
    thread = _codex_sum(_codex_usage(400, cached=100, output=40), recorded)
    rows = [
        {"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
        _codex_record("2026-09-30T23:00:00Z", "resp-1", recorded, thread),
    ]
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))

    usage = parse_codex_session(path, "one").usage

    assert usage is not None
    assert (usage.input_tokens, usage.cached_tokens, usage.output_tokens, usage.total_tokens) == (500, 100, 50, 550)
    assert usage.samples == []
    assert usage.measurement_kind == "provider-reported"


@pytest.mark.parametrize(
    "payload",
    [
        {"usage": {"input_tokens": 1}, "thread_token_usage": {"input_tokens": 1}},
        {"response_id": "resp-1", "usage": {}, "thread_token_usage": {"input_tokens": 1}},
        {"response_id": "resp-1", "usage": {"input_tokens": 1}, "thread_token_usage": "private-invalid"},
    ],
    ids=["missing-response", "no-counters", "invalid-thread-total"],
)
def test_codex_rejects_malformed_response_records(tmp_path: Path, payload: dict) -> None:
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps({"timestamp": "2026-09-30T23:00:00Z", "type": "token_usage_record", "payload": payload}))

    parsed = parse_codex_session(path, "one")

    assert parsed.usage is None
    assert isinstance(parsed.usage_error, ValueError)
    assert "private-invalid" not in str(parsed.usage_error)
