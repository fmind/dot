"""OpenCode transcripts join the shared archive without treating tools as user input."""

import io
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from fmind_dot.archive.parsers import enumerate_sessions, parse_opencode_session
from fmind_dot.archive.store import ingest_session, read_session_bundle, session_bundle_path
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.config import Config
from fmind_dot.process import Runner
from fmind_dot.state import State


def database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE session (id TEXT, directory TEXT);
            CREATE TABLE message (id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
            CREATE TABLE part (id TEXT, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
            INSERT INTO session VALUES ('ses_test', '/work/project');
        """)
        for index, role in enumerate(("user", "assistant")):
            db.execute(
                "INSERT INTO message VALUES (?, 'ses_test', ?, ?)",
                (f"msg_{index}", 1780000000000 + index, json.dumps({"role": role})),
            )
        for index, part in enumerate(
            (
                {"type": "text", "text": "owner request"},
                {"type": "text", "text": "injected", "synthetic": True},
                {"type": "tool", "text": "tool result"},
                {"type": "text", "text": "ignored", "ignored": True},
            )
        ):
            db.execute("INSERT INTO part VALUES (?, 'msg_0', 'ses_test', ?, ?)", (str(index), index, json.dumps(part)))
        db.execute(
            "INSERT INTO part VALUES ('reply', 'msg_1', 'ses_test', 10, ?)",
            (json.dumps({"type": "text", "text": "assistant reply"}),),
        )


def test_opencode_discovery_projection_and_shared_archive(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / "opencode.db"
    database(path)
    assert enumerate_sessions(path, "opencode") == [("ses_test", "/work/project", path)]
    parsed = parse_opencode_session(path, "ses_test")
    assert [log.content for log in parsed.logs] == ["owner request", "assistant reply"]
    assert parsed.usage is None
    assert parsed.usage_error is None
    ingest_session("opencode", "ses_test", parsed.logs)
    manifest, logs = read_session_bundle(session_bundle_path("opencode", "ses_test"))
    assert manifest.agent == "opencode"
    assert [log.role for log in logs] == ["user", "assistant"]


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE part SET data = 'broken' WHERE id = '0'",
        "UPDATE part SET message_id = 'missing' WHERE id = '0'",
        "UPDATE message SET time_created = -1 WHERE id = 'msg_0'",
    ],
)
def test_opencode_rejects_incomplete_sources(tmp_path, mutation) -> None:
    path = tmp_path / "opencode.db"
    database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match=r"Expecting|OpenCode"):
        parse_opencode_session(path, "ses_test")


def test_opencode_summary_is_not_an_owner_request(tmp_path) -> None:
    path = tmp_path / "opencode.db"
    database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE message SET data = ? WHERE id = 'msg_0'", (json.dumps({"role": "user", "summary": True}),))
    assert [log.role for log in parse_opencode_session(path, "ses_test").logs] == ["assistant"]


def test_opencode_sync_catches_wal_updates_and_keeps_user_summary_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".local/share/opencode/opencode.db"
    path.parent.mkdir(parents=True)
    database(path)
    state = State(runner=Runner(), stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    state.__dict__["_config"] = Config()
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            "UPDATE message SET data = ? WHERE id = 'msg_0'",
            (json.dumps({"role": "user", "summary": {"title": "metadata"}}),),
        )
        db.commit()
        assert sync_sessions(state, agent="opencode").ingested == 1
        assert sync_sessions(state, agent="opencode").selected == 0
        db.execute(
            "INSERT INTO message VALUES ('msg_new', 'ses_test', 1780000001000, ?)", (json.dumps({"role": "user"}),)
        )
        db.execute(
            "INSERT INTO part VALUES ('new', 'msg_new', 'ses_test', 20, ?)",
            (json.dumps({"type": "text", "text": "next request"}),),
        )
        db.commit()
        assert sync_sessions(state, agent="opencode").ingested == 1
    _, logs = read_session_bundle(session_bundle_path("opencode", "ses_test"))
    assert [log.content for log in logs if log.role == "user"] == ["owner request", "next request"]


def test_opencode_deeply_nested_part_is_rejected_without_a_crash(tmp_path) -> None:
    path = tmp_path / "opencode.db"
    database(path)
    with closing(sqlite3.connect(path)) as db, db:
        # About a million levels exceed the interpreter stack while decoding.
        db.execute("UPDATE part SET data = ? WHERE id = '0'", ("[" * 1_000_000 + "]" * 1_000_000,))
    with pytest.raises(ValueError, match="OpenCode part"):
        parse_opencode_session(path, "ses_test")


def test_opencode_usage_measures_each_assistant_step(tmp_path: Path) -> None:
    path = tmp_path / "opencode.db"
    database(path)
    step = {
        "role": "assistant",
        "modelID": "claude-sonnet-4-5",
        "cost": 0.25,
        "tokens": {"input": 100, "output": 10, "reasoning": 5, "total": 115, "cache": {"read": 50, "write": 20}},
        "time": {"created": 1780000000100, "completed": 1780000001000},
    }
    summary = step | {"summary": True, "cost": 0.5, "time": {"created": 1780000002000}}
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE message SET data = ? WHERE id = 'msg_1'", (json.dumps(step),))
        db.execute("INSERT INTO message VALUES ('msg_2', 'ses_test', 1780000002000, ?)", (json.dumps(summary),))

    parsed = parse_opencode_session(path, "ses_test")

    assert parsed.usage_error is None
    assert parsed.usage is not None
    usage = parsed.usage.to_dict()
    # Reasoning joins output; the summary is a model call outside the transcript.
    assert (usage["input_tokens"], usage["output_tokens"], usage["reasoning_tokens"]) == (200, 30, 10)
    assert (usage["cached_tokens"], usage["cache_write_tokens"], usage["total_tokens"]) == (100, 40, 370)
    assert (usage["cost_usd"], usage["turn_count"], usage["model"]) == (0.75, 2, "claude-sonnet-4-5")
    assert usage["timestamp"] == "2026-05-28T20:26:42+00:00"
    assert [log.content for log in parsed.logs] == ["owner request", "assistant reply"]


def test_opencode_usage_without_counters_stays_unknown_and_bad_counters_fail(tmp_path: Path) -> None:
    path = tmp_path / "opencode.db"
    database(path)
    assert parse_opencode_session(path, "ses_test").usage is None
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(
            "UPDATE message SET data = ? WHERE id = 'msg_1'",
            (json.dumps({"role": "assistant", "tokens": {"input": -1}}),),
        )
    parsed = parse_opencode_session(path, "ses_test")
    assert parsed.usage is None
    assert isinstance(parsed.usage_error, ValueError)
