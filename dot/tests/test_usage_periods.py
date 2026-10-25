"""Usage reports reconcile request events, immutable history, and monthly boundaries."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive.parsers import parse_claude_session
from fmind_dot.archive.store import ingest_session
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, iter_usage_records, write_usage_stats
from fmind_dot.cli import app
from fmind_dot.errors import DotError


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


def test_monthly_periods_are_utc_calendar_months_across_the_year_end() -> None:
    record = session(request("2026-12-31T23:59:59Z"), request("2027-01-01T00:00:00Z"))
    rows = aggregate_usage([record], monthly=True)
    assert [(r.period_start, r.period_end) for r in rows] == [
        ("2026-12-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00"),
        ("2027-01-01T00:00:00+00:00", "2027-02-01T00:00:00+00:00"),
    ]


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


@pytest.mark.parametrize("child_first", [False, True], ids=["parent-first", "child-first"])
@pytest.mark.parametrize("selection", ["all", "model", "month", "since", "until"])
def test_session_cost_includes_sidechains_before_grouping(selection: str, child_first: bool) -> None:
    parent = UsageRecord(
        timestamp="2026-09-30T23:00:00Z",
        harness="claude",
        session_id="parent",
        model="claude-opus-5-5",
        input_tokens=100,
        cost_usd=5.0,
        cost_known=True,
        measurement_kind="provider-reported",
    ).finalize()
    child = UsageRecord(
        timestamp="2026-10-01T01:00:00Z",
        harness="claude",
        session_id="child",
        parent_session_id="parent",
        sidechain=True,
        model="claude-haiku-4-5",
        input_tokens=50,
        measurement_kind="provider-reported",
    ).finalize()
    records = [child, parent] if child_first else [parent, child]
    boundary = datetime(2026, 10, 1, tzinfo=UTC)
    rows = aggregate_usage(
        records,
        by_model=selection == "model",
        monthly=selection == "month",
        since=boundary if selection == "since" else None,
        until=boundary if selection == "until" else None,
    )
    assert rows
    if selection == "all":
        assert len(rows) == 1
        assert rows[0].total_tokens == 150
        assert rows[0].to_dict()["cost_usd"] == 5.0
        assert rows[0].to_dict()["cost_complete"] is True
    else:
        assert all(row.to_dict()["cost_usd"] is None for row in rows)
        assert all(row.to_dict()["cost_complete"] is False for row in rows)


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


def test_archived_codex_samples_split_months_and_models() -> None:
    # Archived Codex bundles keep one sample per request; reports allocate each to its month and model.
    record = session(
        request("2026-08-31T23:00:00Z", tokens=100),
        request("2026-09-01T23:00:00Z", model="gpt-5.5", tokens=200),
    )
    assert record.total_tokens == 300
    assert len(record.samples) == 2
    assert [row.input_tokens for row in aggregate_usage([record], monthly=True)] == [100, 200]
    assert [row.model for row in aggregate_usage([record], by_model=True)] == ["gpt-5.4", "gpt-5.5"]
    # A session without trustworthy request deltas stays whole in the month of its timestamp.
    unsampled = request("2026-09-02T00:00:00Z", tokens=50)
    assert not unsampled.samples
    assert [(row.period_start[:10], row.total_tokens) for row in aggregate_usage([unsampled], monthly=True)] == [
        ("2026-09-01", 50)
    ]


def test_public_monthly_report_and_retired_billing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    record = session(request("2026-08-31T23:00:00Z"), request("2026-09-01T23:00:00Z"))
    ingest_session("codex", "one", [], usage=record.to_dict())
    runner = CliRunner()
    report = runner.invoke(app, ["agent", "stats", "--tokens-only", "--monthly", "--json"])
    assert report.exit_code == 0, report.output
    result = json.loads(report.output)
    assert result["prompts"] is None
    assert len(result["usage"]) == 2
    assert "subscription_usd" not in result["usage"][0]
    assert runner.invoke(app, ["agent", "stats", "--tokens-only", "--billing"]).exit_code == 2
    config = tmp_path / "config.yaml"
    config.write_text("agent:\n  subscriptions:\n    codex:\n      renewal_day: 15\n")
    invalid = runner.invoke(app, ["--config", str(config), "config", "show"])
    assert invalid.exit_code == 1
    assert isinstance(invalid.exception, DotError)
    assert "agent.subscriptions" in str(invalid.exception)


def test_usage_query_rejects_invalid_usage_and_mismatched_identity() -> None:
    from fmind_dot.archive import store

    ingest_session("codex", "one", [], usage=request("2026-09-01T00:00:00Z").to_dict())
    assert len(list(iter_usage_records())) == 1
    path = store.session_bundle_path("codex", "one")
    # Schema 4 publishes usage on the line after the manifest.
    header, usage_line = path.read_text().splitlines()[:2]
    usage = json.loads(usage_line)
    path.write_text(f"{header}\n{json.dumps(usage | {'input_tokens': -1})}\n")
    with pytest.raises(ValueError, match="non-negative integer"):
        list(iter_usage_records())
    path.write_text(f"{header}\n{json.dumps(usage | {'session_id': 'two'})}\n")
    with pytest.raises(ValueError, match="does not match its session"):
        list(iter_usage_records())


@pytest.mark.parametrize(("parser", "legacy"), [("9", False), ("3", True)], ids=["older", "legacy"])
def test_recapture_replaces_older_parser_accounting(monkeypatch: pytest.MonkeyPatch, parser: str, legacy: bool) -> None:
    from fmind_dot.archive import store

    original = request("2026-09-01T00:00:00Z", tokens=200)
    source = store.SessionSource(type="fixture", fingerprint=store.fingerprint_bytes(b"same source"))
    with monkeypatch.context() as previous:
        previous.setattr(store, "SESSION_PARSER_VERSION", parser)
        ingest_session("codex", "one", [], source, usage=original.to_dict())
    assert next(iter_usage_records()).legacy_accounting is legacy
    corrected = session(request("2026-09-01T00:00:00Z", tokens=100))
    ingest_session("codex", "one", [], source, usage=corrected.to_dict())
    records = list(iter_usage_records())
    assert len(records) == 1
    assert records[0].total_tokens == 100
    assert not records[0].legacy_accounting
    assert [path.name for path in store.discover_session_bundles()] == ["one.jsonl"]


def test_archived_codex_requests_split_at_the_utc_month_boundary() -> None:
    record = session(
        request("2026-09-30T23:00:00Z", model="gpt-6.1-sol", tokens=110),
        request("2026-09-30T23:30:00Z", model="gpt-6.1-sol", tokens=350),
        request("2026-10-01T00:30:00Z", model="gpt-6-astra", tokens=220),
    )
    assert (record.total_tokens, record.turn_count) == (680, 3)
    assert [(sample["timestamp"], sample["model"], sample["total_tokens"]) for sample in record.samples] == [
        ("2026-09-30T23:00:00Z", "gpt-6.1-sol", 110),
        ("2026-09-30T23:30:00Z", "gpt-6.1-sol", 350),
        ("2026-10-01T00:30:00Z", "gpt-6-astra", 220),
    ]
    assert [row.total_tokens for row in aggregate_usage([record], monthly=True)] == [460, 220]


def _usage(session_id: str, timestamp: str, *, cost: float = 0.0) -> dict[str, object]:
    record = request(timestamp)
    record.session_id = session_id
    record.cost_usd, record.cost_known = cost, bool(cost)
    return record.to_dict()


def test_window_skips_only_families_measured_outside_it() -> None:
    from fmind_dot.archive import store
    from fmind_dot.archive.store import SessionSource
    from fmind_dot.archive.usage import iter_usage_records

    ingest_session("codex", "recent", [], usage=_usage("recent", "2026-09-02T12:00:00Z", cost=1.0))
    # The parent is outside the window, its sidechain inside: the parent's cost includes the
    # sidechain, so it must still be read and keep the session cost unattributed.
    ingest_session("codex", "parent", [], usage=_usage("parent", "2026-08-01T00:00:00Z", cost=2.0))
    sidechain = SessionSource(sidechain=True, parent_session_id="parent")
    ingest_session("codex", "child", [], sidechain, usage=_usage("child", "2026-09-02T13:00:00Z"))
    ingest_session("codex", "old", [], usage=_usage("old", "2026-07-01T00:00:00Z"))
    old = store.session_bundle_path("codex", "old")
    header = old.read_text().splitlines()[0]
    assert json.loads(header)["usage_last_timestamp"] == "2026-07-01T00:00:00+00:00"
    # A corrupt usage line proves the window never decodes a family measured outside it.
    old.write_text(f"{header}\n{{broken\n")
    since, until = datetime(2026, 9, 2, tzinfo=UTC), datetime(2026, 9, 3, tzinfo=UTC)

    windowed = aggregate_usage(iter_usage_records(since, until), since=since, until=until)

    assert [(row.sessions, row.total_tokens, row.cost_usd) for row in windowed] == [(2, 2_000_000, 1.0)]
    with pytest.raises(ValueError, match="invalid session usage"):
        list(iter_usage_records())


def test_sync_upgrades_schema_3_bundles_in_place() -> None:
    from fmind_dot.archive import store
    from fmind_dot.archive.sync import sync_sessions
    from fmind_dot.state import State

    usage = _usage("one", "2026-09-01T00:00:00Z")
    ingest_session(
        "claude", "one", [store.SessionLog("2026-09-01T00:00:00Z", "claude", "one", "user", "hi")], usage=usage
    )
    path = store.session_bundle_path("claude", "one")
    header, _, *records = path.read_text().splitlines()
    legacy = json.loads(header) | {"schema_version": 3, "usage": usage}
    for key in ("usage_first_timestamp", "usage_last_timestamp"):
        legacy.pop(key)
    path.write_text("\n".join([json.dumps(legacy), *records]) + "\n")
    manifest, logs = store.read_session_bundle(path)
    assert (manifest.schema_version, manifest.usage) == (3, usage)
    state = State(stdout=io.StringIO(), stderr=io.StringIO())

    sync_sessions(state, agent="claude", dry_run=True)
    assert store.read_session_manifest(path).schema_version == 3
    sync_sessions(state, agent="claude")

    upgraded, upgraded_logs = store.read_session_bundle(path)
    assert (upgraded.schema_version, upgraded.usage, upgraded_logs) == (4, usage, logs)
    assert (upgraded.ingested_at, upgraded.source_fingerprint) == (manifest.ingested_at, manifest.source_fingerprint)
    assert "usage" not in json.loads(path.read_text().splitlines()[0])


def test_unreadable_legacy_bundle_fails_sync_without_failing_the_capture(tmp_path: Path) -> None:
    from fmind_dot.archive import store
    from fmind_dot.archive.sync import sync_sessions
    from fmind_dot.state import State

    (tmp_path / ".claude/projects").mkdir(parents=True)
    ingest_session("claude", "one", [store.SessionLog("2026-09-01T00:00:00Z", "claude", "one", "user", "hi")])
    path = store.session_bundle_path("claude", "one")
    header = json.loads(path.read_text().splitlines()[0]) | {"schema_version": 3, "usage": None}
    path.write_text(json.dumps(header) + "\nnot json\n")
    stderr = io.StringIO()
    state = State(stdout=io.StringIO(), stderr=stderr)

    assert sync_sessions(state, agent="claude", quiet=True).failed == 1
    assert "upgrade session bundle" in stderr.getvalue()
    sync_state = json.loads((store.session_store_root() / "claude/.sync.json").read_text())
    assert sync_state["failed"] == 0
