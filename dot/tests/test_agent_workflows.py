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
            json.dumps({"type": "user", "timestamp": "2026-11-15T00:00:00Z", "message": {"content": p}}) + "\n"
        )
    pi_dir = tmp_path / ".pi/agent/sessions"
    pi_dir.mkdir(parents=True)
    (pi_dir / "2026-11-15_pi-1.jsonl").write_text(
        json.dumps(
            {"type": "message", "timestamp": "2026-11-15T00:00:00Z", "message": {"role": "user", "content": "hello"}}
        )
        + "\n"
    )

    st = make_state()
    out = sync_sessions(st)
    assert out.ingested == 4
    assert out.failed == 0
    assert read_session_manifest(session_bundle_path("agy", "agy-1")).cwd == str(tmp_path / "repo")
    assert len(list((tmp_path / ".agents/sessions" / SESSION_STORE_VERSION / "claude").glob("sub-dup*.jsonl"))) == 2
    assert isinstance(
        read_sync_state(tmp_path / ".agents/sessions" / SESSION_STORE_VERSION, "agy"), sync_module.SyncState
    )

    out2 = sync_sessions(make_state())
    assert out2.unchanged == 4


def test_sync_sessions_failures_read_sync_state_and_bounded_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(DotError, match="retired"):
        sync_sessions(make_state(), agent="copilot")
    with pytest.raises(DotError, match="unknown session agent"):
        sync_sessions(make_state(), agent="bogus")

    assert bounded_failure(ValueError("err 12345678-1234-1234-1234-1234567890ab sid1"), "sid1").count("<session>") == 2
    root = tmp_path / ".agents/sessions" / SESSION_STORE_VERSION
    assert read_sync_state(root, "agy") == "never"
    (root / "agy").mkdir(parents=True)
    (root / "agy" / SYNC_STATE_NAME).write_text(
        json.dumps({"schema": SYNC_STATE_SCHEMA, "synced_at": "2026-11-15T00:00:00", "failed": 0})
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
        + "\n"
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
        + "\nnull\n"
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
