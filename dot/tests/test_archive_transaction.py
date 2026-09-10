"""Observable archive recovery, migration, and usage selection contracts."""

import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fmind_dot.archive import ingest as archive_ingest_module
from fmind_dot.archive import store as session_store
from fmind_dot.archive.parsers import GROK_TRANSCRIPT_NAME
from fmind_dot.archive.query import SessionQuery, query_session_summaries
from fmind_dot.archive.usage import load_usage_records
from fmind_dot.state import State


def source_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[State, Path]:
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / "claude"
    source.mkdir()
    transcript = source / "fixture-id.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "timestamp": "2026-09-01T10:00:00Z", "message": {"content": "fixture"}})
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "timestamp": "2026-09-01T10:01:00Z",
                "message": {
                    "id": "answer-1",
                    "model": "fixture",
                    "content": [{"type": "text", "text": "response"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            }
        )
        + "\n"
    )
    state = State(stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    state.config.agent.sources["claude"] = str(source)
    return state, transcript


def test_failed_usage_publication_retries_the_whole_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    original = session_store._write_owner_only_at  # noqa: SLF001 - inject a failure before atomic publication.

    def fail_usage(directory: int, name: str, content: bytes) -> None:
        if name == "usage.json":
            raise OSError("synthetic usage write failure")
        original(directory, name, content)

    with monkeypatch.context() as failure:
        failure.setattr(session_store, "_write_owner_only_at", fail_usage)
        with pytest.raises(OSError, match="synthetic usage write failure"):
            archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    assert query_session_summaries() == []
    assert load_usage_records() == []
    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    assert len(query_session_summaries()) == 1
    usage = load_usage_records()
    assert len(usage) == 1
    assert usage[0].input_tokens == 10
    assert usage[0].output_tokens == 5
    assert not (tmp_path / ".agents/usages").exists()


def test_usage_survives_source_removal_and_counts_latest_generation_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    with source.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "type": "assistant",
                    "timestamp": "2026-09-01T10:02:00Z",
                    "message": {
                        "id": "answer-2",
                        "model": "fixture",
                        "content": [{"type": "text", "text": "more"}],
                        "usage": {"input_tokens": 20, "output_tokens": 7},
                    },
                }
            )
            + "\n"
        )
    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    source.unlink()
    assert len(query_session_summaries(SessionQuery(agent="claude"))) == 2
    usage = load_usage_records()
    assert len(usage) == 1
    assert usage[0].input_tokens == 30
    assert usage[0].output_tokens == 12


def test_corrupt_usage_rejects_duplicate_and_statistics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _ = source_session(tmp_path, monkeypatch)
    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    usage_path = next((tmp_path / ".agents/sessions").rglob("usage.json"))
    usage_path.write_text("{}")
    with pytest.raises(ValueError, match="usage"):
        archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")
    with pytest.raises(ValueError, match="usage"):
        load_usage_records()


def test_schema_one_archive_remains_unchanged_during_parser_three_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, source = source_session(tmp_path, monkeypatch)
    fingerprint = session_store.fingerprint_bytes(source.read_bytes())
    lineage = session_store.session_lineage_id("claude", "fixture-id")
    generation = session_store.session_digest("2", fingerprint)
    legacy = session_store.session_store_root() / "claude" / lineage / generation
    legacy.mkdir(parents=True, mode=0o700)
    for directory in (legacy, *legacy.parents):
        if directory == tmp_path:
            break
        directory.chmod(0o700)
    transcript = (
        b'{"timestamp":"2026-09-01T10:00:00Z","agent":"claude","session_id":"fixture-id",'
        b'"role":"user","content":"fixture \\u003cold\\u003e"}\n'
    )
    manifest = {
        "schema_version": 1,
        "parser_version": "2",
        "agent": "claude",
        "session_id": "fixture-id",
        "lineage_id": lineage,
        "source_type": "claude-jsonl",
        "source_fingerprint": fingerprint,
        "high_water_mark": "2026-09-01T10:00:00Z",
        "ingested_at": "2026-09-01T10:01:00Z",
        "completeness": "complete",
        "transcript_sha256": session_store.fingerprint_bytes(transcript),
        "record_count": 1,
        "malformed_records": 0,
        "skipped_records": 0,
    }
    for name, content in {"manifest.json": json.dumps(manifest).encode(), "transcript.jsonl": transcript}.items():
        path = legacy / name
        path.write_bytes(content)
        path.chmod(0o600)
    usage_path = tmp_path / ".agents/usages/claude/fixture-id.json"
    usage_path.parent.mkdir(parents=True)
    usage_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-09-01T10:01:00Z",
                "harness": "claude",
                "agent": "claude",
                "session_id": "fixture-id",
                "input_tokens": 999,
            }
        )
    )
    before = {path: path.read_bytes() for path in (*legacy.iterdir(), usage_path)}
    assert len(query_session_summaries()) == 1
    assert load_usage_records()[0].input_tokens == 999

    archive_ingest_module.ingest_agent_session(state, "claude", "fixture-id")

    summaries = query_session_summaries()
    assert len(summaries) == 2
    assert {item.generation_id for item in summaries} == {generation, session_store.session_digest("3", fingerprint)}
    assert load_usage_records()[0].input_tokens == 10
    assert all(path.read_bytes() == content for path, content in before.items())
    assert {path.name for path in legacy.iterdir()} == {"manifest.json", "transcript.jsonl"}


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
    archive_ingest_module.sync_sessions(state, agent="grok")
    before = datetime(2026, 9, 1, tzinfo=UTC).timestamp()
    after = datetime(2026, 9, 3, tzinfo=UTC).timestamp()
    os.utime(transcript, (before, before))
    signals.write_text(json.dumps({"contextTokensUsed": 42}))
    os.utime(signals, (after, after))

    archive_ingest_module.sync_sessions(state, agent="grok", since=datetime(2026, 9, 2, tzinfo=UTC))

    assert len(query_session_summaries()) == 2
    assert [record.total_tokens for record in load_usage_records()] == [42]
