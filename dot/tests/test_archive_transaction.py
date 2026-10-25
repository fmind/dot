"""Observable capture, replacement, and usage selection contracts."""

import io
import json
import os
import sqlite3
import time
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import IO, Any

import pytest

from fmind_dot.archive import parsers
from fmind_dot.archive import store as session_store
from fmind_dot.archive.query import SessionQuery, query_session_summaries
from fmind_dot.archive.store import (
    read_session_bundle,
    read_session_manifest,
    session_bundle_path,
)
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import iter_usage_records
from fmind_dot.errors import DotError
from fmind_dot.state import State

# Once the second writer waits on the lock, a correct lock always exhausts this window.
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


def source_session(tmp_path: Path) -> tuple[State, Path]:
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
    return [(record.input_tokens, record.output_tokens) for record in list(iter_usage_records())]


def test_failed_publication_leaves_no_bundle_and_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path)

    def fail(_path: Path, _content: bytes) -> None:
        raise OSError("synthetic write failure")

    with monkeypatch.context() as failure:
        failure.setattr(session_store, "write_private_file", fail)
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
    assert "synthetic write failure" in _text(state.stderr)
    assert query_session_summaries() == []
    assert list(iter_usage_records()) == []

    sync_sessions(state, agent="claude")
    sync_sessions(state, agent="claude")
    assert len(query_session_summaries()) == 1
    assert _tokens() == [(10, 5)]


def test_latest_copy_grows_with_its_source_and_survives_source_removal(tmp_path: Path) -> None:
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))

    sync_sessions(state, agent="claude")
    source.unlink()
    sync_sessions(state, agent="claude")

    [summary] = query_session_summaries(SessionQuery(agent="claude"))
    assert summary.record_count == 3
    assert _tokens() == [(30, 12)]


def test_sync_lists_ingested_sessions_only_when_verbose(tmp_path: Path) -> None:
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    assert "agent-session: ingested" not in _text(state.stderr)
    assert "claude: 1 ingested, 0 unchanged, 0 retained" in _text(state.stderr)
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))

    sync_sessions(state, agent="claude", verbose=True)

    assert "agent-session: ingested claude records=3" in _text(state.stderr)


def test_truncated_source_never_shrinks_the_archived_copy(tmp_path: Path) -> None:
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    source.write_text(json.dumps({"type": "user", "message": {"content": "rotated"}}) + "\n")

    sync_sessions(state, agent="claude")

    assert "agent-session: retained claude records=2" in _text(state.stderr)
    _, records = read_session_bundle(session_bundle_path("claude", "fixture-id"))
    assert [record.content for record in records] == ["fixture", "response answer-1"]
    assert _tokens() == [(10, 5)]


@pytest.mark.skipif(os.geteuid() == 0, reason="Root bypasses owner directory permissions")
@pytest.mark.parametrize("quiet", [False, True])
def test_unreadable_archive_preserves_capture_and_syncs_later_agents(tmp_path: Path, quiet: bool) -> None:
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    before = path.read_bytes()
    source.write_text(json.dumps({"type": "user", "message": {"content": "rotated"}}) + "\n")
    # Copilot syncs after Claude: one unreadable agent archive must not stop it.
    later = tmp_path / "copilot.db"
    with closing(sqlite3.connect(later)) as connection:
        connection.executescript(
            """CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
            CREATE TABLE turns(id INTEGER, session_id TEXT, turn_index INTEGER, user_message TEXT,
                assistant_response TEXT, timestamp TEXT);
            CREATE TABLE assistant_usage_events(session_id TEXT, model TEXT, input_tokens INTEGER,
                output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);
            INSERT INTO sessions VALUES('later', '', '2026-09-01T10:00:00Z');
            INSERT INTO turns VALUES(1, 'later', 1, 'later', '', '2026-09-01T10:00:00Z');"""
        )
    state.config.agent.sources["copilot"] = str(later)
    path.parent.chmod(0)
    try:
        if quiet:
            outcome = sync_sessions(state, quiet=True)
            assert (outcome.failed, outcome.ingested) == (1, 1)
        else:
            with pytest.raises(DotError, match="1 failure"):
                sync_sessions(state)
        assert "failed to inspect the session archive for Claude" in _text(state.stderr)
    finally:
        path.parent.chmod(0o700)
    assert path.read_bytes() == before
    assert read_session_bundle(session_bundle_path("copilot", "later"))[1][0].content == "later"


def test_usage_error_keeps_the_last_measurement_and_grows_the_transcript(tmp_path: Path) -> None:
    """Regression for 2b5fbbd: a failed extraction must never cost the measured usage."""
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", -1, 7))

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        assert "usage extraction failed; kept the archived usage" in _text(state.stderr)
        assert read_session_manifest(path).record_count == 3
        assert _tokens() == [(10, 5)]

    # Once the source measures again, the longer transcript and its usage replace the copy.
    source.write_text(source.read_text().replace('"input_tokens": -1', '"input_tokens": 20'))
    sync_sessions(state, agent="claude")
    assert read_session_manifest(path).record_count == 3
    assert _tokens() == [(30, 12)]


def test_malformed_line_never_freezes_the_transcript(tmp_path: Path) -> None:
    """A persistent malformed record keeps the measurement but still archives later messages."""
    state, source = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    with source.open("a") as stream:
        stream.write("{\n")
    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")
    assert "malformed source records; kept the archived usage" in _text(state.stderr)
    with source.open("a") as stream:
        stream.write(_answer("answer-2", "2026-09-01T10:02:00Z", 20, 7))

    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")

    manifest, records = read_session_bundle(path)
    assert [record.content for record in records][-1] == "response answer-2"
    assert (manifest.malformed_records, manifest.completeness, manifest.source_signature) == (1, "partial", "")
    assert _tokens() == [(10, 5)]


_INVALID_METRICS = ["private-invalid-metric", True, [], {}]
_INVALID_CONTAINERS = [[], "private-invalid-container", True, 1]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        *(("input_tokens", value) for value in _INVALID_METRICS),
        *(("cost_usd", value) for value in _INVALID_METRICS),
        *(("usage", value) for value in _INVALID_CONTAINERS),
    ],
)
def test_invalid_usage_keeps_the_last_measured_copy(tmp_path: Path, field: str, value: object) -> None:
    state, source = source_session(tmp_path)
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows.append({"type": "cost-state", "totalCostUSD": 0.25})
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    measured = path.read_bytes()
    if field == "usage":
        rows[1]["message"]["usage"] = value
    elif field == "cost_usd":
        rows[-1]["totalCostUSD"] = value
    else:
        rows[1]["message"]["usage"][field] = value
    source_info = source.stat()
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    # Equal-length replacements must advance mtime even on a coarse-clock filesystem.
    os.utime(source, ns=(source_info.st_atime_ns, source_info.st_mtime_ns + 1_000_000_000))

    for _ in range(2):
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent="claude")
        assert path.read_bytes() == measured
        assert _tokens() == [(10, 5)]
        assert "usage extraction failed; kept the archived usage" in _text(state.stderr)
        assert "private-invalid" not in _text(state.stderr)


def test_sync_recaptures_older_parser_bundles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fmind_dot.archive.sync import _source_signature

    state, source = source_session(tmp_path)
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows[0]["message"]["content"] = [{"type": "text", "text": "fixture"}]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    parsed = parsers.parse_claude_session(source, "fixture-id")
    assert parsed.usage is not None
    with monkeypatch.context() as legacy:
        legacy.setattr(session_store, "SESSION_PARSER_VERSION", "9")
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

    result = sync_sessions(state, agent="claude")

    manifest, records = read_session_bundle(session_bundle_path("claude", "fixture-id"))
    assert result.ingested == 1
    assert manifest.parser_version == session_store.SESSION_PARSER_VERSION
    assert [record.content for record in records] == ["fixture", "response answer-1"]


def test_sync_recaptures_meta_flags_from_unchanged_parser_13_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fmind_dot.archive.sync import _source_signature

    state, source = source_session(tmp_path)
    with source.open("a") as stream:
        stream.write(json.dumps({"type": "user", "isMeta": True, "message": {"content": "injected skill"}}) + "\n")
    parsed = parsers.parse_claude_session(source, "fixture-id")
    assert parsed.usage is not None
    with monkeypatch.context() as legacy:
        legacy.setattr(session_store, "SESSION_PARSER_VERSION", "13")
        session_store.ingest_session(
            "claude",
            "fixture-id",
            [replace(record, meta=False) for record in parsed.logs],
            session_store.SessionSource(
                type=parsed.source_type,
                fingerprint=parsed.fingerprint,
                signature=_source_signature([source])[0],
            ),
            usage=parsed.usage.to_dict(),
        )
    path = session_bundle_path("claude", "fixture-id")
    old_manifest, old_records = read_session_bundle(path)
    assert old_manifest.parser_version == "13"
    assert all(not record.meta for record in old_records)

    assert sync_sessions(state, agent="claude").ingested == 1
    manifest, records = read_session_bundle(path)
    assert manifest.schema_version == session_store.SESSION_SCHEMA_VERSION
    assert manifest.parser_version == session_store.SESSION_PARSER_VERSION
    assert records == parsed.logs
    assert manifest.usage == old_manifest.usage
    # Records start after the manifest and usage lines.
    assert [json.loads(line).get("meta") for line in path.read_text().splitlines()[2:]] == [None, None, True]
    assert sync_sessions(state, agent="claude").unchanged == 1


def test_new_session_with_failed_usage_archives_its_transcript_and_retries(tmp_path: Path) -> None:
    state, source = source_session(tmp_path)
    source.write_text(source.read_text().replace('"input_tokens": 10', '"input_tokens": -1'))

    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")

    assert "archived the transcript without usage" in _text(state.stderr)
    assert read_session_manifest(session_bundle_path("claude", "fixture-id")).usage is None
    assert list(iter_usage_records()) == []
    source.write_text(source.read_text().replace('"input_tokens": -1', '"input_tokens": 10'))
    sync_sessions(state, agent="claude")
    assert _tokens() == [(10, 5)]


def test_incremental_sync_skips_unchanged_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, source = source_session(tmp_path)
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


def test_corrupt_bundle_fails_sync_and_usage_without_modification(tmp_path: Path) -> None:
    state, _ = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    path.write_text("{}\n")

    with pytest.raises(DotError, match="1 failure"):
        sync_sessions(state, agent="claude")
    with pytest.raises(ValueError, match="unsupported session format"):
        list(iter_usage_records())
    assert path.read_text() == "{}\n"


@pytest.mark.parametrize(
    ("field", "version", "message"),
    [
        ("schema_version", 2, "unsupported session format; recapture available sources"),
        ("schema_version", 999, "written by a newer dot; install that dot version"),
        ("parser_version", "2", "unsupported session format; recapture available sources"),
        ("parser_version", "999", "written by a newer dot; install that dot version"),
    ],
)
def test_active_store_rejects_other_formats_without_modification(
    tmp_path: Path, field: str, version: int | str, message: str
) -> None:
    state, _ = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    header, rest = path.read_bytes().split(b"\n", 1)
    value = json.loads(header)
    value[field] = version
    path.write_bytes(json.dumps(value).encode() + b"\n" + rest)
    before = path.read_bytes()
    for operation in (query_session_summaries, lambda: list(iter_usage_records())):
        with pytest.raises(ValueError, match=message):
            operation()
    assert path.read_bytes() == before


@pytest.mark.parametrize("command", [["session", "list", "--json"], ["stats", "--tokens-only", "--json"]])
def test_public_queries_report_unsupported_store_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: list[str]
) -> None:
    import sys

    from fmind_dot.cli import main

    state, _ = source_session(tmp_path)
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


def test_concurrent_sync_never_replaces_a_longer_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    state, source = source_session(tmp_path)
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
    short_ready, long_waiting, long_written = Event(), Event(), Event()
    write = session_store.write_private_file
    flock = session_store.fcntl.flock

    def observed_flock(stream: IO[bytes], operation: int) -> None:
        # While the shorter writer holds the lock, any exclusive request is the longer writer's.
        if operation == session_store.fcntl.LOCK_EX and short_ready.is_set():
            long_waiting.set()
        flock(stream, operation)

    def delayed_write(path: Path, content: bytes) -> None:
        count = json.loads(content.split(b"\n", 1)[0])["record_count"]
        if count == 3:
            short_ready.set()
            # Hold the lock until the longer writer contends for it (or, with a broken lock, writes),
            # so a loaded host cannot let the test pass without exercising the lock.
            deadline = time.monotonic() + 30
            while not (long_waiting.is_set() or long_written.is_set()) and time.monotonic() < deadline:
                time.sleep(0.005)
            long_written.wait(timeout=_RACE_WINDOW_SECONDS)
        write(path, content)
        if count == 4:
            long_written.set()

    monkeypatch.setattr(session_store, "write_private_file", delayed_write)
    monkeypatch.setattr(session_store.fcntl, "flock", observed_flock)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(
            session_store.ingest_session, "claude", "fixture-id", shorter.logs, usage=shorter.usage.to_dict()
        )
        assert short_ready.wait(timeout=5)
        latest = pool.submit(
            session_store.ingest_session, "claude", "fixture-id", longer.logs, usage=longer.usage.to_dict()
        )
        pending.result(timeout=30)
        latest.result(timeout=30)
    assert long_waiting.is_set()
    assert read_session_manifest(session_bundle_path("claude", "fixture-id")).record_count == 4


def test_unavailable_usage_publishes_new_turns_and_retains_the_measurement(tmp_path: Path) -> None:
    state, path = source_session(tmp_path)
    rows: list[dict[str, Any]] = [
        {"type": "user", "timestamp": "2026-09-18T10:00:00Z", "message": {"content": "Keep this owner request"}},
        json.loads(_answer("answer-1", "2026-09-18T10:00:30Z", 10, 1)),
        # A response without counters leaves the whole session measurement unavailable.
        {
            "type": "assistant",
            "timestamp": "2026-09-18T10:01:00Z",
            "message": {"id": "answer-2", "model": "fixture", "content": [{"type": "text", "text": "response"}]},
        },
    ]

    def write(usage: dict[str, int] | None) -> None:
        if usage is None:
            rows[-1]["message"].pop("usage", None)
        else:
            rows[-1]["message"]["usage"] = usage
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    write(None)
    sync_sessions(state, agent="claude")
    bundle = session_bundle_path("claude", "fixture-id")
    manifest, records = read_session_bundle(bundle)
    assert manifest.usage is None
    assert manifest.completeness == "complete"
    assert records[0].content == "Keep this owner request"
    # A complete measurement can later replace the unavailable one.
    write({"input_tokens": 100, "output_tokens": 2})
    sync_sessions(state, agent="claude")
    measured = bundle.read_bytes()
    assert read_session_manifest(bundle).usage is not None
    write(None)
    outcome = sync_sessions(state, agent="claude")
    assert bundle.read_bytes() == measured
    assert (outcome.retained, outcome.ingested) == (1, 0)
    rows[0]["message"]["content"] += " with a new instruction"
    write(None)
    outcome = sync_sessions(state, agent="claude")
    # New turns publish; the measurement the source can no longer provide stays, marked as retained.
    manifest, records = read_session_bundle(bundle)
    assert records[0].content == "Keep this owner request with a new instruction"
    assert manifest.usage == json.loads(measured.split(b"\n")[1])
    assert (manifest.usage_parser_version, manifest.source_signature) == (manifest.parser_version, "")
    assert (outcome.retained, outcome.ingested) == (1, 0)
    # Sync retries the source without rewriting a current transcript.
    published = bundle.read_bytes()
    assert sync_sessions(state, agent="claude").retained == 1
    assert bundle.read_bytes() == published
    # A complete measurement measures the session again.
    write({"input_tokens": 100, "output_tokens": 2})
    assert sync_sessions(state, agent="claude").ingested == 1
    manifest = read_session_manifest(bundle)
    assert manifest.usage_parser_version == ""
    assert manifest.source_signature
    assert [record.input_tokens for record in list(iter_usage_records())] == [110]


def test_quiet_sync_announces_a_parser_upgrade_once(tmp_path: Path) -> None:
    state, _ = source_session(tmp_path)
    sync_sessions(state, agent="claude")
    path = session_bundle_path("claude", "fixture-id")
    header, rest = path.read_bytes().split(b"\n", 1)
    path.write_bytes(json.dumps(json.loads(header) | {"parser_version": "13"}).encode() + b"\n" + rest)
    state.stderr = io.StringIO()

    assert sync_sessions(state, agent="claude", quiet=True).ingested == 1
    assert sync_sessions(state, agent="claude", quiet=True).unchanged == 1

    assert isinstance(state.stderr, io.StringIO)
    assert state.stderr.getvalue() == (
        f"agent-session: upgrading archived claude sessions to parser {session_store.SESSION_PARSER_VERSION}; "
        "this can take minutes\n"
    )
