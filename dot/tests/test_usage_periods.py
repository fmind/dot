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
    ).finalize()


def session(*samples: UsageRecord) -> UsageRecord:
    record = request(samples[-1].timestamp)
    record.set_samples(list(samples))
    return record.finalize()


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
    write_usage_stats(output, [row], as_json=False, by_model=False)
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
    billed = runner.invoke(app, ["--config", str(config), "agent", "usage", "stats", "--billing", "--json"])
    assert billed.exit_code == 0, billed.output
    assert json.loads(billed.output)[0]["period_start"].startswith("2026-08-15")
    config.write_text("agent:\n  subscriptions:\n    codex:\n      renewal_day: 32\n")
    assert runner.invoke(app, ["--config", str(config), "config", "validate"]).exit_code != 0
    config.write_text("agent:\n  subscriptions:\n    codex:\n      renewal_day: 1\n      timezone: Invalid/Zone\n")
    assert runner.invoke(app, ["--config", str(config), "config", "validate"]).exit_code != 0


def test_usage_query_still_rejects_corrupt_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "one", [], usage=request("2026-09-01T00:00:00Z").to_dict())
    assert len(load_usage_records()) == 1
    next(tmp_path.rglob("transcript.jsonl")).write_text("corrupt")
    with pytest.raises(ValueError, match="transcript fingerprint"):
        load_usage_records()


def test_recapture_preserves_parser_three_and_selects_corrected_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fmind_dot.archive import store

    monkeypatch.setenv("HOME", str(tmp_path))
    original = request("2026-09-01T00:00:00Z", tokens=200)
    source = store.SessionSource(type="fixture", fingerprint=store.fingerprint_bytes(b"same source"))
    with monkeypatch.context() as previous:
        previous.setattr(store, "SESSION_PARSER_VERSION", "3")
        ingest_session("codex", "one", [], source, usage=original.to_dict())
    old = {path: path.read_bytes() for path in store.session_store_root().rglob("*") if path.is_file()}
    assert load_usage_records()[0].legacy_accounting
    corrected = session(request("2026-09-01T00:00:00Z", tokens=100))
    ingest_session("codex", "one", [], source, usage=corrected.to_dict())
    records = load_usage_records()
    assert len(records) == 1
    assert records[0].total_tokens == 100
    assert not records[0].legacy_accounting
    assert all(path.read_bytes() == content for path, content in old.items())
