"""Incomplete sources and competing captures must not erase archived evidence."""

import io
import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Event, current_thread

import pytest
from typer.testing import CliRunner

from fmind_dot.archive import parsers, store
from fmind_dot.archive import sync as archive_sync
from fmind_dot.archive.store import read_session_bundle, session_bundle_path
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, iter_usage_records
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.state import State


def _state(home: Path, agent: str, monkeypatch: pytest.MonkeyPatch) -> State:
    monkeypatch.setenv("HOME", str(home))
    state = State(stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    state.config.agent.sources[agent] = str(home / "source")
    return state


def _write(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    previous = path.stat().st_mtime_ns if path.exists() else 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    if previous:
        os.utime(path, ns=(previous + 1_000_000_000, previous + 1_000_000_000))


def _claude(tokens: int | None = None, *, identity: str = "answer", model: str = "claude-sonnet-4-6") -> dict:
    message: dict[str, object] = {
        "id": identity,
        "model": model,
        "content": [{"type": "text", "text": "Synthetic answer"}],
    }
    if tokens is not None:
        message["usage"] = {"input_tokens": tokens, "output_tokens": 0}
    return {"type": "assistant", "timestamp": "2026-09-01T10:00:00Z", "message": message}


@pytest.mark.parametrize("existing", [False, True], ids=["first-capture", "retained-measurement"])
def test_malformed_usage_line_never_publishes_partial_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/project/session.jsonl"
    _write(source, [_claude(130)])
    bundle = session_bundle_path("claude", "session")
    if existing:
        sync_sessions(state, agent="claude")
    before = bundle.read_bytes() if existing else None
    _write(source, [_claude()])
    with source.open("a") as stream:
        stream.write('{"type":"assistant","message":')

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        manifest, records = read_session_bundle(bundle)
        assert len(records) == 1
        if existing:
            assert bundle.read_bytes() == before
            assert next(iter_usage_records()).total_tokens == 130
        else:
            assert manifest.usage is None
            assert manifest.source_signature == ""
            assert manifest.completeness == "partial"


@pytest.mark.parametrize("missing", [None, {}], ids=["absent", "empty"])
def test_missing_claude_counters_retain_existing_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: dict | None
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    _write(source, [_claude(130)])
    sync_sessions(state, agent="claude")
    bundle = session_bundle_path("claude", "session")
    before = bundle.read_bytes()
    row = _claude()
    if missing is not None:
        row["message"]["usage"] = missing
    _write(source, [row])

    assert sync_sessions(state, agent="claude").retained == 1
    assert bundle.read_bytes() == before


def test_public_report_does_not_price_absent_counters_at_zero(tmp_path: Path) -> None:
    source = tmp_path / ".claude/projects/project/session.jsonl"
    _write(source, [_claude()])

    result = CliRunner().invoke(app, ["agent", "stats", "--agent", "claude", "--tokens-only", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["usage"] == []
    assert read_session_bundle(session_bundle_path("claude", "session"))[0].usage is None


@pytest.mark.parametrize("row", [_claude(0), _claude(model="<synthetic>")], ids=["explicit-zero", "synthetic"])
def test_known_zero_measurements_remain_available(tmp_path: Path, row: dict) -> None:
    source = tmp_path / "session.jsonl"
    _write(source, [row])

    parsed = parsers.parse_claude_session(source, "session")

    assert parsed.usage_error is None
    assert parsed.usage is not None
    assert parsed.usage.total_tokens == 0


def test_streamed_measurement_can_complete_an_earlier_missing_block(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    _write(source, [_claude(), _claude(100)])
    parsed = parsers.parse_claude_session(source, "session")
    assert parsed.usage is not None
    assert parsed.usage.total_tokens == 100

    # A different unmeasured request makes the whole-session total unavailable.
    _write(source, [_claude(100), _claude(identity="other")])
    assert parsers.parse_claude_session(source, "session").usage is None


def test_concurrent_equal_count_capture_never_replaces_newer_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    _write(source, [_claude(10)])
    sync_sessions(state, agent="claude")
    _write(source, [_claude(20)])
    ready, release = Event(), Event()
    capture = archive_sync._capture  # noqa: SLF001 - pause between parsing and locked publication

    def delayed(*args, **kwargs):
        if current_thread().name.startswith("older-capture"):
            ready.set()
            assert release.wait(30)
        return capture(*args, **kwargs)

    monkeypatch.setattr(archive_sync, "_capture", delayed)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="older-capture") as pool:
        older = pool.submit(sync_sessions, state, agent="claude")
        try:
            assert ready.wait(30)
            _write(source, [_claude(30)])
            assert sync_sessions(state, agent="claude").ingested == 1
            assert next(iter_usage_records()).input_tokens == 30
        finally:
            release.set()
        assert older.result(timeout=30).retained == 1
    assert next(iter_usage_records()).input_tokens == 30


def test_source_changed_during_parse_is_not_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    _write(source, [_claude(10)])
    adapter = parsers.AGENT_ADAPTERS["claude"]

    def changing(path: Path, identity: str, cwd: str) -> parsers.ParsedSession:
        parsed = adapter.parser(path, identity, cwd)
        _write(path, [_claude(20)])
        return parsed

    with monkeypatch.context() as changed:
        changed.setitem(parsers.AGENT_ADAPTERS, "claude", replace(adapter, parser=changing))
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
    assert not session_bundle_path("claude", "session").exists()
    assert sync_sessions(state, agent="claude").ingested == 1
    assert next(iter_usage_records()).input_tokens == 20


def test_source_written_once_during_parse_is_captured_on_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    _write(source, [_claude(10)])
    adapter = parsers.AGENT_ADAPTERS["claude"]
    calls = 0

    def appending_once(path: Path, identity: str, cwd: str) -> parsers.ParsedSession:
        nonlocal calls
        calls += 1
        parsed = adapter.parser(path, identity, cwd)
        if calls == 1:
            _write(path, [_claude(20)])
        return parsed

    with monkeypatch.context() as changed:
        changed.setitem(parsers.AGENT_ADAPTERS, "claude", replace(adapter, parser=appending_once))
        assert sync_sessions(state, agent="claude").ingested == 1
    assert calls == 2
    assert next(iter_usage_records()).input_tokens == 20
    # The retry recorded the stable source's signature, so the next pass skips it.
    assert sync_sessions(state, agent="claude").unchanged == 1


@pytest.mark.parametrize("known_cost", [False, True], ids=["unknown-cost", "known-cost"])
def test_parser_upgrade_retains_an_older_parser_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, known_cost: bool
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    cost = [{"type": "cost-state", "totalCostUSD": 0.25}] if known_cost else []
    _write(source, [_claude(100), *cost])
    parsed = parsers.parse_claude_session(source, "session")
    older_usage = UsageRecord(
        harness="claude",
        session_id="session",
        measurement_kind="provider-reported",
        input_tokens=100,
        cost_known=known_cost,
        cost_usd=0.25 if known_cost else 0.0,
    ).finalize(fallback_timestamp="2026-09-01T10:00:00Z")
    with monkeypatch.context() as older:
        older.setattr(store, "SESSION_PARSER_VERSION", "9")
        store.ingest_session(
            "claude",
            "session",
            parsed.logs,
            store.SessionSource(type=parsed.source_type, fingerprint=parsed.fingerprint),
            usage=older_usage.to_dict(),
        )
    bundle = session_bundle_path("claude", "session")
    before = bundle.read_bytes()
    _write(source, [_claude(), *cost])

    outcome = sync_sessions(state, agent="claude")

    # The current parser republishes the transcript but keeps the parser-9 measurement.
    assert outcome.retained == 1
    manifest = store.read_session_manifest(bundle)
    assert (manifest.parser_version, manifest.usage_parser_version) == (store.SESSION_PARSER_VERSION, "9")
    assert manifest.usage == json.loads(before.split(b"\n")[1])
    [record] = list(iter_usage_records())
    assert (record.input_tokens, record.legacy_accounting) == (100, False)
    republished = bundle.read_bytes()
    assert sync_sessions(state, agent="claude").retained == 1
    assert bundle.read_bytes() == republished


def test_disappearing_database_measurement_never_becomes_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(tmp_path, "copilot", monkeypatch)
    source = tmp_path / "source"
    with closing(sqlite3.connect(source)) as connection:
        connection.executescript(
            """CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
            CREATE TABLE turns(id INTEGER, session_id TEXT, turn_index INTEGER, user_message TEXT,
                assistant_response TEXT, timestamp TEXT);
            CREATE TABLE assistant_usage_events(session_id TEXT, model TEXT, input_tokens INTEGER,
                output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);
            INSERT INTO sessions VALUES('session', '', '2026-09-01T10:00:00Z');
            INSERT INTO turns VALUES(1, 'session', 1, 'Question', 'Answer', '2026-09-01T10:00:00Z');
            INSERT INTO assistant_usage_events VALUES('session', 'gpt-test', 10, 0, 0, 0, 0);"""
        )
    sync_sessions(state, agent="copilot")
    bundle = session_bundle_path("copilot", "session")
    before = bundle.read_bytes()
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("DELETE FROM assistant_usage_events")
        connection.commit()

    assert sync_sessions(state, agent="copilot").retained == 1
    assert bundle.read_bytes() == before
    assert next(iter_usage_records()).input_tokens == 10


@pytest.mark.parametrize("append", [False, True], ids=["equal-count", "new-message"])
def test_changed_capture_checks_each_message_and_allows_metadata_changes(append: bool) -> None:
    records = [
        store.SessionLog("", "claude", "session", "user", "Question", model="old"),
        store.SessionLog("", "claude", "session", "assistant", "Long answer", model="old"),
    ]
    store.ingest_session("claude", "session", records)
    updated = [replace(record, model="new", cwd="/new") for record in records]
    assert store.ingest_session("claude", "session", updated).status == "ingested"
    shortened = [replace(updated[0], content="Question with much more text"), replace(updated[1], content="Long")]
    if append:
        shortened.append(store.SessionLog("later", "claude", "session", "user", "Another question"))

    assert store.ingest_session("claude", "session", shortened).status == "retained"
    assert read_session_bundle(session_bundle_path("claude", "session"))[1] == updated


def test_known_provider_cost_survives_missing_token_measurement(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    _write(source, [_claude(), {"type": "cost-state", "totalCostUSD": 0.25}])

    parsed = parsers.parse_claude_session(source, "session")

    assert parsed.usage is not None
    assert (parsed.usage.cost_known, parsed.usage.cost_usd) == (True, 0.25)
    stats = aggregate_usage([parsed.usage])[0].to_dict()
    assert stats["cost_usd"] == 0.25
    assert stats["api_equivalent_usd"] is None
    assert stats["pricing_complete"] is False


@pytest.mark.parametrize("cost", [0.0, 0.25], ids=["known-zero", "known-cost"])
def test_recapture_preserves_known_cost_until_source_reports_it_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cost: float
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    _write(source, [_claude(100), {"type": "cost-state", "totalCostUSD": cost}])
    sync_sessions(state, agent="claude")
    bundle = session_bundle_path("claude", "session")
    before = bundle.read_bytes()

    _write(source, [_claude(150)])
    for _ in range(2):
        assert sync_sessions(state, agent="claude").retained == 1
        assert bundle.read_bytes() == before

    _write(source, [_claude(150), {"type": "cost-state", "totalCostUSD": cost + 0.25}])
    assert sync_sessions(state, agent="claude").ingested == 1
    record = next(iter_usage_records())
    assert record.input_tokens == 150
    assert record.cost_known
    assert record.cost_usd == cost + 0.25


def test_optional_cache_zero_does_not_demonstrate_a_zero_token_request(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    row = _claude()
    row["message"]["usage"] = {"cache_read_input_tokens": 0}
    _write(source, [row])

    assert parsers.parse_claude_session(source, "session").usage is None


@pytest.mark.parametrize(("harness", "legacy"), [("grok", True), ("claude", False)])
def test_archived_parser_7_usage_is_legacy_only_for_grok(
    monkeypatch: pytest.MonkeyPatch, harness: str, legacy: bool
) -> None:
    # Grok's parser 7 accounting stays flagged as legacy in its retired archive; other harnesses' does not.
    usage = UsageRecord(
        harness=harness,
        session_id="session",
        measurement_kind="provider-reported",
        model="fixture",
        input_tokens=10,
    ).finalize(fallback_timestamp="2026-09-01T10:00:00Z")
    with monkeypatch.context() as older:
        older.setattr(store, "SESSION_PARSER_VERSION", "7")
        store.ingest_session(harness, "session", [], usage=usage.to_dict())

    [record] = list(iter_usage_records())
    assert (record.input_tokens, record.legacy_accounting) == (10, legacy)


def _sync_json(state: State, agent: str) -> dict[str, object]:
    state.stdout = io.StringIO()
    sync_sessions(state, agent=agent, as_json=True)
    return json.loads(state.stdout.getvalue())


def test_sync_json_proves_only_retained_transcripts_that_match_the_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No retained session: nothing to prove.
    state = _state(tmp_path / "none", "claude", monkeypatch)
    _write(tmp_path / "none/source/session.jsonl", [_claude(130)])
    first = _sync_json(state, "claude")
    assert (first["schema"], first["ingested"], first["retained"], first["retained_current_transcripts"]) == (
        "dot.agent.session.sync/v2",
        1,
        0,
        0,
    )
    again = _sync_json(state, "claude")
    assert (again["unchanged"], again["retained"], again["retained_current_transcripts"]) == (1, 0, 0)

    # Retained and current: only the usage measurement is kept; the archived transcript is the source's.
    state = _state(tmp_path / "usage", "claude", monkeypatch)
    source = tmp_path / "usage/source/session.jsonl"
    _write(source, [_claude(130)])
    sync_sessions(state, agent="claude")
    _write(source, [_claude()])
    current = _sync_json(state, "claude")
    assert (current["failed"], current["retained"], current["retained_current_transcripts"]) == (0, 1, 1)

    # Retained but stale: the source shrank, so the archive keeps a transcript that no longer matches it.
    state = _state(tmp_path / "stale", "claude", monkeypatch)
    source = tmp_path / "stale/source/session.jsonl"
    rows = [
        {"type": "user", "timestamp": "2026-09-01T09:59:00Z", "message": {"content": "Question"}},
        _claude(130),
    ]
    _write(source, rows)
    sync_sessions(state, agent="claude")
    _write(source, rows[:-1])
    stale = _sync_json(state, "claude")
    assert (stale["failed"], stale["retained"], stale["retained_current_transcripts"]) == (0, 1, 0)
