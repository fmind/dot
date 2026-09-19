"""Observable capture, replacement, migration, and usage selection contracts."""

import hashlib
import io
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

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
from fmind_dot.archive.usage import UsageRecord, load_usage_records
from fmind_dot.errors import DotError
from fmind_dot.state import State


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


# --- v2 migration -------------------------------------------------------------------------------------------------


def _digest(*values: str) -> str:
    return hashlib.sha256("".join(f"{value}\0" for value in values).encode()).hexdigest()


def _usage(agent: str, session_id: str, tokens: int) -> dict[str, Any]:
    return (
        UsageRecord(timestamp="2026-09-01T10:00:00Z", harness=agent, session_id=session_id, input_tokens=tokens)
        .finalize()
        .to_dict()
    )


def _v2_generation(
    home: Path,
    session_id: str,
    *,
    records: int,
    ingested_at: str,
    usage: int | None = None,
    parser: str = "5",
    agent: str = "claude",
    corrupt: bool = False,
    schema: int = 2,
) -> Path:
    """Write one generation exactly as the v2 writer laid it out."""
    fingerprint = _digest(session_id, str(records), ingested_at)
    lineage = _digest(agent, session_id)
    path = home / ".agents/sessions/v2" / agent / lineage / _digest(parser, fingerprint)
    path.mkdir(parents=True, mode=0o700)
    transcript = b"".join(
        json.dumps(
            {
                "ts": f"2026-09-01T10:0{index}:00Z",
                "agent": agent,
                "sid": session_id,
                "role": "user",
                "content": f"m{index}",
            }
        ).encode()
        + b"\n"
        for index in range(records)
    )
    usage_document = {
        "schema": "dot.session.usage/v1",
        "status": "available" if usage is not None else "unsupported",
        "record": _usage(agent, session_id, usage) if usage is not None else None,
    }
    usage_content = (json.dumps(usage_document) + "\n").encode()
    manifest = {
        "parser_version": parser,
        "agent": agent,
        "session_id": session_id,
        "lineage_id": lineage,
        "source_type": "claude-jsonl",
        "source_fingerprint": fingerprint,
        "high_water_mark": f"2026-09-01T10:0{records - 1}:00Z",
        "ingested_at": ingested_at,
        "completeness": "complete",
        "transcript_sha256": hashlib.sha256(transcript).hexdigest(),
        "schema_version": schema,
        "record_count": records,
        "malformed_records": 0,
        "skipped_records": 0,
        "usage_sha256": hashlib.sha256(usage_content).hexdigest(),
    }
    (path / "transcript.jsonl").write_bytes(transcript + (b"tampered\n" if corrupt else b""))
    (path / "usage.json").write_bytes(usage_content)
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def test_migration_keeps_the_longest_generation_with_its_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _v2_generation(tmp_path, "grown", records=1, ingested_at="2026-09-01T10:00:00Z", usage=10)
    _v2_generation(tmp_path, "grown", records=3, ingested_at="2026-09-02T10:00:00Z", usage=30)
    _v2_generation(tmp_path, "grown", records=2, ingested_at="2026-09-03T10:00:00Z", usage=20)
    _v2_generation(tmp_path, "tied", records=2, ingested_at="2026-09-01T10:00:00Z", usage=1, parser="4")
    _v2_generation(tmp_path, "tied", records=2, ingested_at="2026-09-02T10:00:00Z", usage=2)
    legacy = tmp_path / ".agents/sessions/v2"
    before = _snapshot(legacy)
    report = io.StringIO()

    root = ensure_session_store(report)

    assert "migrated 2 sessions from sessions/v2 to sessions/v3 (0 unreadable generations skipped)" in report.getvalue()
    grown = read_session_manifest(root / "claude/grown.jsonl")
    assert (grown.record_count, grown.ingested_at, grown.source_signature) == (3, "2026-09-02T10:00:00Z", "")
    assert [log.content for log in read_session_bundle(root / "claude/grown.jsonl")[1]] == ["m0", "m1", "m2"]
    assert read_session_manifest(root / "claude/tied.jsonl").ingested_at == "2026-09-02T10:00:00Z"
    assert sorted((record.session_id, record.input_tokens) for record in load_usage_records()) == [
        ("grown", 30),
        ("tied", 2),
    ]
    # v2 is never modified; repeated access neither re-migrates nor rewrites v3.
    after = _snapshot(root)
    assert ensure_session_store(report) == root
    assert _snapshot(legacy) == before
    assert _snapshot(root) == after
    assert report.getvalue().count("migrated") == 1


def test_migration_carries_earlier_usage_when_the_longest_generation_has_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _v2_generation(tmp_path, "session", records=1, ingested_at="2026-09-01T10:00:00Z", usage=10, parser="4")
    _v2_generation(tmp_path, "session", records=2, ingested_at="2026-09-02T10:00:00Z", usage=12)
    _v2_generation(tmp_path, "session", records=3, ingested_at="2026-09-03T10:00:00Z", usage=None)

    ensure_session_store()

    assert read_session_manifest(session_bundle_path("claude", "session")).record_count == 3
    assert [record.input_tokens for record in load_usage_records()] == [12]


def test_migration_skips_unreadable_generations_and_legacy_parsers_stay_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _v2_generation(tmp_path, "session", records=2, ingested_at="2026-09-01T10:00:00Z", usage=5, parser="4")
    _v2_generation(tmp_path, "session", records=3, ingested_at="2026-09-02T10:00:00Z", usage=9, corrupt=True)
    _v2_generation(tmp_path, "unsupported", records=1, ingested_at="2026-09-01T10:00:00Z", schema=1)
    report = io.StringIO()

    ensure_session_store(report)

    assert "migrated 1 sessions" in report.getvalue()
    assert "(1 unreadable generations skipped)" in report.getvalue()
    [summary] = query_session_summaries()
    assert (summary.record_count, summary.status) == (2, ["legacy"])
    [record] = load_usage_records()
    assert (record.input_tokens, record.legacy_accounting) == (5, True)


def test_existing_v3_store_is_never_replaced_by_migration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    sync_sessions(state, agent="claude")
    _v2_generation(tmp_path, "legacy-only", records=4, ingested_at="2026-09-01T10:00:00Z", usage=1)

    assert ensure_session_store() == session_store_root()
    assert [summary.session_id for summary in query_session_summaries()] == ["fixture-id"]


def test_sync_recaptures_migrated_sessions_from_available_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    _v2_generation(tmp_path, "fixture-id", records=2, ingested_at="2026-09-01T10:00:00Z", usage=99, parser="4")
    retired = tmp_path / ".agents/sessions/v1/claude/fixture.json"
    retired.parent.mkdir(parents=True)
    retired.write_text("{}")

    outcome = sync_sessions(state, agent="claude")

    assert (outcome.selected, outcome.ingested) == (1, 1)
    [summary] = query_session_summaries()
    assert (summary.parser_version, summary.status) == ("5", ["current"])
    assert _tokens() == [(10, 5)]
    assert retired.read_text() == "{}"
