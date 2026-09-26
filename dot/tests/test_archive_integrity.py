"""Incomplete sources and competing captures must not erase archived evidence."""

import io
import json
import os
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event, current_thread

import pytest
from typer.testing import CliRunner

from fmind_dot.archive import parsers, store
from fmind_dot.archive import sync as archive_sync
from fmind_dot.archive.store import read_session_bundle, session_bundle_path
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, load_usage_records
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
    state = _state(tmp_path, "codex", monkeypatch)
    source = tmp_path / "source/rollout-2026-09-01T10-00-00-session.jsonl"
    conversation = {
        "type": "response_item",
        "timestamp": "2026-09-01T10:00:00Z",
        "payload": {"role": "assistant", "content": "Synthetic answer"},
    }
    metric = {
        "type": "event_msg",
        "timestamp": "2026-09-01T10:00:01Z",
        "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 100, "output_tokens": 30}}},
    }
    _write(source, [conversation, metric])
    bundle = session_bundle_path("codex", "session")
    if existing:
        sync_sessions(state, agent="codex")
    before = bundle.read_bytes() if existing else None
    _write(source, [conversation])
    with source.open("a") as stream:
        stream.write('{"type":"event_msg","payload":')

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="codex")
        manifest, records = read_session_bundle(bundle)
        assert len(records) == 1
        if existing:
            assert bundle.read_bytes() == before
            assert load_usage_records()[0].total_tokens == 130
        else:
            assert manifest.usage is None
            assert manifest.source_signature == ""
            assert manifest.completeness == "partial"


def test_grok_truncated_chunks_keep_the_longer_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(tmp_path, "grok", monkeypatch)
    source = tmp_path / "source/project/session/updates.jsonl"

    def chunk(role: str, text: str) -> dict:
        return {
            "timestamp": 1_788_256_800,
            "params": {"_meta": {"promptId": "prompt"}, "update": {"sessionUpdate": role, "content": {"text": text}}},
        }

    rows = [
        chunk("user_message_chunk", "Question"),
        chunk("agent_message_chunk", "First part. "),
        chunk("agent_message_chunk", "Final part."),
    ]
    _write(source, rows)
    sync_sessions(state, agent="grok")
    bundle = session_bundle_path("grok", "session")
    before = bundle.read_bytes()
    _write(source, rows[:-1])

    assert sync_sessions(state, agent="grok").retained == 1
    assert bundle.read_bytes() == before


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


def test_public_report_does_not_price_absent_counters_at_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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
            assert release.wait(5)
        return capture(*args, **kwargs)

    monkeypatch.setattr(archive_sync, "_capture", delayed)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="older-capture") as pool:
        older = pool.submit(sync_sessions, state, agent="claude")
        try:
            assert ready.wait(5)
            _write(source, [_claude(30)])
            assert sync_sessions(state, agent="claude").ingested == 1
            assert load_usage_records()[0].input_tokens == 30
        finally:
            release.set()
        assert older.result(timeout=5).retained == 1
    assert load_usage_records()[0].input_tokens == 30


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
    assert load_usage_records()[0].input_tokens == 20


@pytest.mark.parametrize("measured", [False, True], ids=["repair-false-zero", "retain-measured-usage"])
@pytest.mark.parametrize("known_cost", [False, True], ids=["unknown-cost", "known-cost"])
def test_parser_upgrade_removes_only_unmeasured_legacy_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, measured: bool, known_cost: bool
) -> None:
    state = _state(tmp_path, "claude", monkeypatch)
    source = tmp_path / "source/session.jsonl"
    cost = [{"type": "cost-state", "totalCostUSD": 0.25}] if known_cost else []
    _write(source, [_claude(100 if measured else None), *cost])
    parsed = parsers.parse_claude_session(source, "session")
    legacy_usage = UsageRecord(
        harness="claude",
        session_id="session",
        measurement_kind="provider-reported",
        input_tokens=100 if measured else 0,
        cost_known=known_cost,
        cost_usd=0.25 if known_cost else 0.0,
    ).finalize(fallback_timestamp="2026-09-01T10:00:00Z")
    with monkeypatch.context() as legacy:
        legacy.setattr(store, "SESSION_PARSER_VERSION", "6")
        store.ingest_session(
            "claude",
            "session",
            parsed.logs,
            store.SessionSource(type=parsed.source_type, fingerprint=parsed.fingerprint),
            usage=legacy_usage.to_dict(),
        )
    bundle = session_bundle_path("claude", "session")
    before = bundle.read_bytes()
    if measured:
        _write(source, [_claude(), *cost])

    outcome = sync_sessions(state, agent="claude")

    if measured:
        assert outcome.retained == 1
        assert bundle.read_bytes() == before
        assert load_usage_records()[0].input_tokens == 100
    else:
        assert outcome.ingested == 1
        manifest, _ = read_session_bundle(bundle)
        assert manifest.parser_version == store.SESSION_PARSER_VERSION
        if known_cost:
            assert manifest.usage is not None
            stats = aggregate_usage(load_usage_records())[0].to_dict()
            assert stats["cost_usd"] == 0.25
            assert stats["api_equivalent_usd"] is None
        else:
            assert manifest.usage is None
            assert load_usage_records() == []


@pytest.mark.parametrize("agent", ["codex", "grok"])
def test_disappearing_provider_measurement_never_becomes_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, agent: str
) -> None:
    state = _state(tmp_path, agent, monkeypatch)
    if agent == "codex":
        source = tmp_path / "source/rollout-2026-09-01T10-00-00-session.jsonl"
        conversation = {"type": "response_item", "payload": {"role": "assistant", "content": "Answer"}}
        metric = {
            "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 10}}},
        }
    else:
        source = tmp_path / "source/project/session/updates.jsonl"
        conversation = {"params": {"update": {"sessionUpdate": "agent_message_chunk", "content": {"text": "Answer"}}}}
        metric = {"params": {"update": {"sessionUpdate": "turn_completed", "usage": {"inputTokens": 10}}}}
    _write(source, [conversation, metric])
    sync_sessions(state, agent=agent)
    bundle = session_bundle_path(agent, "session")
    before = bundle.read_bytes()
    _write(source, [conversation])

    assert sync_sessions(state, agent=agent).retained == 1
    assert bundle.read_bytes() == before


@pytest.mark.parametrize("append", [False, True], ids=["equal-count", "new-message"])
def test_changed_capture_checks_each_message_and_allows_metadata_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, append: bool
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    records = [
        store.SessionLog("", "grok", "session", "user", "Question", model="old"),
        store.SessionLog("", "grok", "session", "assistant", "Long answer", model="old"),
    ]
    store.ingest_session("grok", "session", records)
    updated = [replace(record, model="new", cwd="/new") for record in records]
    assert store.ingest_session("grok", "session", updated).status == "ingested"
    shortened = [replace(updated[0], content="Question with much more text"), replace(updated[1], content="Long")]
    if append:
        shortened.append(store.SessionLog("later", "grok", "session", "user", "Another question"))

    assert store.ingest_session("grok", "session", shortened).status == "retained"
    assert read_session_bundle(session_bundle_path("grok", "session"))[1] == updated


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
    record = load_usage_records()[0]
    assert record.input_tokens == 150
    assert record.cost_known
    assert record.cost_usd == cost + 0.25


def test_optional_cache_zero_does_not_demonstrate_a_zero_token_request(tmp_path: Path) -> None:
    source = tmp_path / "session.jsonl"
    row = _claude()
    row["message"]["usage"] = {"cache_read_input_tokens": 0}
    _write(source, [row])

    assert parsers.parse_claude_session(source, "session").usage is None


@pytest.mark.parametrize("incomplete", [False, True], ids=["repair-known-cost", "retain-incomplete-evidence"])
def test_grok_parser_upgrade_repairs_cost_without_erasing_old_measurements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, incomplete: bool
) -> None:
    state = _state(tmp_path, "grok", monkeypatch)
    source = tmp_path / "source/project/session/updates.jsonl"
    metric: dict[str, object] = {"costUsdTicks": 5_000_000, "modelUsage": {"grok-test": {"inputTokens": 10}}}
    if incomplete:
        metric["usageIsIncomplete"] = True
    _write(source, [{"timestamp": 1, "params": {"update": {"sessionUpdate": "turn_completed", "usage": metric}}}])
    parsed = parsers.parse_grok_session(source, "session")
    old_usage = UsageRecord(
        harness="grok",
        session_id="session",
        measurement_kind="provider-reported",
        model="grok-test",
        input_tokens=10,
        cost_known=not incomplete,
    ).finalize(fallback_timestamp="1970-01-01T00:00:01Z")
    with monkeypatch.context() as legacy:
        legacy.setattr(store, "SESSION_PARSER_VERSION", "7")
        store.ingest_session(
            "grok",
            "session",
            parsed.logs,
            store.SessionSource(type=parsed.source_type, fingerprint=parsed.fingerprint),
            usage=old_usage.to_dict(),
        )
    bundle = session_bundle_path("grok", "session")
    before = bundle.read_bytes()

    if incomplete:
        for _ in range(2):
            with pytest.raises(DotError, match="1 failure"):
                sync_sessions(state, agent="grok")
            assert bundle.read_bytes() == before
            assert load_usage_records()[0].legacy_accounting
    else:
        assert sync_sessions(state, agent="grok").ingested == 1
        record = load_usage_records()[0]
        assert record.cost_known
        assert record.cost_usd == pytest.approx(0.0005)
        assert record.input_tokens == 10
        assert not record.legacy_accounting
