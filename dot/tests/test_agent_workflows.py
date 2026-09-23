from __future__ import annotations

import io
import json
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
from fmind_dot.archive.parsers import AgentAdapter, ParsedSession
from fmind_dot.archive.store import SessionLog, read_session_bundle, read_session_manifest, session_bundle_path
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import UsageRecord, load_usage_records
from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.hooks import notification_workspace
from fmind_dot.process import Runner
from fmind_dot.state import State


def _state(*, runner: Runner | None = None, stdin: str = "") -> State:
    state = State(
        runner=runner or Runner(),
        stdin=io.StringIO(stdin),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    state.__dict__["_config"] = Config()
    return state


def _stderr(state: State) -> str:
    assert isinstance(state.stderr, io.StringIO)
    return state.stderr.getvalue()


def _create_copilot_database(path: Path, *, complete_schema: bool = True) -> None:
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
        if complete_schema:
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


def _write_jsonl(path: Path, *records: object, malformed: bool = False) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = [json.dumps(record) for record in records]
    if malformed:
        lines.append("{")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fixture_adapter(
    monkeypatch: pytest.MonkeyPatch, state: State, tmp_path: Path, parser: object, session_id: str = "fixture-id"
) -> None:
    adapter = AgentAdapter("fixture", "Fixture", False, parser)  # ty: ignore[invalid-argument-type]
    monkeypatch.setattr(archive_sync_module, "agent_adapters", lambda: [adapter])
    monkeypatch.setattr(archive_sync_module, "enumerate_sessions", lambda *_args: [(session_id, "", tmp_path)])
    state.config.agent.sources["fixture"] = str(tmp_path)


def test_sync_rejects_configured_source_with_wrong_kind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / "claude-source"
    source.write_text("not a directory\n", encoding="utf-8")
    state = _state()
    state.config.agent.sources["claude"] = str(source)

    with pytest.raises(DotError, match="Claude session path is not a directory"):
        sync_sessions(state)

    # A report's quiet refresh names the broken source and carries on.
    outcome = sync_sessions(state, quiet=True)
    assert outcome.failed == 1
    assert "failed to inspect the session source for Claude: Claude session path is not a directory" in _stderr(state)


def test_session_sync_keeps_the_longest_copy_of_a_duplicated_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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
    state = _state()

    first = sync_sessions(state)
    second = sync_sessions(state)

    manifest, records = read_session_bundle(session_bundle_path("claude", session_id))
    assert (manifest.record_count, manifest.completeness, len(records)) == (2, "complete", 2)
    assert (first.ingested, first.retained) == (1, 1)
    assert (second.ingested, second.unchanged, second.retained) == (0, 1, 1)
    assert load_usage_records()[0].total_tokens == 42
    assert "claude: 0 ingested, 1 unchanged, 1 retained" in _stderr(state)
    assert "agent-session-sync: done (0 failed)" in _stderr(state)


def test_session_sync_isolates_malformed_sessions_and_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

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
    _write_jsonl(
        tmp_path / ".codex/sessions/rollout-2026-09-06T08-00-00-codex-ok.jsonl",
        {"timestamp": "2026-09-06T08:00:00Z", "role": "user", "content": "later adapter"},
    )
    _write_jsonl(
        tmp_path / ".grok/sessions/%2Fwork/grok-negative/updates.jsonl",
        {
            "timestamp": 1_788_681_600,
            "params": {"update": {"sessionUpdate": "agent_message_chunk", "content": {"text": "grok answer"}}},
        },
        {"params": {"update": {"sessionUpdate": "turn_completed", "usage": {"inputTokens": -1}}}},
    )

    synced = CliRunner().invoke(app, ["agent", "session", "sync", "--json"])

    assert synced.exit_code == 1
    outcomes = json.loads(synced.stdout)
    assert outcomes["schema"] == "dot.agent.session.sync/v2"
    assert (outcomes["failed"], outcomes["ingested"], outcomes["selected"]) == (4, 5, 6)
    assert "agent-session: failed to capture session for Claude: " in synced.stderr
    assert "a-surrogate" not in synced.stderr
    assert synced.stderr.count("usage extraction failed; archived the transcript without usage") == 3
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
        ("codex-ok", "complete", 0, True),
        ("grok-negative", "complete", 0, True),
    }
    assert {record.session_id for record in load_usage_records()} == {"d-valid"}


def test_usage_sync_covers_file_database_and_signals_only_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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

    grok_dir = tmp_path / ".grok/sessions/%2Fwork%2Fgrok/grok-sync"
    grok_dir.mkdir(mode=0o700, parents=True)
    (grok_dir / "signals.json").write_text(
        json.dumps({"primaryModelId": "grok-test", "contextTokensUsed": 21, "turnCount": 3}),
        encoding="utf-8",
    )
    _create_copilot_database(tmp_path / ".copilot/session-store.db")
    state = _state()

    assert sync_sessions(state).ingested == 4

    usage = {record.harness: record for record in load_usage_records()}
    assert set(usage) == {"agy", "claude", "copilot", "grok"}
    assert usage["agy"].turn_count == 1
    assert usage["grok"].total_tokens == 21


def test_copilot_sessions_are_captured_from_the_database_without_a_hook(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)

    first = CliRunner().invoke(app, ["agent", "usage", "show", "copilot", "copilot-live"])
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE assistant_usage_events SET input_tokens = 20 WHERE session_id = 'copilot-live'")
        connection.commit()
    second = CliRunner().invoke(app, ["agent", "usage", "show", "copilot", "copilot-live"])

    assert first.exit_code == second.exit_code == 0
    assert json.loads(first.stdout)["record"]["total_tokens"] == 17
    record = json.loads(second.stdout)["record"]
    assert (record["model"], record["total_tokens"]) == ("gpt-test", 27)
    assert [path.name for path in (tmp_path / ".agents/sessions/v3/copilot").glob("*.jsonl")] == ["copilot-live.jsonl"]
    assert read_session_manifest(session_bundle_path("copilot", "copilot-live")).record_count == 2


@pytest.mark.parametrize("agent", ["claude", "codex", "grok", "agy"])
def test_sync_reports_inaccessible_project_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state()
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


def test_copilot_checkpoint_skips_reads_and_keeps_unchanged_bundles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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
    state = _state()
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
    monkeypatch.setenv("HOME", str(tmp_path))
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    state = _state()
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


def test_copilot_checkpoint_detects_wal_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    database = tmp_path / ".copilot/session-store.db"
    _create_copilot_database(database)
    state = _state()
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


def test_reports_sync_first_and_warn_without_blocking_on_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_jsonl(
        tmp_path / ".claude/projects/project/fresh.jsonl",
        {
            "type": "assistant",
            "timestamp": "2026-09-06T08:00:00Z",
            "message": {"model": "m", "content": [{"type": "text", "text": "a"}], "usage": {"input_tokens": 4}},
        },
    )
    broken = tmp_path / ".codex/sessions"
    broken.parent.mkdir(parents=True)
    broken.write_text("not a directory")

    stats = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--json"])
    listed = CliRunner().invoke(app, ["agent", "usage", "list"])

    assert stats.exit_code == 0
    assert [row["harness"] for row in json.loads(stats.stdout)["usage"]] == ["claude"]
    assert "failed to inspect the session source for Codex" in stats.stderr
    assert "agent-session-sync" not in stats.stderr
    assert listed.exit_code == 0
    assert "fresh" in listed.stdout


def test_session_and_usage_cli_surfaces_report_ingested_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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
    exported = CliRunner().invoke(
        app,
        ["agent", "session", "export", "--session", session_id, "--redact-content"],
    )
    usage_list = CliRunner().invoke(app, ["agent", "usage", "list", "--json"])
    usage_show = CliRunner().invoke(app, ["agent", "usage", "show", "claude", session_id])
    usage_stats = CliRunner().invoke(app, ["agent", "stats", "--tokens-only", "--json", "--by-model"])

    assert listed.exit_code == 0
    assert f"claude {session_id} records=1" in listed.stdout
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["session"]["records"][0]["content"] == "answer"
    assert exported.exit_code == 0
    assert json.loads(exported.stdout)["sessions"][0]["records"][0]["content"] == "[redacted]"
    assert usage_list.exit_code == 0
    assert json.loads(usage_list.stdout)["records"][0]["session_id"] == session_id
    assert usage_show.exit_code == 0
    assert json.loads(usage_show.stdout)["record"]["total_tokens"] == 7
    assert usage_stats.exit_code == 0
    assert json.loads(usage_stats.stdout)["usage"][0]["model"] == "claude-test"


def test_session_sync_main_normalizes_empty_copilot_database_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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


def test_session_cli_rejects_inverted_date_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

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
    assert notification_workspace(io.StringIO(""), "codex") == ""
    assert notification_workspace(io.StringIO('{"stop_hook_active":true}'), "claude") is None
    assert notification_workspace(io.StringIO('{"cwd":"/work"}'), "agy") is None

    with pytest.raises(DotError, match="expected a JSON object"):
        notification_workspace(io.StringIO("[]"), "codex")
    with pytest.raises(DotError, match="stopHookActive must be a boolean"):
        notification_workspace(io.StringIO('{"stopHookActive":"false"}'), "grok")


def test_sync_failures_name_the_agent_operation_and_redact_session_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    session_id = "01a0685e-853d-7c12-99a8-4866999e6f55"

    def parser(_path: Path, _session_id: str, _cwd: str) -> ParsedSession:
        raise TypeError(f"bad session {session_id}")

    state = _state()
    _fixture_adapter(monkeypatch, state, tmp_path, parser, session_id)

    with pytest.raises(DotError, match=r"session sync recorded 1 failure"):
        sync_sessions(state)
    assert "agent-session: failed to capture session for Fixture: bad session <session>\n" in _stderr(state)

    def scan_failure(_root: Path, _agent: str) -> list[tuple[str, str, Path]]:
        raise sqlite3.OperationalError(f"scan exposed {session_id}")

    monkeypatch.setattr(archive_sync_module, "enumerate_sessions", scan_failure)
    with pytest.raises(DotError, match=r"session sync recorded 1 failure"):
        sync_sessions(state)
    assert "agent-session: failed to scan sessions for Fixture: scan exposed <session>\n" in _stderr(state)


def test_session_sync_archives_transcript_then_reports_failed_usage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    log = SessionLog("2026-09-06T08:00:00Z", "fixture", "fixture-id", "user", "kept")
    state = _state()
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
    monkeypatch.setenv("HOME", str(tmp_path))
    usage = UsageRecord(
        harness="fixture", agent="fixture", session_id="fixture-id", measurement_kind="provider-reported"
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    state = _state()
    _fixture_adapter(monkeypatch, state, tmp_path, lambda *_args: ParsedSession([], "a" * 64, "fixture", usage=usage))

    assert sync_sessions(state).ingested == 1

    assert read_session_manifest(session_bundle_path("fixture", "fixture-id")).usage == usage.to_dict()


def test_sync_normalizes_publication_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state()
    _fixture_adapter(monkeypatch, state, tmp_path, lambda *_args: ParsedSession([], "a" * 64, "fixture"))

    def record_failure(*_args: object, **_kwargs: object) -> None:
        raise OSError("source vanished")

    monkeypatch.setattr(archive_sync_module, "ingest_session", record_failure)

    with pytest.raises(DotError, match="session sync recorded 1 failure"):
        sync_sessions(state)
    assert "failed to capture session for Fixture: source vanished" in _stderr(state)


def test_sync_rejects_unknown_agents() -> None:
    with pytest.raises(DotError, match="unknown session agent"):
        sync_sessions(_state(), agent="fixture")


def test_usage_and_session_empty_cli_contracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    usage = CliRunner().invoke(app, ["agent", "usage", "list"])
    shown = CliRunner().invoke(app, ["agent", "session", "show"])

    assert usage.exit_code == 0
    assert usage.stdout == "No usage records found.\n"
    assert shown.exit_code == 2
    assert "show requires a session identity" in shown.stderr
    for removed in (["compact", "--apply"], ["ingest", "claude", "session-id"], ["show", "x", "--latest"]):
        assert CliRunner().invoke(app, ["agent", "session", *removed]).exit_code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["agent", "stats", "--agent", "claud"],
        ["agent", "usage", "list", "--agent", "claud"],
        ["agent", "usage", "show", "claud", "session-id"],
        ["agent", "session", "list", "--agent", "claud"],
        ["agent", "session", "show", "session-id", "--agent", "claud"],
        ["agent", "session", "export", "--agent", "claud"],
        ["agent", "session", "stats", "--agent", "claud"],
        ["agent", "session", "sync", "--agent", "claud"],
        ["agent", "doctor", "--agent", "claud"],
    ],
)
def test_reports_reject_unknown_agents_before_any_sync(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, arguments: list[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an unknown agent must not trigger a sync")

    monkeypatch.setattr(agent_module, "sync_sessions", forbidden)
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 2, arguments
    assert "unknown agent 'claud'" in _click.utils.strip_ansi(result.stderr)
    assert not (tmp_path / ".agents").exists()


def test_reports_with_no_sync_read_the_archive_as_stored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
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
    listed = CliRunner().invoke(app, ["agent", "usage", "list", "--no-sync", "--json"])
    shown = CliRunner().invoke(app, ["agent", "usage", "show", "--no-sync", "claude", session_id])

    assert stats.exit_code == 0
    assert "without a sync" in json.loads(stats.stdout)["coverage"]
    assert [row["sessions"] for row in json.loads(stats.stdout)["usage"]] == [1]
    assert listed.exit_code == 0
    assert [record["session_id"] for record in json.loads(listed.stdout)["records"]] == [session_id]
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["record"]["input_tokens"] == 4
