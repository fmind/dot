"""Observable capture, replacement, retired-store, and usage selection contracts."""

import io
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

import pytest

from fmind_dot.archive import parsers
from fmind_dot.archive import store as session_store
from fmind_dot.archive.parsers import GROK_TRANSCRIPT_NAME
from fmind_dot.archive.query import SessionQuery, query_session_summaries
from fmind_dot.archive.store import (
    ensure_session_store,
    read_session_bundle,
    read_session_manifest,
    session_bundle_path,
    session_store_root,
)
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import load_usage_records
from fmind_dot.errors import DotError
from fmind_dot.state import State

# A correct lock always exhausts this window, so it bounds the test's cost as well.
_RACE_WINDOW_SECONDS = 0.2


def _text(stream: IO[str]) -> str:
    assert isinstance(stream, io.StringIO)
    return stream.getvalue()


def _answer(identity: str, timestamp: str, input_tokens: int, output_tokens: int) -> str:
    return (
        json.dumps(
            {
                "type": "assistant",
                "timestamp": timestamp,
                "message": {
                    "id": identity,
                    "model": "fixture",
                    "content": [{"type": "text", "text": f"response {identity}"}],
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
                },
            }
        )
        + "\n"
    )


def source_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[State, Path]:
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / "claude"
    source.mkdir()
    transcript = source / "fixture-id.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "timestamp": "2026-09-01T10:00:00Z", "message": {"content": "fixture"}})
        + "\n"
        + _answer("answer-1", "2026-09-01T10:01:00Z", 10, 5)
    )
    state = State(stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    for agent in state.config.agent.sources:
        state.config.agent.sources[agent] = str(tmp_path / "absent" / agent)
    state.config.agent.sources["claude"] = str(source)
    return state, transcript


def _tokens() -> list[tuple[int, int]]:
    return [(record.input_tokens, record.output_tokens) for record in load_usage_records()]


def test_failed_publication_leaves_no_bundle_and_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)

    def fail(_path: Path, _content: bytes) -> None:
        raise OSError("synthetic write failure")

    with monkeypatch.context() as failure:
        failure.setattr(session_store, "write_private_file", fail)
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
    assert "synthetic write failure" in _text(state.stderr)
    assert query_session_summaries() == []
    assert load_usage_records() == []

    sync_sessions(state, agent="claude")
    sync_sessions(state, agent="claude")
    assert len(query_session_summaries()) == 1
    assert _tokens() == [(10, 5)]


def test_latest_copy_grows_with_its_source_and_survives_source_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))

    sync_sessions(state, agent="claude")
    source.unlink()
    sync_sessions(state, agent="claude")

    [summary] = query_session_summaries(SessionQuery(agent="claude"))
    assert summary.record_count == 3
    assert _tokens() == [(30, 12)]


def test_truncated_source_never_shrinks_the_archived_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    source.write_text(json.dumps({"type": "user", "message": {"content": "rotated"}}) + "\n")

    sync_sessions(state, agent="claude")

    assert "agent-session: retained claude records=2" in _text(state.stderr)
    _, records = read_session_bundle(session_bundle_path("claude", "fixture-id"))
    assert [record.content for record in records] == ["fixture", "response answer-1"]
    assert _tokens() == [(10, 5)]


def test_usage_error_keeps_the_last_measured_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression for 2b5fbbd: a failed extraction must never cost the measured usage."""
    state, source = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    measured = path.read_bytes()
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", -1, 7))

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        assert "kept the archived copy and its usage" in _text(state.stderr)
        assert path.read_bytes() == measured
        assert _tokens() == [(10, 5)]

    # Once the source measures again, the longer transcript and its usage replace the copy.
    source.write_text(source.read_text().replace('"input_tokens": -1', '"input_tokens": 20'))
    sync_sessions(state, agent="claude")
    assert read_session_manifest(path).record_count == 3
    assert _tokens() == [(30, 12)]


@pytest.mark.parametrize("field", ["input_tokens", "cost_usd"])
@pytest.mark.parametrize("value", ["private-invalid-metric", True, [], {}], ids=["string", "boolean", "list", "object"])
def test_wrong_type_usage_keeps_the_last_measured_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows.append({"type": "cost-state", "totalCostUSD": 0.25})
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    measured = path.read_bytes()
    if field == "input_tokens":
        rows[1]["message"]["usage"][field] = value
    else:
        rows[-1]["totalCostUSD"] = value
    source_info = source.stat()
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    # Equal-length replacements must advance mtime even on a coarse-clock filesystem.
    os.utime(source, ns=(source_info.st_atime_ns, source_info.st_mtime_ns + 1_000_000_000))

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        assert path.read_bytes() == measured
        assert "kept the archived copy and its usage" in _text(state.stderr)
        assert "private-invalid-metric" not in _text(state.stderr)


@pytest.mark.parametrize(
    "value", [[], "private-invalid-container", True, 1], ids=["list", "string", "boolean", "number"]
)
def test_malformed_usage_container_keeps_the_last_measured_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    measured = path.read_bytes()
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows[1]["message"]["usage"] = value
    source_info = source.stat()
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    os.utime(source, ns=(source_info.st_atime_ns, source_info.st_mtime_ns + 1_000_000_000))

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        assert path.read_bytes() == measured
        assert _tokens() == [(10, 5)]
        assert "kept the archived copy and its usage" in _text(state.stderr)
        assert "private-invalid-container" not in _text(state.stderr)


def test_sync_recaptures_version_five_user_text_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fmind_dot.archive.sync import _source_signature

    state, source = source_session(tmp_path, monkeypatch)
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows[0]["message"]["content"] = [{"type": "text", "text": "fixture"}]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    parsed = parsers.parse_claude_session(source, "fixture-id")
    assert parsed.usage is not None
    with monkeypatch.context() as legacy:
        legacy.setattr(session_store, "SESSION_PARSER_VERSION", "5")
        session_store.ingest_session(
            "claude",
            "fixture-id",
            [record for record in parsed.logs if record.role == "assistant"],
            session_store.SessionSource(
                type=parsed.source_type,
                fingerprint=parsed.fingerprint,
                signature=_source_signature([source])[0],
            ),
            usage=parsed.usage.to_dict(),
        )
    assert load_usage_records()[0].legacy_accounting

    result = sync_sessions(state, agent="claude")

    manifest, records = read_session_bundle(session_bundle_path("claude", "fixture-id"))
    assert result.ingested == 1
    assert manifest.parser_version != "5"
    assert [record.content for record in records] == ["fixture", "response answer-1"]
    assert not load_usage_records()[0].legacy_accounting


def test_new_session_with_failed_usage_archives_its_transcript_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    source.write_text(source.read_text().replace('"input_tokens": 10', '"input_tokens": -1'))

    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")

    assert "archived the transcript without usage" in _text(state.stderr)
    assert read_session_manifest(session_bundle_path("claude", "fixture-id")).usage is None
    assert load_usage_records() == []
    source.write_text(source.read_text().replace('"input_tokens": -1', '"input_tokens": 10'))
    sync_sessions(state, agent="claude")
    assert _tokens() == [(10, 5)]


def test_incremental_sync_skips_unchanged_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    adapter = parsers.AGENT_ADAPTERS["claude"]
    parsed: list[str] = []

    def counting(path: Path, session_id: str, cwd: str = "") -> parsers.ParsedSession:
        parsed.append(session_id)
        return adapter.parser(path, session_id, cwd)

    monkeypatch.setitem(parsers.AGENT_ADAPTERS, "claude", replace(adapter, parser=counting))

    first = sync_sessions(state, agent="claude")
    second = sync_sessions(state, agent="claude")
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))
    third = sync_sessions(state, agent="claude")

    assert (first.selected, first.ingested) == (1, 1)
    assert (second.selected, second.unchanged, second.ingested) == (0, 1, 0)
    assert (third.selected, third.ingested) == (1, 1)
    # The unchanged source was recognized by its size and modification time, without parsing.
    assert parsed == ["fixture-id", "fixture-id"]


def test_corrupt_bundle_fails_sync_and_usage_without_modification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    path.write_text("{}\n")

    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")
    with pytest.raises(ValueError, match="unsupported session format"):
        load_usage_records()
    assert path.read_text() == "{}\n"


def test_recent_grok_signals_update_an_unchanged_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "grok"
    directory = root / "project/session-1"
    directory.mkdir(parents=True)
    transcript = directory / GROK_TRANSCRIPT_NAME
    transcript.write_text("")
    signals = directory / "signals.json"
    signals.write_text(json.dumps({"contextTokensUsed": 21}))
    state = State(stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    state.config.agent.sources["grok"] = str(root)
    sync_sessions(state, agent="grok")
    before = datetime(2026, 9, 1, tzinfo=UTC).timestamp()
    after = datetime(2026, 9, 3, tzinfo=UTC).timestamp()
    os.utime(transcript, (before, before))
    signals.write_text(json.dumps({"contextTokensUsed": 42}))
    os.utime(signals, (after, after))

    sync_sessions(state, agent="grok", since=datetime(2026, 9, 2, tzinfo=UTC))

    assert len(query_session_summaries()) == 1
    assert [record.total_tokens for record in load_usage_records()] == [42]


@pytest.mark.parametrize(
    ("field", "version"), [("schema_version", 2), ("schema_version", 999), ("parser_version", "2")]
)
def test_active_store_rejects_other_formats_without_modification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, version: int | str
) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    header, rest = path.read_bytes().split(b"\n", 1)
    value = json.loads(header)
    value[field] = version
    path.write_bytes(json.dumps(value).encode() + b"\n" + rest)
    before = path.read_bytes()
    for operation in (query_session_summaries, load_usage_records):
        with pytest.raises(ValueError, match="unsupported session format; recapture available sources"):
            operation()
    assert path.read_bytes() == before


@pytest.mark.parametrize("command", [["session", "list", "--json"], ["stats", "--tokens-only", "--json"]])
def test_public_queries_report_unsupported_store_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: list[str]
) -> None:
    import sys

    from fmind_dot.cli import main

    state, _ = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    header, rest = path.read_bytes().split(b"\n", 1)
    path.write_bytes(json.dumps(json.loads(header) | {"schema_version": 1}).encode() + b"\n" + rest)
    monkeypatch.setattr(sys, "argv", ["dot", "agent", *command])
    with pytest.raises(SystemExit) as result:
        main()
    captured = capsys.readouterr()
    assert result.value.code == 1
    assert captured.out == ""
    assert "unsupported session format" in captured.err
    assert "dot agent session sync" in captured.err
    assert "Traceback" not in captured.err


# --- retired v2 store ---------------------------------------------------------------------------------------------


def _v2_store(home: Path) -> dict[Path, bytes]:
    """Write a stand-in for the retired v2 layout and return its exact content."""
    manifest = home / ".agents/sessions/v2/claude/lineage/generation/manifest.json"
    manifest.parent.mkdir(parents=True, mode=0o700)
    manifest.write_text('{"schema_version": 2}\n')
    return _snapshot(home / ".agents/sessions/v2")


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def test_retired_v2_store_fails_closed_without_modifying_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    before = _v2_store(tmp_path)

    with pytest.raises(DotError, match=r"sessions/v2 predates sessions/v3; migrate it once with dot v7\.0\.4"):
        sync_sessions(state, agent="claude")

    assert not session_store_root().exists()
    assert _snapshot(tmp_path / ".agents/sessions/v2") == before


def test_existing_v3_store_ignores_a_leftover_v2_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    _v2_store(tmp_path)

    assert ensure_session_store() == session_store_root()
    assert [summary.session_id for summary in query_session_summaries()] == ["fixture-id"]


def test_dry_run_does_not_touch_a_retired_v2_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    _v2_store(tmp_path)
    before = _snapshot(tmp_path)

    outcome = sync_sessions(state, agent="claude", dry_run=True)

    assert outcome.selected == 1
    assert not session_store_root().exists()
    assert _snapshot(tmp_path) == before


def test_concurrent_sync_never_replaces_a_longer_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    state, source = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    adapter = parsers.AGENT_ADAPTERS["claude"]
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))
    shorter = adapter.parser(source, "fixture-id", "")
    with source.open("a") as stream:
        stream.write(_answer("answer-3", "2026-09-01T10:03:00Z", 30, 9))
    longer = adapter.parser(source, "fixture-id", "")
    assert shorter.usage is not None
    assert longer.usage is not None
    short_ready, long_written = Event(), Event()
    write = session_store.write_private_file

    def delayed_write(path: Path, content: bytes) -> None:
        count = json.loads(content.split(b"\n", 1)[0])["record_count"]
        if count == 3:
            short_ready.set()
            long_written.wait(timeout=_RACE_WINDOW_SECONDS)
        write(path, content)
        if count == 4:
            long_written.set()

    monkeypatch.setattr(session_store, "write_private_file", delayed_write)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(
            session_store.ingest_session, "claude", "fixture-id", shorter.logs, usage=shorter.usage.to_dict()
        )
        assert short_ready.wait(timeout=5)
        latest = pool.submit(
            session_store.ingest_session, "claude", "fixture-id", longer.logs, usage=longer.usage.to_dict()
        )
        pending.result(timeout=5)
        latest.result(timeout=5)
    assert read_session_manifest(session_bundle_path("claude", "fixture-id")).record_count == 4
