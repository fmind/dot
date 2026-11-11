"""Usage reports reconcile request events, immutable history, and monthly boundaries."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fmind_dot.archive import store
from fmind_dot.archive.parsers import parse_claude_session
from fmind_dot.archive.store import SessionLog, SessionSource, ingest_session
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, iter_usage_records, write_usage_stats
from fmind_dot.cli import app
from tests.fakes import CliRunner


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


def test_public_monthly_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    record = session(request("2026-08-31T23:00:00Z"), request("2026-09-01T23:00:00Z"))
    ingest_session("codex", "one", [], usage=record.to_dict())
    report = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--monthly", "--json"])
    assert report.exit_code == 0, report.output
    result = json.loads(report.output)
    assert result["prompts"] is None
    assert len(result["usage"]) == 2


def test_usage_query_rejects_invalid_usage_and_mismatched_identity() -> None:
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


def test_reports_include_whole_until_day_and_exact_timestamp() -> None:
    for identity, timestamp in [("day", "2026-09-15T12:00:00Z"), ("next", "2026-09-16T00:00:00Z")]:
        usage = UsageRecord(timestamp=timestamp, harness="codex", session_id=identity, input_tokens=10).finalize(
            fallback_timestamp="2026-09-01T00:00:00Z"
        )
        ingest_session(
            "codex",
            identity,
            [SessionLog(timestamp, "codex", identity, "user", "hello", "/work")],
            usage=usage.to_dict(),
        )
    runner = CliRunner()
    for command in [["agent", "stats"], ["agent", "stats", "--prompts-only"], ["agent", "stats", "--tokens-only"]]:
        result = runner.invoke(app, [*command, "--since", "2026-09-15", "--until", "2026-09-15", "--json"])
        assert result.exit_code == 0, result.output
        document = json.loads(result.stdout)
        assert document["schema"] == "dot.agent.stats/v4"
        if "--tokens-only" not in command:
            assert document["prompts"]["prompts"] == 1
        if "--prompts-only" not in command:
            assert document["usage"][0]["total_tokens"] == 10
    result = runner.invoke(app, ["agent", "stats", "--until", "2026-09-15T00:00:00Z", "--json"])
    document = json.loads(result.stdout)
    assert document["prompts"]["prompts"] == 0
    assert document["usage"] == []


@pytest.mark.parametrize("flag", ["--agent", "-a"])
def test_agent_filter_aliases_select_the_same_usage(flag: str) -> None:
    for agent in ["agy", "claude"]:
        record = UsageRecord(
            timestamp="2026-09-15T12:00:00Z", harness=agent, session_id=agent, input_tokens=10
        ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
        ingest_session(agent, agent, [], usage=record.to_dict())
    result = CliRunner().invoke(app, ["agent", "stats", "--sessions", flag, "agy", "--limit", "0", "--json"])
    assert result.exit_code == 0, result.output
    assert [record["harness"] for record in json.loads(result.stdout)["records"]] == ["agy"]


def test_stats_are_readable_in_a_narrow_terminal_and_preserve_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "60")
    timestamp = "2026-09-15T12:00:00Z"
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        session_id="readable",
        model="unknown-model",
        input_tokens=1234567,
        measurement_kind="provider-reported",
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    ingest_session(
        "codex",
        "readable",
        [SessionLog(timestamp, "codex", "readable", "user", "private words")],
        usage=record.to_dict(),
    )
    runner = CliRunner()
    human = runner.invoke(app, ["agent", "stats", "--by-model"])
    assert human.exit_code == 0, human.output
    assert "Prompt activity" in human.stdout
    assert "Total tokens: 1,234,567" in human.stdout
    assert "API equivalent: unknown" in human.stdout
    assert "Recorded cost: unknown" in human.stdout
    assert "private words" not in human.stdout
    assert "\t" not in human.stdout
    assert max(map(len, human.stdout.splitlines())) <= 60
    document = json.loads(runner.invoke(app, ["agent", "stats", "--by-model", "--json"]).stdout)
    assert document["schema"] == "dot.agent.stats/v4"
    assert document["usage"][0]["total_tokens"] == 1234567
    assert document["usage"][0]["api_equivalent_usd"] is None
    assert document["prompts"]["prompts"] == 1


def test_mixed_models_unknown_cost_and_comparable_statistics() -> None:
    # An archived Codex session that switched models without dated requests stays one mixed measurement.
    record = UsageRecord(
        harness="codex", session_id="example", measurement_kind="provider-reported", input_tokens=150, total_tokens=150
    )
    for model in ("first", "second"):
        record.observe_model(model)
    record = record.finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    assert record.model == "mixed"
    assert record.total_tokens == 150
    assert record.to_dict()["cost_usd"] is None
    estimate = UsageRecord(
        harness="agy", session_id="estimate", measurement_kind="estimated", total_tokens=50
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    stats = aggregate_usage([record, estimate], by_model=True)
    output = io.StringIO()
    write_usage_stats(output, stats, by_model=True)
    assert "unknown" in output.getvalue()
    assert "No combined total" in output.getvalue()
    assert all(row.to_dict()["cost_usd"] is None for row in stats)
