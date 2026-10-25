from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
from typer import _click
from typer.testing import CliRunner

from fmind_dot import agent as agent_module
from fmind_dot import cli as cli_module
from fmind_dot.archive import sync as archive_sync_module
from fmind_dot.archive.parsers import RETIRED_AGENTS, AgentAdapter, ParsedSession, SessionParser
from fmind_dot.archive.store import (
    SessionLog,
    ingest_session,
    read_session_bundle,
    read_session_manifest,
    session_bundle_path,
    session_store_root,
)
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import UsageRecord, iter_usage_records
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.hooks import notification_workspace
from fmind_dot.state import State
from tests.fakes import make_state


def _stderr(state: State) -> str:
    assert isinstance(state.stderr, io.StringIO)
    return state.stderr.getvalue()


def _create_copilot_database(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                cwd TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE turns (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                turn_index INTEGER,
                user_message TEXT,
                assistant_response TEXT,
                timestamp TEXT
            );
            INSERT INTO sessions VALUES (
                'copilot-live', '/work/project',
                '2026-09-06T08:00:00Z', '2026-09-06T08:01:00Z'
            );
            INSERT INTO turns VALUES (
                1, 'copilot-live', 1, 'private prompt', 'useful answer',
                '2026-09-06T08:00:00Z'
            );
            """
        )
        connection.executescript(
            """
            CREATE TABLE assistant_usage_events (
                session_id TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cache_read_tokens INTEGER,
                cache_write_tokens INTEGER,
                reasoning_tokens INTEGER
            );
            INSERT INTO assistant_usage_events VALUES (
                'copilot-live', 'gpt-test', 10, 4, 2, 1, 3
            );
            """
        )


def _write_jsonl(path: Path, *records: object) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def _fixture_adapter(
    monkeypatch: pytest.MonkeyPatch, state: State, tmp_path: Path, parser: SessionParser, session_id: str = "fixture-id"
) -> None:
    adapter = AgentAdapter(
        "fixture",
        "Fixture",
        False,
        parser,
        lambda _root: [(session_id, "", tmp_path)],
    )
    monkeypatch.setattr(archive_sync_module, "AGENT_ADAPTERS", {"fixture": adapter})
    state.config.agent.sources["fixture"] = str(tmp_path)


def test_sync_rejects_configured_source_with_wrong_kind(tmp_path: Path) -> None:
    source = tmp_path / "claude-source"
    source.write_text("not a directory\n", encoding="utf-8")
    state = make_state()
    state.config.agent.sources["claude"] = str(source)

    with pytest.raises(DotError, match="Claude session path is not a directory"):
        sync_sessions(state)

    # A report's quiet refresh names the broken source and carries on.
    outcome = sync_sessions(state, quiet=True)
    assert outcome.failed == 1
    assert "failed to inspect the session source for Claude: Claude session path is not a directory" in _stderr(state)


def test_session_sync_keeps_the_longest_copy_of_a_duplicated_session(tmp_path: Path) -> None:
    session_id = "shared-claude-session"

    def answer(index: int) -> dict[str, object]:
        return {
            "type": "assistant",
            "timestamp": f"2026-09-06T08:00:0{index}Z",
            "cwd": "/work/project",
            "message": {
                "id": f"message-{index}",
                "model": "claude-test",
                "content": [{"type": "text", "text": f"answer {index}"}],
                "usage": {"input_tokens": 10 * index, "output_tokens": 4 * index},
            },
        }

    _write_jsonl(tmp_path / f".claude/projects/project-1/{session_id}.jsonl", answer(1), answer(2))
    _write_jsonl(tmp_path / f".claude/projects/project-2/{session_id}.jsonl", answer(1))
    state = make_state()

    first = sync_sessions(state)
    second = sync_sessions(state)

    manifest, records = read_session_bundle(session_bundle_path("claude", session_id))
    assert (manifest.record_count, manifest.completeness, len(records)) == (2, "complete", 2)
    assert (first.ingested, first.retained) == (1, 1)
    assert (second.ingested, second.unchanged, second.retained) == (0, 1, 1)
    # The complete pass records the retained count that `dot agent doctor` reports.
    assert json.loads((session_store_root() / "claude/.sync.json").read_text())["retained"] == 1
    assert next(iter_usage_records()).total_tokens == 42
    assert "claude: 0 ingested, 1 unchanged, 1 retained" in _stderr(state)
    assert "agent-session-sync: done (0 failed)" in _stderr(state)


def test_session_sync_dry_run_summary_omits_the_unevaluated_retained_count(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".claude/projects/project/claude-dry.jsonl",
        {"type": "user", "timestamp": "2026-09-06T08:00:00Z", "message": {"content": "hi"}},
    )
    state = make_state()

    assert sync_sessions(state, agent="claude", dry_run=True).selected == 1

    # Retention is decided only during capture, so a dry run cannot report it.
    assert "claude: 1 selected, 0 unchanged\n" in _stderr(state)
    assert "retained" not in _stderr(state)


def test_session_sync_isolates_malformed_sessions_and_exits_nonzero(tmp_path: Path) -> None:

    def claude(text: str, **usage: int) -> dict[str, object]:
        return {
            "type": "assistant",
            "timestamp": "2026-09-06T08:00:00Z",
            "message": {"model": "claude-test", "content": [{"type": "text", "text": text}], "usage": usage},
        }

    projects = tmp_path / ".claude/projects/project"
    # A lone surrogate cannot be stored as UTF-8: this session fails first and alone.
    _write_jsonl(projects / "a-surrogate.jsonl", claude("broken \ud83d emoji", input_tokens=1))
    _write_jsonl(projects / "b-rawbyte.jsonl", claude("kept", input_tokens=1))
    with (projects / "b-rawbyte.jsonl").open("ab") as stream:
        stream.write(b'{"type":"user","message":{"content":"\xff"}}\n')
    _write_jsonl(projects / "c-negative.jsonl", claude("kept despite bad metrics", input_tokens=-5))
    _write_jsonl(projects / "d-valid.jsonl", claude("fine", input_tokens=3, output_tokens=2))
    # A later adapter still captures its sessions after Claude's failures.
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """DELETE FROM sessions; DELETE FROM turns; DELETE FROM assistant_usage_events;
            INSERT INTO sessions VALUES ('copilot-ok', '/work', '2026-09-06T08:00:00Z', NULL);
            INSERT INTO turns VALUES (1, 'copilot-ok', 1, 'later adapter', '', '2026-09-06T08:00:00Z');
            INSERT INTO sessions VALUES ('copilot-negative', '/work', '2026-09-06T08:00:00Z', NULL);
            INSERT INTO turns VALUES (2, 'copilot-negative', 1, '', 'copilot answer', '2026-09-06T08:00:00Z');
            INSERT INTO assistant_usage_events VALUES ('copilot-negative', 'gpt-test', -1, 0, 0, 0, 0);"""
        )

    synced = CliRunner().invoke(app, ["agent", "session", "sync", "--json"])

    assert synced.exit_code == 1
    outcomes = json.loads(synced.stdout)
    assert outcomes["schema"] == "dot.agent.session.sync/v2"
    assert (outcomes["failed"], outcomes["ingested"], outcomes["selected"]) == (4, 5, 6)
    assert "agent-session: failed to capture session for Claude: " in synced.stderr
    assert "a-surrogate" not in synced.stderr
    assert synced.stderr.count("usage extraction failed; archived the transcript without usage") == 2
    assert synced.stderr.count("malformed source records; archived the transcript without usage") == 1
    assert isinstance(synced.exception, DotError)
    assert "session sync recorded 4 failure(s)" in str(synced.exception)
    manifests = {
        (manifest.session_id, manifest.completeness, manifest.malformed_records, manifest.usage is None)
        for path in (tmp_path / ".agents/sessions/v3").glob("*/*.jsonl")
        for manifest in [read_session_manifest(path)]
    }
    assert manifests == {
        ("b-rawbyte", "partial", 1, True),
        ("c-negative", "complete", 0, True),
        ("d-valid", "complete", 0, False),
        ("copilot-ok", "complete", 0, True),
        ("copilot-negative", "complete", 0, True),
    }
    assert {record.session_id for record in list(iter_usage_records())} == {"d-valid"}


def test_usage_sync_covers_file_and_database_sources(tmp_path: Path) -> None:
    agy_root = tmp_path / ".gemini/antigravity-cli/brain"
    agy_logs = agy_root / "agy-sync/.system_generated/logs"
    agy_records = (
        {
            "created_at": "2026-09-06T08:00:00Z",
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": "Please inspect this",
        },
        {
            "created_at": "2026-09-06T08:00:01Z",
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "content": "Inspection complete",
            "thinking": "bounded reasoning",
        },
    )
    _write_jsonl(agy_logs / "transcript.jsonl", agy_records[0])
    _write_jsonl(agy_logs / "transcript_full.jsonl", *agy_records)
    (agy_root / "empty-session").mkdir()

    claude_root = tmp_path / ".claude/projects/project"
    claude_record = {
        "type": "assistant",
        "timestamp": "2026-09-06T08:01:00Z",
        "message": {
            "model": "claude-test",
            "content": [{"type": "text", "text": "done"}],
            "usage": {"input_tokens": 9, "output_tokens": 3},
        },
    }
    _write_jsonl(claude_root / "claude-sync.jsonl", claude_record)
    _write_jsonl(claude_root / "memory.jsonl", claude_record)

    _create_copilot_database(tmp_path / ".copilot/session-store.db")
    state = make_state()

    assert sync_sessions(state).ingested == 3

    usage = {record.harness: record for record in list(iter_usage_records())}
    assert set(usage) == {"agy", "claude", "copilot"}
    assert usage["agy"].turn_count == 1
    assert usage["agy"].model == "unknown"
    assert usage["copilot"].total_tokens == 17


def test_agy_workspace_discovered_later_recaptures_an_unchanged_transcript(tmp_path: Path) -> None:
    store = tmp_path / ".gemini/antigravity-cli"
    record = {"created_at": "2026-09-06T08:00:00Z", "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hi"}
    _write_jsonl(store / "brain/agy-cwd/.system_generated/logs/transcript.jsonl", record)
    state = make_state()

    first = sync_sessions(state, agent="agy")
    with closing(sqlite3.connect(store / "conversation_summaries.db")) as connection:
        connection.execute("CREATE TABLE conversation_summaries (conversation_id text, workspace_uris text NOT NULL)")
        connection.execute(
            "INSERT INTO conversation_summaries VALUES ('agy-cwd', ?)", (json.dumps(["file:///work/project"]),)
        )
        connection.commit()
    second = sync_sessions(state, agent="agy")
    third = sync_sessions(state, agent="agy")

    assert (first.ingested, second.ingested, third.ingested, third.unchanged) == (1, 1, 0, 1)
    manifest, logs = read_session_bundle(session_bundle_path("agy", "agy-cwd"))
    assert manifest.cwd == "/work/project"
    assert [log.cwd for log in logs] == ["/work/project"]
    assert sync_sessions(state, agent="agy", cwd="/work/project").unchanged == 1

    # A pruned summaries row keeps the captured workspace while the transcript is unchanged.
    with closing(sqlite3.connect(store / "conversation_summaries.db")) as connection:
        connection.execute("DELETE FROM conversation_summaries")
        connection.commit()
    pruned = sync_sessions(state, agent="agy")
    assert (pruned.ingested, pruned.unchanged) == (0, 1)
    assert read_session_bundle(session_bundle_path("agy", "agy-cwd"))[0].cwd == "/work/project"

    # A transcript that grows after the row is pruned still keeps its workspace.
    with (store / "brain/agy-cwd/.system_generated/logs/transcript.jsonl").open("a") as handle:
        handle.write(json.dumps({**record, "created_at": "2026-09-06T08:01:00Z", "content": "again"}) + "\n")
    grown = sync_sessions(state, agent="agy")
    assert grown.ingested == 1
    assert read_session_bundle(session_bundle_path("agy", "agy-cwd"))[0].cwd == "/work/project"


def test_copilot_sessions_are_captured_from_the_database_without_a_hook(tmp_path: Path) -> None:
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)

    first = CliRunner().invoke(app, ["agent", "stats", "--sessions", "--agent", "copilot", "--json"])
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE assistant_usage_events SET input_tokens = 20 WHERE session_id = 'copilot-live'")
        connection.commit()
    second = CliRunner().invoke(app, ["agent", "stats", "--sessions", "--agent", "copilot", "--json"])

    assert first.exit_code == second.exit_code == 0
    assert json.loads(first.stdout)["records"][0]["total_tokens"] == 17
    [record] = json.loads(second.stdout)["records"]
    assert (record["model"], record["total_tokens"]) == ("gpt-test", 27)
    assert [path.name for path in (tmp_path / ".agents/sessions/v3/copilot").glob("*.jsonl")] == ["copilot-live.jsonl"]
    assert read_session_manifest(session_bundle_path("copilot", "copilot-live")).record_count == 2


@pytest.mark.skipif(os.geteuid() == 0, reason="Root bypasses owner directory permissions")
@pytest.mark.parametrize("agent", ["claude", "agy"])
def test_sync_reports_inaccessible_project_directories(tmp_path: Path, agent: str) -> None:
    state = make_state()
    source = tmp_path / "source"
    blocked = source / "project"
    blocked.mkdir(parents=True)
    (blocked / "session.jsonl").write_text("{}\n")
    state.config.agent.sources[agent] = str(source)
    blocked.chmod(0)
    try:
        with pytest.raises(DotError, match="1 failure"):
            sync_sessions(state, agent=agent)
    finally:
        blocked.chmod(0o700)
    checkpoint = json.loads((tmp_path / f".agents/sessions/v3/{agent}/.sync.json").read_text())
    assert checkpoint["failed"] == 1
    assert "failed to scan sessions" in _stderr(state)


def test_copilot_checkpoint_skips_reads_and_keeps_unchanged_bundles(tmp_path: Path) -> None:
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("INSERT INTO sessions SELECT 'other', cwd, created_at, updated_at FROM sessions")
        connection.execute(
            "INSERT INTO turns SELECT 2, 'other', turn_index, user_message, assistant_response, timestamp FROM turns"
        )
        connection.execute(
            "INSERT INTO assistant_usage_events SELECT 'other', model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens FROM assistant_usage_events"
        )
        connection.commit()
    state = make_state()
    sync_sessions(state, agent="copilot")
    unchanged = session_bundle_path("copilot", "other")
    original = unchanged.read_bytes(), unchanged.stat().st_mtime_ns, unchanged.stat().st_ino
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE assistant_usage_events SET input_tokens=20 WHERE session_id='copilot-live'")
        # A growing shared database must not update source_bytes in unrelated bundles.
        connection.execute("CREATE TABLE unrelated(payload TEXT)")
        connection.execute("INSERT INTO unrelated VALUES (?)", ("x" * 20000,))
        connection.commit()
    outcome = sync_sessions(state, agent="copilot")
    assert (outcome.ingested, outcome.unchanged) == (1, 1)
    assert (unchanged.read_bytes(), unchanged.stat().st_mtime_ns, unchanged.stat().st_ino) == original
    assert sync_sessions(state, agent="copilot").selected == 0
    # Checkpoints cannot hide deleted bundles: only existing current bundles can skip.
    unchanged.unlink()
    assert sync_sessions(state, agent="copilot").ingested == 1
    assert unchanged.exists()


@pytest.mark.parametrize("interruption", ["filtered", "failed", "changed-during-scan"])
def test_copilot_partial_scans_never_publish_a_skip_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, interruption: str
) -> None:
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    state = make_state()
    adapter = archive_sync_module.AGENT_ADAPTERS["copilot"]

    def parse(path: Path, session_id: str, cwd: str) -> ParsedSession:
        result = adapter.parser(path, session_id, cwd)
        if interruption == "failed":
            result.usage_error = ValueError("synthetic extraction failure")
        elif interruption == "changed-during-scan":
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("UPDATE assistant_usage_events SET input_tokens=20")
                connection.commit()
        return result

    with monkeypatch.context() as temporary:
        temporary.setitem(archive_sync_module.AGENT_ADAPTERS, "copilot", replace(adapter, parser=parse))
        sync_sessions(state, agent="copilot", session="copilot-live" if interruption == "filtered" else "", quiet=True)
    # The unchanged source still needs a full parse after partial/failed capture.
    outcome = sync_sessions(state, agent="copilot")
    assert outcome.selected == 1
    manifest = read_session_manifest(session_bundle_path("copilot", "copilot-live"))
    assert manifest.usage is not None
    assert manifest.usage["input_tokens"] == (20 if interruption == "changed-during-scan" else 10)
    assert sync_sessions(state, agent="copilot").selected == 0


def test_copilot_writes_during_every_parse_still_capture_the_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A running Copilot writes the shared database while sync parses: each parse reads one
    # transaction snapshot, so the capture succeeds and only the pass checkpoint is withheld.
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    state = make_state()
    adapter = archive_sync_module.AGENT_ADAPTERS["copilot"]

    def parse(path: Path, session_id: str, cwd: str) -> ParsedSession:
        result = adapter.parser(path, session_id, cwd)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS unrelated (value INTEGER)")
            connection.execute("INSERT INTO unrelated VALUES (1)")
            connection.commit()
        return result

    with monkeypatch.context() as temporary:
        temporary.setitem(archive_sync_module.AGENT_ADAPTERS, "copilot", replace(adapter, parser=parse))
        outcome = sync_sessions(state, agent="copilot")

    assert (outcome.ingested, outcome.failed) == (1, 0)
    assert sync_sessions(state, agent="copilot").selected == 1


def test_copilot_checkpoint_detects_wal_updates(tmp_path: Path) -> None:
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    state = make_state()
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("UPDATE assistant_usage_events SET input_tokens=15")
        connection.commit()
        sync_sessions(state, agent="copilot")
        before = database.stat().st_size, database.stat().st_mtime_ns
        connection.execute("UPDATE assistant_usage_events SET input_tokens=20")
        connection.commit()
        assert (database.stat().st_size, database.stat().st_mtime_ns) == before
        assert sync_sessions(state, agent="copilot").ingested == 1
        manifest = read_session_manifest(session_bundle_path("copilot", "copilot-live"))
        assert manifest.usage is not None
        assert manifest.usage["input_tokens"] == 20


def test_reports_sync_first_and_warn_without_blocking_on_failures(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / ".claude/projects/project/fresh.jsonl",
        {
            "type": "assistant",
            "timestamp": "2026-09-06T08:00:00Z",
            "message": {"model": "m", "content": [{"type": "text", "text": "a"}], "usage": {"input_tokens": 4}},
        },
    )
    broken = tmp_path / ".gemini/antigravity-cli/brain"
    broken.parent.mkdir(parents=True)
    broken.write_text("not a directory")

    stats = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--json"])
    listed = CliRunner().invoke(app, ["agent", "stats", "--sessions"])

    assert stats.exit_code == 0
    assert [row["harness"] for row in json.loads(stats.stdout)["usage"]] == ["claude"]
    assert "failed to inspect the session source for agy" in stats.stderr
    assert "agent-session-sync" not in stats.stderr
    assert listed.exit_code == 0
    assert "fresh" in listed.stdout


def test_session_and_usage_cli_surfaces_report_ingested_evidence(tmp_path: Path) -> None:
    session_id = "claude-cli"
    _write_jsonl(
        tmp_path / f".claude/projects/project/{session_id}.jsonl",
        {
            "type": "assistant",
            "timestamp": "2026-09-06T08:00:00Z",
            "cwd": "/work/cli",
            "message": {
                "model": "claude-test",
                "content": [{"type": "text", "text": "answer"}],
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
        },
    )
    synced = CliRunner().invoke(app, ["agent", "session", "sync"])
    assert synced.exit_code == 0

    listed = CliRunner().invoke(app, ["agent", "session", "list", "--agent", "claude"])
    shown = CliRunner().invoke(app, ["agent", "session", "show", session_id, "--content"])
    usage_list = CliRunner().invoke(app, ["agent", "stats", "--sessions", "--json"])
    usage_stats = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--json", "--by-model"])

    assert listed.exit_code == 0
    assert f"claude {session_id} records=1" in listed.stdout
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["session"]["records"][0]["content"] == "answer"
    assert usage_list.exit_code == 0
    [usage] = json.loads(usage_list.stdout)["records"]
    assert (usage["session_id"], usage["total_tokens"]) == (session_id, 7)
    assert usage_stats.exit_code == 0
    assert json.loads(usage_stats.stdout)["usage"][0]["model"] == "claude-test"


def test_session_sync_main_normalizes_empty_copilot_database_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / ".copilot/session-store.db"
    database.parent.mkdir(parents=True)
    database.touch()
    monkeypatch.setattr(sys, "argv", ["dot", "agent", "session", "sync"])

    with pytest.raises(SystemExit) as stopped:
        cli_module.main()

    captured = capsys.readouterr()
    assert stopped.value.code == 1
    assert captured.out == ""
    assert captured.err == (
        "agent-session: failed to scan sessions for Copilot: no such table: sessions\n"
        "agent-session-sync: done (1 failed)\n"
        "dot: session sync recorded 1 failure(s); see errors above\n"
    )


def test_session_cli_rejects_inverted_date_window() -> None:

    result = CliRunner().invoke(
        app,
        ["agent", "session", "list", "--since", "2026-09-07", "--until", "2026-09-06"],
    )

    assert result.exit_code == 2
    assert "must not be after --until" in _click.utils.strip_ansi(result.stderr)


def test_notification_workspace_accepts_host_aliases_and_honors_guards() -> None:
    aliased = io.StringIO(json.dumps({"workspacePaths": [None, "/work/project"], "fullyIdle": True}))
    assert notification_workspace(aliased, "agy") == "/work/project"
    assert notification_workspace(io.StringIO(json.dumps({"cwd": "/work/direct"})), "claude") == "/work/direct"
    assert notification_workspace(io.StringIO(""), "copilot") is None
    assert notification_workspace(io.StringIO('{"stop_hook_active":true}'), "claude") is None
    assert notification_workspace(io.StringIO('{"cwd":"/work"}'), "agy") is None

    with pytest.raises(DotError, match="expected a JSON object"):
        notification_workspace(io.StringIO("[]"), "copilot")
    with pytest.raises(DotError, match="stopHookActive must be a boolean"):
        notification_workspace(io.StringIO('{"stopHookActive":"false"}'), "agy")


def test_sync_failures_name_the_agent_operation_and_redact_session_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session_id = "01a0685e-853d-7c12-99a8-4866999e6f55"

    def parser(_path: Path, _session_id: str, _cwd: str) -> ParsedSession:
        raise TypeError(f"bad session {session_id}")

    state = make_state()
    _fixture_adapter(monkeypatch, state, tmp_path, parser, session_id)

    with pytest.raises(DotError, match=r"session sync recorded 1 failure"):
        sync_sessions(state)
    assert "agent-session: failed to capture session for Fixture: bad session <session>\n" in _stderr(state)

    def scan_failure(_root: Path) -> list[tuple[str, str, Path]]:
        raise sqlite3.OperationalError(f"scan exposed {session_id}")

    adapter = archive_sync_module.AGENT_ADAPTERS["fixture"]
    monkeypatch.setitem(archive_sync_module.AGENT_ADAPTERS, "fixture", replace(adapter, enumerate=scan_failure))
    with pytest.raises(DotError, match=r"session sync recorded 1 failure"):
        sync_sessions(state)
    assert "agent-session: failed to scan sessions for Fixture: scan exposed <session>\n" in _stderr(state)


def test_session_sync_archives_transcript_then_reports_failed_usage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log = SessionLog("2026-09-06T08:00:00Z", "fixture", "fixture-id", "user", "kept")
    state = make_state()
    _fixture_adapter(
        monkeypatch,
        state,
        tmp_path,
        lambda *_args: ParsedSession([log], "a" * 64, "fixture", usage_error=ValueError("private detail")),
    )

    with pytest.raises(DotError, match="session sync recorded 1 failure"):
        sync_sessions(state)

    assert "usage extraction failed; archived the transcript without usage" in _stderr(state)
    assert "private detail" not in _stderr(state)
    manifest, records = read_session_bundle(session_bundle_path("fixture", "fixture-id"))
    assert (manifest.usage, manifest.source_signature, records) == (None, "", [log])


def test_sync_publishes_usage_from_the_same_parse(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage = UsageRecord(
        harness="fixture", agent="fixture", session_id="fixture-id", measurement_kind="provider-reported"
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    state = make_state()
    _fixture_adapter(monkeypatch, state, tmp_path, lambda *_args: ParsedSession([], "a" * 64, "fixture", usage=usage))

    assert sync_sessions(state).ingested == 1

    assert read_session_manifest(session_bundle_path("fixture", "fixture-id")).usage == usage.to_dict()


def test_sync_normalizes_publication_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = make_state()
    _fixture_adapter(monkeypatch, state, tmp_path, lambda *_args: ParsedSession([], "a" * 64, "fixture"))

    def record_failure(*_args: object, **_kwargs: object) -> None:
        raise OSError("source vanished")

    monkeypatch.setattr(archive_sync_module, "ingest_session", record_failure)

    with pytest.raises(DotError, match="session sync recorded 1 failure"):
        sync_sessions(state)
    assert "failed to capture session for Fixture: source vanished" in _stderr(state)


def test_sync_rejects_unknown_agents() -> None:
    with pytest.raises(DotError, match="unknown session agent"):
        sync_sessions(make_state(), agent="fixture")


@pytest.mark.parametrize("agent", RETIRED_AGENTS)
def test_retired_agents_stay_queryable_but_never_sync(tmp_path: Path, agent: str) -> None:
    usage = UsageRecord(
        timestamp="2026-09-01T00:00:00Z",
        harness=agent,
        session_id="archived",
        model="fixture",
        measurement_kind="provider-reported",
        input_tokens=10,
        turn_count=1,
    ).finalize()
    ingest_session(
        agent,
        "archived",
        [SessionLog("2026-09-01T00:00:00Z", agent, "archived", "user", "kept")],
        usage=usage.to_dict(),
    )
    ingest_session("claude", "current", [SessionLog("2026-09-01T00:00:00Z", "claude", "current", "user", "other")])

    synced = CliRunner().invoke(app, ["agent", "session", "sync", "--agent", agent])
    listed = CliRunner().invoke(app, ["agent", "session", "list", "--agent", agent, "--json"])
    stats = CliRunner().invoke(app, ["agent", "stats", "--agent", agent, "--tokens-only", "--json"])

    assert synced.exit_code == 1
    assert isinstance(synced.exception, DotError)
    assert (
        str(synced.exception)
        == f"{agent} is retired: its archived sessions stay queryable, but dot no longer captures them"
    )
    assert not (tmp_path / f".agents/sessions/v3/{agent}/.sync.json").exists()
    assert listed.exit_code == 0, listed.output
    assert [(item["agent"], item["session_id"]) for item in json.loads(listed.stdout)["sessions"]] == [
        (agent, "archived")
    ]
    assert stats.exit_code == 0, stats.output
    report = json.loads(stats.stdout)
    assert [(row["harness"], row["input_tokens"]) for row in report["usage"]] == [(agent, 10)]
    assert report["coverage"].startswith(f"Archived records without a sync ({agent} is retired).")
    # The doctor inspects live adapters only, so a retired name is a usage error, never an empty pass.
    assert CliRunner().invoke(app, ["agent", "doctor", "--agent", agent, "--json"]).exit_code == 2


def test_usage_and_session_empty_cli_contracts() -> None:

    usage = CliRunner().invoke(app, ["agent", "stats", "--sessions"])
    shown = CliRunner().invoke(app, ["agent", "session", "show"])

    assert usage.exit_code == 0
    assert usage.stdout == "No usage records found.\n"
    assert shown.exit_code == 2
    assert "Missing argument 'identity'" in shown.stderr
    for removed in (["compact", "--apply"], ["ingest", "claude", "session-id"], ["show", "x", "--latest"]):
        assert CliRunner().invoke(app, ["agent", "session", *removed]).exit_code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["agent", "stats", "--agent", "claud"],
        ["agent", "stats", "--sessions", "--agent", "claud"],
        ["agent", "session", "list", "--agent", "claud"],
        ["agent", "session", "show", "session-id", "--agent", "claud"],
        ["agent", "session", "sync", "--agent", "claud"],
        ["agent", "doctor", "--agent", "claud"],
    ],
)
def test_reports_reject_unknown_agents_before_any_sync(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, arguments: list[str]
) -> None:

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an unknown agent must not trigger a sync")

    monkeypatch.setattr(agent_module, "sync_sessions", forbidden)
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 2, arguments
    assert "'claud' is not one of" in _click.utils.strip_ansi(result.stderr)
    assert not (tmp_path / ".agents").exists()


def test_reports_with_no_sync_read_the_archive_as_stored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    session_id = "stored"
    _write_jsonl(
        tmp_path / f".claude/projects/project/{session_id}.jsonl",
        {
            "type": "assistant",
            "timestamp": "2026-09-06T08:00:00Z",
            "message": {"model": "m", "content": [{"type": "text", "text": "a"}], "usage": {"input_tokens": 4}},
        },
    )
    assert CliRunner().invoke(app, ["agent", "session", "sync"]).exit_code == 0
    # A newer source must stay invisible: --no-sync never captures it.
    _write_jsonl(
        tmp_path / ".claude/projects/project/unsynced.jsonl",
        {"type": "assistant", "timestamp": "2026-09-07T08:00:00Z", "message": {"usage": {"input_tokens": 1}}},
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("--no-sync must not capture sessions")

    monkeypatch.setattr(agent_module, "sync_sessions", forbidden)
    stats = CliRunner().invoke(app, ["agent", "stats", "--no-sync", "--tokens-only", "--json"])
    listed = CliRunner().invoke(app, ["agent", "stats", "--sessions", "--no-sync", "--json"])

    assert stats.exit_code == 0
    assert "without a sync" in json.loads(stats.stdout)["coverage"]
    assert [row["sessions"] for row in json.loads(stats.stdout)["usage"]] == [1]
    assert listed.exit_code == 0
    [record] = json.loads(listed.stdout)["records"]
    assert (record["session_id"], record["input_tokens"]) == (session_id, 4)


def test_subagent_transcripts_count_once_with_their_parent_session(tmp_path: Path) -> None:
    from fmind_dot.archive.query import SessionQuery
    from fmind_dot.archive.statistics import prompt_statistics

    project = tmp_path / "claude/-work-project"
    state = make_state()
    state.config.agent.sources["claude"] = str(tmp_path / "claude")

    def answer(tokens: int, model: str) -> dict:
        content = [{"type": "text", "text": "done"}]
        usage = {"input_tokens": tokens, "output_tokens": 0}
        return {"type": "assistant", "timestamp": "2026-09-06T10:01:00Z", "cwd": "/work/project"} | {
            "message": {"id": f"m-{tokens}", "model": model, "content": content, "usage": usage}
        }

    _write_jsonl(
        project / "parent-id.jsonl",
        {"type": "user", "timestamp": "2026-09-06T10:00:00Z", "cwd": "/work/project", "message": {"content": "owner"}},
        answer(1000, "claude-opus-5-5"),
        {"type": "cost-state", "totalCostUSD": 0.5, "hasUnknownModelCost": False},
    )
    delegated = {"isSidechain": True, "sessionId": "parent-id", "agentId": "a1"}
    _write_jsonl(
        project / "parent-id/subagents/agent-a1.jsonl",
        delegated | {"type": "user", "timestamp": "2026-09-06T10:00:30Z", "message": {"content": "delegated task"}},
        delegated | answer(100, "claude-haiku-4-5"),
    )
    _write_jsonl(project / "parent-id/subagents/workflows/wf_1/journal.jsonl", {"type": "launched"})

    sync_sessions(state, agent="claude")
    result = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--no-sync", "--json"])
    listed = CliRunner().invoke(app, ["agent", "session", "list", "--json"])

    assert result.exit_code == 0, result.output
    [row] = json.loads(result.stdout)["usage"]
    assert (row["sessions"], row["input_tokens"], row["cost_usd"], row["cost_complete"]) == (1, 1100, 0.5, True)
    prompts = prompt_statistics(SessionQuery())
    assert (prompts["prompts"], prompts["sidechain_sessions"], prompts["complete"]) == (1, 1, True)
    sessions = {item["session_id"]: item for item in json.loads(listed.stdout)["sessions"]}
    assert sorted(sessions) == ["agent-a1", "parent-id"]
    assert (sessions["agent-a1"]["sidechain"], sessions["agent-a1"]["parent_session_id"]) == (True, "parent-id")
    assert "sidechain" not in sessions["parent-id"]

    # A resumed/forked parent session writing the same subagent basename (even sorting earlier)
    # gets a parent-qualified archive id instead of colliding with the first owner's bundle.
    _write_jsonl(
        project / "00-resumed-id.jsonl",
        {"type": "user", "timestamp": "2026-09-06T10:02:00Z", "cwd": "/work/project", "message": {"content": "next"}},
        answer(500, "claude-opus-5-5"),
        {"type": "cost-state", "totalCostUSD": 0.25, "hasUnknownModelCost": False},
    )
    resumed_delegated = {"isSidechain": True, "sessionId": "00-resumed-id", "agentId": "a1"}
    _write_jsonl(
        project / "00-resumed-id/subagents/agent-a1.jsonl",
        resumed_delegated | answer(50, "claude-haiku-4-5"),
    )

    outcome = sync_sessions(state, agent="claude")
    assert (outcome.ingested, outcome.unchanged, outcome.retained) == (2, 2, 0)
    repeat = sync_sessions(state, agent="claude")
    assert (repeat.ingested, repeat.unchanged, repeat.retained) == (0, 4, 0)
    listed = CliRunner().invoke(app, ["agent", "session", "list", "--json"])
    sessions = {item["session_id"]: item for item in json.loads(listed.stdout)["sessions"]}
    assert sorted(sessions) == ["00-resumed-id", "agent-a1", "agent-a1-00-resumed-id", "parent-id"]
    assert (
        sessions["agent-a1-00-resumed-id"]["sidechain"],
        sessions["agent-a1-00-resumed-id"]["parent_session_id"],
    ) == (True, "00-resumed-id")
