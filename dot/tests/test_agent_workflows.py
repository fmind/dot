from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from fmind_dot.archive import sync as sync_module
from fmind_dot.archive.parsers import AGY_SUMMARIES_NAME, ParsedSession
from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SESSION_STORE_VERSION,
    read_session_manifest,
    session_bundle_path,
)
from fmind_dot.archive.sync import (
    SYNC_STATE_NAME,
    SYNC_STATE_SCHEMA,
    bounded_failure,
    read_sync_state,
    sync_sessions,
)
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from tests.fakes import CliRunner, buf, make_state


def _write_agy(home: Path, sid: str, *, project: Path | None = None, malformed: bool = False) -> Path:
    log = home / f".gemini/antigravity-cli/brain/{sid}/.system_generated/logs/transcript_full.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    row = json.dumps(
        {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hi", "created_at": "2026-11-15T00:00:00Z"}
    )
    log.write_text(row + ("\n{bad\n" if malformed else "\n"), encoding="utf-8")
    if project is not None:
        db = home / ".gemini/antigravity-cli" / AGY_SUMMARIES_NAME
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS conversation_summaries(conversation_id TEXT, workspace_uris TEXT)")
            conn.execute("INSERT INTO conversation_summaries VALUES (?, ?)", (sid, json.dumps([project.as_uri()])))
    return log


def test_sync_sessions_incremental_and_claude_subagents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_agy(tmp_path, "agy-1", project=tmp_path / "repo")
    for p in ("p1", "p2"):
        sub = tmp_path / f".claude/projects/w/{p}/subagents/sub-dup.jsonl"
        sub.parent.mkdir(parents=True)
        sub.write_text(
            json.dumps({"type": "user", "timestamp": "2026-11-15T00:00:00Z", "message": {"content": p}}) + "\n",
            encoding="utf-8",
        )
    pi_dir = tmp_path / ".pi/agent/sessions"
    pi_dir.mkdir(parents=True)
    (pi_dir / "2026-11-15_pi-1.jsonl").write_text(
        json.dumps(
            {"type": "message", "timestamp": "2026-11-15T00:00:00Z", "message": {"role": "user", "content": "hello"}}
        )
        + "\n",
        encoding="utf-8",
    )
    cop_db = tmp_path / ".copilot/session-store.db"
    cop_db.parent.mkdir(parents=True)
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions(id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns(id INTEGER PRIMARY KEY, session_id TEXT, turn_index INT, user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events(id INTEGER PRIMARY KEY, session_id TEXT, model TEXT, input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT, created_at TEXT);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-1', ?, '2026-11-15T00:00:00Z')", (str(tmp_path / "repo"),))
        conn.execute(
            "INSERT INTO assistant_usage_events VALUES (1, 'cop-1', 'gpt-6-luna', 100, 20, 80, 0, 0, '2026-11-15T00:01:00Z')"
        )
    oc_db = tmp_path / ".local/share/opencode/opencode.db"
    oc_db.parent.mkdir(parents=True)
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE session_v2(id TEXT PRIMARY KEY, directory TEXT, time_created INT);"
            "CREATE TABLE session_message(id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INT, time_created INT, data TEXT);"
            "CREATE TABLE session_part(message_id TEXT, session_id TEXT, ordinal INT, type TEXT, time_created INT, data TEXT);"
        )
        conn.execute("INSERT INTO session_v2 VALUES ('oc-1', ?, 1000)", (str(tmp_path / "repo"),))
        conn.execute(
            "INSERT INTO session_message VALUES ('m1', 'oc-1', 'assistant', 1, 1000, ?)",
            (
                json.dumps(
                    {
                        "model": {"providerID": "anthropic", "id": "claude-sonnet-4-5"},
                        "tokens": {"input": 10, "output": 5},
                        "cost": 0.01,
                    }
                ),
            ),
        )

    st = make_state()
    out = sync_sessions(st)
    assert out.ingested == 6
    assert out.failed == 0
    assert read_session_manifest(session_bundle_path("agy", "agy-1")).cwd == str(tmp_path / "repo")
    assert len(list((tmp_path / ".agents/sessions" / SESSION_STORE_VERSION / "claude").glob("sub-dup*.jsonl"))) == 2
    assert isinstance(
        read_sync_state(tmp_path / ".agents/sessions" / SESSION_STORE_VERSION, "agy"), sync_module.SyncState
    )
    cop_state = read_sync_state(tmp_path / ".agents/sessions" / SESSION_STORE_VERSION, "copilot")
    assert isinstance(cop_state, sync_module.SyncState)
    assert cop_state.database_signature

    cop1_ingested = read_session_manifest(session_bundle_path("copilot", "cop-1")).ingested_at
    oc1_ingested = read_session_manifest(session_bundle_path("opencode", "oc-1")).ingested_at
    out2 = sync_sessions(make_state())
    assert out2.unchanged == 6

    # Growing shared SQLite DBs with new sessions skips parsing unchanged historical sessions via per-session stamps.
    parsed_sids: list[tuple[str, str]] = []
    cop_orig = sync_module.AGENT_ADAPTERS["copilot"]
    oc_orig = sync_module.AGENT_ADAPTERS["opencode"]
    monkeypatch.setitem(
        sync_module.AGENT_ADAPTERS,
        "copilot",
        replace(cop_orig, parser=lambda p, s, c: (parsed_sids.append(("copilot", s)), cop_orig.parser(p, s, c))[1]),
    )
    monkeypatch.setitem(
        sync_module.AGENT_ADAPTERS,
        "opencode",
        replace(oc_orig, parser=lambda p, s, c: (parsed_sids.append(("opencode", s)), oc_orig.parser(p, s, c))[1]),
    )
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute("INSERT INTO sessions VALUES ('cop-2', ?, '2026-11-15T01:00:00Z')", (str(tmp_path / "repo"),))
        conn.execute(
            "INSERT INTO assistant_usage_events VALUES (2, 'cop-2', 'gpt-6-luna', 50, 10, 0, 0, 0, '2026-11-15T01:01:00Z')"
        )
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.execute("INSERT INTO session_v2 VALUES ('oc-2', ?, 2000)", (str(tmp_path / "repo"),))
        conn.execute(
            "INSERT INTO session_message VALUES ('m2', 'oc-2', 'assistant', 1, 2000, ?)",
            (
                json.dumps(
                    {
                        "model": {"providerID": "anthropic", "id": "claude-sonnet-4-5"},
                        "tokens": {"input": 5, "output": 2},
                    }
                ),
            ),
        )
    out3 = sync_sessions(make_state())
    assert out3.selected == 2
    assert out3.ingested == 2
    assert out3.unchanged == 6
    assert parsed_sids == [("copilot", "cop-2"), ("opencode", "oc-2")]
    assert read_session_manifest(session_bundle_path("copilot", "cop-1")).ingested_at == cop1_ingested
    assert read_session_manifest(session_bundle_path("opencode", "oc-1")).ingested_at == oc1_ingested

    # Updating an existing session invalidates only that session's stamp without reparsing sibling sessions.
    parsed_sids.clear()
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute("INSERT INTO turns VALUES (1, 'cop-1', 0, 'follow-up', 'done', '2026-11-15T02:00:00Z')")
    out_upd = sync_sessions(make_state(), agent="copilot")
    assert out_upd.selected == 1
    assert out_upd.ingested == 1
    assert out_upd.unchanged == 1
    assert parsed_sids == [("copilot", "cop-1")]

    # OpenCode in-place equal-length JSON update reparses only oc-1, leaving oc-2 untouched.
    parsed_sids.clear()
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.execute(
            "INSERT INTO session_part VALUES ('m1', 'oc-1', 0, 'text', 1000, ?)",
            (json.dumps({"type": "text", "text": "aaaa"}),),
        )
    out_oc_ins = sync_sessions(make_state(), agent="opencode")
    assert out_oc_ins.selected == 1
    assert out_oc_ins.unchanged == 1
    assert parsed_sids == [("opencode", "oc-1")]
    parsed_sids.clear()
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.execute(
            "UPDATE session_part SET data = ? WHERE message_id = 'm1'",
            (json.dumps({"type": "text", "text": "bbbb"}),),
        )
    out_oc_eq = sync_sessions(make_state(), agent="opencode")
    assert out_oc_eq.selected == 1
    assert out_oc_eq.unchanged == 1
    assert parsed_sids == [("opencode", "oc-1")]

    # Untouched DB checkpoint uses lightweight enumerate() and skips enumerate_stamped().
    monkeypatch.setitem(
        sync_module.AGENT_ADAPTERS,
        "opencode",
        replace(
            oc_orig,
            enumerate_stamped=lambda _p: (_ for _ in ()).throw(AssertionError("should skip stamped scan")),
        ),
    )
    out_fast = sync_sessions(make_state(), agent="opencode")
    assert out_fast.unchanged == 2
    assert out_fast.selected == 0

    monkeypatch.setitem(sync_module.AGENT_ADAPTERS, "copilot", cop_orig)
    monkeypatch.setitem(sync_module.AGENT_ADAPTERS, "opencode", oc_orig)

    # A database bundle with cleared source_signature retries even when database_signature matches checkpoint.
    cop1_path = session_bundle_path("copilot", "cop-1")
    cop1_lines = cop1_path.read_text(encoding="utf-8").splitlines()
    cop1_doc = json.loads(cop1_lines[0]) | {"source_signature": ""}
    cop1_path.write_text("\n".join([json.dumps(cop1_doc), *cop1_lines[1:]]) + "\n", encoding="utf-8")
    out4 = sync_sessions(make_state(), agent="copilot")
    assert out4.selected == 1
    assert read_session_manifest(cop1_path).source_signature != ""


def test_sync_sessions_failures_read_sync_state_and_bounded_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for retired_name in ("codex", "grok"):
        with pytest.raises(DotError, match="retired"):
            sync_sessions(make_state(), agent=retired_name)
    with pytest.raises(DotError, match="unknown session agent"):
        sync_sessions(make_state(), agent="bogus")

    (tmp_path / ".copilot/session-store.db").mkdir(parents=True)
    st_dir = make_state()
    assert sync_sessions(st_dir, agent="copilot").failed == 1
    assert "database path is a directory" in buf(st_dir.stderr)
    (tmp_path / ".copilot/session-store.db").rmdir()

    assert bounded_failure(ValueError("err 12345678-1234-1234-1234-1234567890ab sid1"), "sid1").count("<session>") == 2
    root = tmp_path / ".agents/sessions" / SESSION_STORE_VERSION
    assert read_sync_state(root, "agy") == "never"
    (root / "agy").mkdir(parents=True)
    (root / "agy" / SYNC_STATE_NAME).write_text(
        json.dumps({"schema": SYNC_STATE_SCHEMA, "synced_at": "2026-11-15T00:00:00", "failed": 0}),
        encoding="utf-8",
    )
    assert read_sync_state(root, "agy") == "unreadable"

    log = _write_agy(tmp_path, "agy-bad", malformed=True)
    st = make_state()
    bad_outcome = sync_sessions(st, agent="agy")
    assert bad_outcome.failed == 1
    assert "malformed source records; archived the transcript without usage" in buf(st.stderr)

    log.write_text(
        json.dumps(
            {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "ok", "created_at": "2026-11-15T00:00:00Z"}
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "agy/agy-bad.jsonl").write_text(
        json.dumps(
            {
                "agent": "agy",
                "session_id": "agy-bad",
                "schema_version": SESSION_SCHEMA_VERSION,
                "parser_version": str(int(SESSION_PARSER_VERSION) - 1),
                "source_type": "x",
                "source_fingerprint": "f",
                "ingested_at": "2026-11-15T00:00:00Z",
                "completeness": "complete",
                "record_count": 1,
            }
        )
        + "\nnull\n",
        encoding="utf-8",
    )
    (root / "agy" / SYNC_STATE_NAME).unlink(missing_ok=True)
    st_up = make_state()
    assert sync_sessions(st_up, agent="agy").failed == 0
    assert "upgrading archived agy sessions" in buf(st_up.stderr)

    # Corrupt bundle in store is skipped during incremental sync; retained usage is preserved on malformed rerun.
    (root / "agy/corrupt.jsonl").write_text("{corrupt\n", encoding="utf-8")
    log.write_text(log.read_text(encoding="utf-8") + "{bad\n", encoding="utf-8")
    st_keep = make_state()
    kept = sync_sessions(st_keep, agent="agy")
    assert kept.failed == 1
    assert kept.retained == 1
    assert "kept the archived usage" in buf(st_keep.stderr)

    # Source-changed-during-capture guard aborts capture when source mutates mid-parse.
    agy_adapter = sync_module.AGENT_ADAPTERS["agy"]

    def mutating_parser(path: Path, sid: str, cwd: str) -> ParsedSession:
        parsed = agy_adapter.parser(path, sid, cwd)
        if path == log:
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        return parsed

    st_race = make_state()
    monkeypatch.setitem(sync_module.AGENT_ADAPTERS, "agy", replace(agy_adapter, parser=mutating_parser))
    race = sync_sessions(st_race, agent="agy")
    assert race.failed == 1
    assert "changed during capture" in buf(st_race.stderr)

    # Mid-sync SQLite WAL mutation omits database_signature so the next sync re-scans the DB cleanly.
    cop_db = tmp_path / ".copilot/session-store.db"
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions(id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns(id INTEGER PRIMARY KEY, session_id TEXT, turn_index INT, user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events(id INTEGER PRIMARY KEY, session_id TEXT, model TEXT, input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT, created_at TEXT);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-race-1', ?, '2026-11-15T00:00:00Z')", (str(tmp_path / "repo"),))
        conn.execute(
            "INSERT INTO assistant_usage_events VALUES (1, 'cop-race-1', 'gpt-6-luna', 10, 5, 0, 0, 0, '2026-11-15T00:01:00Z')"
        )
    cop_adapter = sync_module.AGENT_ADAPTERS["copilot"]

    def mutating_cop_parser(path: Path, sid: str, cwd: str) -> ParsedSession:
        parsed = cop_adapter.parser(path, sid, cwd)
        if sid == "cop-race-1":
            with closing(sqlite3.connect(path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "INSERT INTO sessions VALUES ('cop-race-2', ?, '2026-11-15T00:02:00Z')", (str(tmp_path / "repo"),)
                )
                conn.execute(
                    "INSERT INTO assistant_usage_events VALUES (2, 'cop-race-2', 'gpt-6-luna', 20, 8, 0, 0, 0, '2026-11-15T00:03:00Z')"
                )
                conn.commit()
        return parsed

    monkeypatch.setitem(sync_module.AGENT_ADAPTERS, "copilot", replace(cop_adapter, parser=mutating_cop_parser))
    assert sync_sessions(make_state(), agent="copilot").ingested == 1
    cop_race_state = read_sync_state(root, "copilot")
    assert isinstance(cop_race_state, sync_module.SyncState)
    assert cop_race_state.database_signature == ""

    monkeypatch.setitem(sync_module.AGENT_ADAPTERS, "copilot", cop_adapter)
    res_cop = sync_sessions(make_state(), agent="copilot")
    assert res_cop.unchanged == 1
    assert res_cop.ingested == 1
    cop_clean_state = read_sync_state(root, "copilot")
    assert isinstance(cop_clean_state, sync_module.SyncState)
    assert cop_clean_state.database_signature


def test_stats_cli_sync_filters_and_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    proj = tmp_path / "proj"
    _write_agy(tmp_path, "agy-cli", project=proj)

    res_sync = CliRunner().invoke(
        app,
        [
            "stats",
            "--since",
            "2026-01-01",
            "--until",
            "2026-12-31",
            "--project",
            str(proj),
            "--by-model",
            "--by-project",
            "--json",
        ],
    )
    assert res_sync.exit_code == 0
    doc = json.loads(res_sync.stdout)
    assert doc["schema"] == "dot.stats/v5"
    assert doc["sync"] == {"failed": 0, "retained": 0, "retained_current_transcripts": 0}
    assert len(doc["usage"]) == 1

    res_no_sync = CliRunner().invoke(app, ["stats", "--no-sync", "--json"])
    assert res_no_sync.exit_code == 0
    assert "sync" not in json.loads(res_no_sync.stdout)

    retired = CliRunner().invoke(app, ["stats", "--agent", "codex"])
    assert retired.exit_code == 0
    assert "codex is retired" in retired.stdout

    _write_agy(tmp_path, "agy-bad-cli", project=proj, malformed=True)
    failed = CliRunner().invoke(app, ["stats", "--agent", "agy", "--json"])
    assert failed.exit_code == 1
    assert json.loads(failed.stdout)["sync"]["failed"] == 1
    assert "malformed source records" in failed.stderr

    assert CliRunner().invoke(app, ["stats", "--since", "not-a-date"]).exit_code == 2
    assert CliRunner().invoke(app, ["stats", "--since", "2026-12-01", "--until", "2026-01-01"]).exit_code == 2
