from __future__ import annotations

import io
import json
import os
import sqlite3
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from fmind_dot import agent as agent_module
from fmind_dot import cli as cli_module
from fmind_dot.agent import resolve_hook_identity, sync_sessions, sync_usage
from fmind_dot.agent_parsers import AgentAdapter, ParsedSession
from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


class GitRootRunner(Runner):
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
        max_output_bytes: int | None = None,
    ) -> CommandResult:
        del cwd, input_text, env, timeout, check, max_output_bytes
        assert tuple(args) == ("git", "rev-parse", "--show-toplevel")
        return CommandResult(f"{self.root}\n", "", 0)


def _state(*, runner: Runner | None = None, stdin: str = "") -> State:
    state = State(
        runner=runner or Runner(),
        stdin=io.StringIO(stdin),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    state.__dict__["_config"] = Config()
    return state


def _copilot_payload(session_id: str = "copilot-live", reason: object = "complete") -> str:
    return json.dumps(
        {
            "sessionId": session_id,
            "cwd": "/work/project",
            "reason": reason,
            "timestamp": 1_785_600_000_000,
        }
    )


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


@pytest.mark.parametrize("sync", [sync_sessions, sync_usage])
def test_sync_rejects_configured_source_with_wrong_kind(
    sync: Callable[[State], int], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / "claude-source"
    source.write_text("not a directory\n", encoding="utf-8")
    state = _state()
    state.config.agent.sources["claude"] = str(source)

    with pytest.raises(DotError, match="Claude session path is not a directory"):
        sync(state)

    assert isinstance(state.stdout, io.StringIO)
    assert "Synced 0" not in state.stdout.getvalue()


def test_copilot_session_end_never_blocks_on_database_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _create_copilot_database(tmp_path / ".copilot/session-store.db", complete_schema=False)

    result = CliRunner().invoke(app, ["agent", "hook", "copilot-session-end"], input=_copilot_payload())

    assert result.exit_code == 0
    assert result.stdout == "{}\n"
    records = list((tmp_path / ".agents/hook-failures/v1").glob("*.json"))
    assert len(records) == 1
    failure = json.loads(records[0].read_text(encoding="utf-8"))
    assert failure["operation"] == "sessionEnd"
    assert failure["session_hash"] != "copilot-live"
    assert "copilot-live" not in failure["detail"]


def test_copilot_session_hook_spools_database_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    database = tmp_path / ".copilot/session-store.db"
    database.parent.mkdir(parents=True)
    database.touch()

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "session", "copilot", "copilot-live", "/work/project"],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, sqlite3.Error)
    records = list((tmp_path / ".agents/hook-failures/v1").glob("*.json"))
    assert len(records) == 1
    failure = json.loads(records[0].read_text(encoding="utf-8"))
    assert failure["operation"] == "session"
    assert "no such table: turns" in failure["detail"]


def test_copilot_session_end_rejects_malformed_field_types_without_blocking(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "copilot-session-end"],
        input=_copilot_payload(reason=["complete"]),
    )

    assert result.exit_code == 0
    assert result.stdout == "{}\n"
    records = list((tmp_path / ".agents/hook-failures/v1").glob("*.json"))
    assert len(records) == 1
    failure = json.loads(records[0].read_text(encoding="utf-8"))
    assert failure["detail"] == "invalid Copilot sessionEnd payload: reason must be a string"


def test_hook_failure_spool_refuses_symlinked_parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".agents").symlink_to(outside, target_is_directory=True)

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "session", "claude", "private-session"],
        input="{",
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert "failed to parse agent hook input" in str(result.exception)
    assert list(outside.iterdir()) == []


def test_clean_dry_run_normalizes_targets_and_lists_each_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompts = tmp_path / ".agents/prompts"
    reports = tmp_path / ".agents/reports"
    prompts.mkdir(parents=True)
    reports.mkdir(parents=True)
    prompt = prompts / "TASK.md"
    report = reports / "audit.html"
    prompt.write_text("prompt", encoding="utf-8")
    report.write_text("report", encoding="utf-8")
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    result = CliRunner().invoke(app, ["agent", "clean", " prompts , REPORTS ", "--dry-run"])

    assert result.exit_code == 0
    assert prompt.is_file()
    assert report.is_file()
    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "  ○ .agents/prompts/TASK.md" in output
    assert "  ○ .agents/reports/audit.html" in output
    assert "Would clean 1 file(s) in .agents/prompts" in output
    assert "Would clean 1 file(s) in .agents/reports" in output


def test_failure_spool_is_private_bounded_and_redacts_session_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state()
    state.config.agent.hook_failures.limit = 2
    state.config.agent.hook_failures.detail_limit = 80
    session_id = "01a0685e-853d-7c12-99a8-4866999e6f55"

    for index in range(3):
        agent_module._spool_hook_failure(  # noqa: SLF001 - exercise the spool boundary directly.
            state,
            "codex",
            "session",
            session_id,
            DotError(f"session {session_id} failed with private detail {index}"),
        )

    root = tmp_path / ".agents/hook-failures/v1"
    records = sorted(root.glob("*.json"))
    assert len(records) == 2
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in records)
    content = "".join(path.read_text(encoding="utf-8") for path in records)
    assert session_id not in content
    assert "<session>" in content


def test_failure_spool_retention_stays_on_opened_root_when_path_is_swapped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".agents/hook-failures/v1"
    root.mkdir(parents=True)
    (root / "20000101T000000.000000Z-old.json").write_text("{}\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_records = [outside / "10000101T000000.000000Z-a.json", outside / "10000101T000000.000001Z-b.json"]
    for path in outside_records:
        path.write_text("preserve\n", encoding="utf-8")
    moved = tmp_path / ".agents/hook-failures/v1-opened"
    original_publish = agent_module._publish_owner_only_at  # noqa: SLF001 - inject a deterministic race.

    def publish_then_swap(directory: int, name: str, content: bytes) -> None:
        original_publish(directory, name, content)
        root.rename(moved)
        root.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(agent_module, "_publish_owner_only_at", publish_then_swap)
    state = _state()
    state.config.agent.hook_failures.limit = 1

    agent_module._spool_hook_failure(  # noqa: SLF001 - exercise retention after the injected race.
        state, "codex", "session", "private-session", DotError("failed")
    )

    assert root.is_symlink()
    assert [path.read_text(encoding="utf-8") for path in outside_records] == ["preserve\n", "preserve\n"]
    assert len(list(moved.glob("*.json"))) == 1


def _write_jsonl(path: Path, *records: object, malformed: bool = False) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = [json.dumps(record) for record in records]
    if malformed:
        lines.append("{")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_session_sync_preserves_source_generations_and_standalone_usage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    session_id = "shared-claude-session"
    for index, content in enumerate(("first answer", "second answer"), start=1):
        _write_jsonl(
            tmp_path / f".claude/projects/project-{index}/{session_id}.jsonl",
            {
                "type": "assistant",
                "timestamp": f"2026-09-06T08:00:0{index}Z",
                "cwd": "/work/project",
                "message": {
                    "model": "claude-test",
                    "content": [{"type": "text", "text": content}],
                    "usage": {"input_tokens": 10 * index, "output_tokens": 4 * index},
                },
            },
            malformed=index == 2,
        )
    state = _state()

    assert sync_sessions(state) == 2

    lineage = tmp_path / ".agents/sessions/v1/claude"
    manifests = sorted(lineage.glob("*/*/manifest.json"))
    assert len(manifests) == 2
    parsed = [json.loads(path.read_text(encoding="utf-8")) for path in manifests]
    assert {manifest["completeness"] for manifest in parsed} == {"complete", "partial"}
    assert {manifest["source_fingerprint"] for manifest in parsed} == {
        agent_module.fingerprint_file(tmp_path / f".claude/projects/project-{index}/{session_id}.jsonl")
        for index in (1, 2)
    }
    usage_path = tmp_path / f".agents/usages/claude/{session_id}.json"
    usage = json.loads(usage_path.read_text(encoding="utf-8"))
    assert usage["total_tokens"] == 28
    usage["total_tokens"] = 999
    usage_path.write_text(json.dumps(usage), encoding="utf-8")

    assert sync_sessions(state) == 2
    assert len(list(lineage.glob("*/*/manifest.json"))) == 2
    assert json.loads(usage_path.read_text(encoding="utf-8"))["total_tokens"] == 999
    assert isinstance(state.stderr, io.StringIO)
    assert "claude: 2 checked" in state.stderr.getvalue()
    assert "agent-session-sync: done (2 total processed)" in state.stderr.getvalue()


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

    assert sync_usage(state) == 4

    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == "Synced 4 usage records across 4 harnesses into ~/.agents/usages\n"
    usage_root = tmp_path / ".agents/usages"
    assert sorted(path.relative_to(usage_root).as_posix() for path in usage_root.rglob("*.json")) == [
        "agy/agy-sync.json",
        "claude/claude-sync.json",
        "copilot/copilot-live.json",
        "grok/grok-sync.json",
    ]
    assert json.loads((usage_root / "agy/agy-sync.json").read_text(encoding="utf-8"))["turn_count"] == 1
    assert json.loads((usage_root / "grok/grok-sync.json").read_text(encoding="utf-8"))["total_tokens"] == 21


def test_unsupported_typed_hook_fields_fail_instead_of_changing_control_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state(stdin=json.dumps({"sessionId": "grok-live", "stopHookActive": "false"}))

    with pytest.raises(DotError, match="stopHookActive must be a boolean"):
        resolve_hook_identity(state)


def test_agy_usage_hook_waits_for_idle_and_emits_stop_decision(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    transcript = tmp_path / "agy.jsonl"
    _write_jsonl(
        transcript,
        {
            "created_at": "2026-09-06T08:00:00Z",
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": "hello",
        },
    )
    active = CliRunner().invoke(
        app,
        ["agent", "hook", "usage", "agy"],
        input=json.dumps(
            {
                "conversationId": "agy-live",
                "transcriptPath": str(transcript),
                "workspacePaths": ["/work/agy"],
                "fullyIdle": False,
            }
        ),
    )

    assert active.exit_code == 0
    assert active.stdout == '{"decision":""}\n'
    assert not (tmp_path / ".agents/usages").exists()

    idle = CliRunner().invoke(
        app,
        ["agent", "hook", "usage", "agy"],
        input=json.dumps(
            {
                "conversationId": "agy-live",
                "transcriptPath": str(transcript),
                "workspacePaths": ["/work/agy"],
                "fullyIdle": True,
            }
        ),
    )

    assert idle.exit_code == 0
    assert idle.stdout == '{"decision":""}\n'
    usage = json.loads((tmp_path / ".agents/usages/agy/agy-live.json").read_text(encoding="utf-8"))
    assert usage["cwd"] == "/work/agy"
    assert usage["turn_count"] == 1


def test_copilot_usage_hook_spools_failure_and_keeps_neutral_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _create_copilot_database(tmp_path / ".copilot/session-store.db", complete_schema=False)

    result = CliRunner().invoke(
        app,
        ["agent", "hook", "usage", "copilot"],
        input=_copilot_payload(),
    )

    assert result.exit_code == 1
    assert result.stdout == "{}\n"
    assert isinstance(result.exception, sqlite3.Error)
    failures = list((tmp_path / ".agents/hook-failures/v1").glob("*.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text(encoding="utf-8"))["operation"] == "usage"


def test_copilot_session_end_is_idempotent_and_writes_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _create_copilot_database(tmp_path / ".copilot/session-store.db")

    outputs = [
        CliRunner().invoke(app, ["agent", "hook", "copilot-session-end"], input=_copilot_payload()) for _ in range(2)
    ]

    assert all(result.exit_code == 0 and result.stdout == "{}\n" for result in outputs)
    manifests = list((tmp_path / ".agents/sessions/v1/copilot").glob("*/*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["record_count"] == 2
    usage = json.loads((tmp_path / ".agents/usages/copilot/copilot-live.json").read_text(encoding="utf-8"))
    assert usage["model"] == "gpt-test"
    assert usage["total_tokens"] == 17


def test_clean_removes_only_generated_targets_and_rejects_redirected_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prompts = tmp_path / ".agents/prompts/nested"
    skills = tmp_path / ".agents/skills/custom"
    prompts.mkdir(parents=True)
    skills.mkdir(parents=True)
    (prompts / "TASK.md").write_text("prompt", encoding="utf-8")
    (skills / "SKILL.md").write_text("preserve", encoding="utf-8")
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    cleaned = CliRunner().invoke(app, ["agent", "clean", "prompts"])

    assert cleaned.exit_code == 0
    assert not prompts.exists()
    assert (skills / "SKILL.md").read_text(encoding="utf-8") == "preserve"
    (tmp_path / ".agents/prompts").rmdir()

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.md").write_text("keep", encoding="utf-8")
    (tmp_path / ".agents/prompts").symlink_to(outside, target_is_directory=True)
    rejected = CliRunner().invoke(app, ["agent", "clean", "prompts"])

    assert rejected.exit_code == 1
    assert isinstance(rejected.exception, DotError)
    assert "refusing symlinked cleanup directory" in str(rejected.exception)
    assert (outside / "keep.md").read_text(encoding="utf-8") == "keep"


def test_clean_rejects_non_directory_target_with_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    agents = tmp_path / ".agents"
    agents.mkdir()
    (agents / "prompts").write_text("not a directory", encoding="utf-8")
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    result = CliRunner().invoke(app, ["agent", "clean", "prompts"])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert str(result.exception) == "cleanup target .agents/prompts is not a directory"


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
    usage_stats = CliRunner().invoke(app, ["agent", "usage", "stats", "--json", "--by-model"])

    assert listed.exit_code == 0
    assert f"claude {session_id} records=1" in listed.stdout
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["records"][0]["content"] == "answer"
    assert exported.exit_code == 0
    assert json.loads(exported.stdout)["sessions"][0]["records"][0]["content"] == "[redacted]"
    assert usage_list.exit_code == 0
    assert json.loads(usage_list.stdout)[0]["session_id"] == session_id
    assert usage_show.exit_code == 0
    assert json.loads(usage_show.stdout)["total_tokens"] == 7
    assert usage_stats.exit_code == 0
    assert json.loads(usage_stats.stdout)[0]["model"] == "claude-test"


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
    assert captured.err == "dot: failed to scan sessions for Copilot: no such table: sessions\n"
    assert "Traceback" not in captured.err


def test_session_cli_rejects_inverted_date_window(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = CliRunner().invoke(
        app,
        ["agent", "session", "list", "--since", "2026-09-07", "--until", "2026-09-06"],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert str(result.exception) == "--since must not be after --until"


def test_clean_stays_on_opened_directory_when_target_is_swapped_to_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / ".agents/prompts"
    target.mkdir(parents=True)
    (target / "generated.md").write_text("generated", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "preserve.md"
    victim.write_text("preserve", encoding="utf-8")
    moved = tmp_path / ".agents/prompts-opened"
    swapped = False

    def swap_target() -> None:
        nonlocal swapped
        if swapped:
            return
        target.rename(moved)
        target.symlink_to(outside, target_is_directory=True)
        swapped = True

    original_is_symlink = Path.is_symlink

    def racing_is_symlink(path: Path) -> bool:
        result = original_is_symlink(path)
        if path == target:
            swap_target()
        return result

    original_listdir = os.listdir

    def racing_listdir(path: int | str | bytes | os.PathLike[str] | os.PathLike[bytes]):
        names = original_listdir(path)
        if isinstance(path, int):
            swap_target()
        return names

    monkeypatch.setattr(Path, "is_symlink", racing_is_symlink)
    monkeypatch.setattr(os, "listdir", racing_listdir)
    monkeypatch.setattr(agent_module, "_safe_agent_fs_available", lambda: True)
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    result = CliRunner().invoke(app, ["agent", "clean", "prompts"])

    assert swapped
    assert result.exit_code == 0
    assert victim.read_text(encoding="utf-8") == "preserve"
    assert list(moved.iterdir()) == []
    assert target.is_symlink()


def test_clean_fails_closed_without_symlink_safe_recursive_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    generated = tmp_path / ".agents/prompts/nested/generated.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated", encoding="utf-8")
    monkeypatch.delattr(agent_module.os, "fwalk")
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    result = CliRunner().invoke(app, ["agent", "clean", "prompts"])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert str(result.exception) == "safe agent cleanup is unavailable on this platform"
    assert generated.read_text(encoding="utf-8") == "generated"


def test_hook_identity_accepts_host_aliases_and_fails_closed_on_bad_identity(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.touch()
    aliased = resolve_hook_identity(
        _state(
            stdin=json.dumps(
                {
                    "conversationId": "conversation-id",
                    "workspacePaths": [None, "/work/project"],
                    "transcriptPath": str(transcript),
                    "fullyIdle": True,
                }
            )
        ),
        require_idle=True,
    )
    assert (aliased.session_id, aliased.cwd, aliased.transcript_path, aliased.from_hook) == (
        "conversation-id",
        "/work/project",
        str(transcript),
        True,
    )

    direct = resolve_hook_identity(_state(), "direct-id", "/work/direct")
    assert (direct.session_id, direct.cwd, direct.from_hook) == ("direct-id", "/work/direct", False)
    assert resolve_hook_identity(_state(stdin='{"stop_hook_active":true}')).halt
    assert resolve_hook_identity(_state(stdin='{"sessionId":"ignored"}'), require_idle=True).halt

    with pytest.raises(DotError, match="expected a JSON object"):
        resolve_hook_identity(_state(stdin="[]"))
    with pytest.raises(DotError, match="missing session_id"):
        resolve_hook_identity(_state(stdin="{}"))
    with pytest.raises(DotError, match="invalid session_id format"):
        resolve_hook_identity(_state(stdin='{"sessionId":"invalid/id"}'))


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        '{"sessionId":"only-one-field"}',
        _copilot_payload("invalid/id"),
        json.dumps({"sessionId": "id", "cwd": "", "reason": "complete", "timestamp": 1}),
        json.dumps({"sessionId": "id", "cwd": "/work", "reason": "complete", "timestamp": True}),
        json.dumps({"sessionId": "id", "cwd": "/work", "reason": "complete", "timestamp": 1.5}),
        _copilot_payload(reason="unexpected"),
    ],
    ids=["malformed", "not-object", "fields", "session", "cwd", "timestamp-bool", "timestamp-float", "reason"],
)
def test_copilot_session_end_decoder_rejects_every_invalid_contract_shape(payload: str) -> None:
    with pytest.raises(DotError, match="Copilot sessionEnd"):
        agent_module.decode_copilot_session_end(io.StringIO(payload))


def test_copilot_session_end_decoder_requires_a_payload() -> None:
    with pytest.raises(DotError, match="missing Copilot sessionEnd payload"):
        agent_module.decode_copilot_session_end(None)


def test_sync_failures_name_the_agent_operation_and_redact_session_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session_id = "01a0685e-853d-7c12-99a8-4866999e6f55"

    def parser(_path: Path, _session_id: str, _cwd: str) -> ParsedSession:
        raise TypeError(f"bad session {session_id}")

    adapter = AgentAdapter("fixture", "Fixture", "", "fixture", False, parser, None)

    def adapters(*, verified_only: bool = False) -> list[AgentAdapter]:
        assert verified_only
        return [adapter]

    monkeypatch.setattr(agent_module, "agent_adapters", adapters)
    state = _state()
    state.config.agent.sources["fixture"] = str(tmp_path)
    monkeypatch.setattr(agent_module, "enumerate_sessions", lambda _root, _agent: [(session_id, "", tmp_path)])

    with pytest.raises(DotError, match=r"failed to ingest session for Fixture: bad session <session>"):
        sync_sessions(state)

    def scan_failure(_root: Path, _agent: str):
        raise sqlite3.OperationalError(f"scan exposed {session_id}")

    monkeypatch.setattr(agent_module, "enumerate_usage_sessions", scan_failure)
    with pytest.raises(DotError, match=r"failed to scan usage for Fixture: scan exposed <session>"):
        sync_usage(state)


def test_session_sync_keeps_ingestion_when_standalone_usage_is_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session_id = "fixture-id"
    adapter = AgentAdapter(
        "fixture",
        "Fixture",
        "",
        "fixture",
        False,
        lambda _path, _session_id, _cwd: ParsedSession([], "a" * 64, "fixture"),
        None,
    )

    def adapters(*, verified_only: bool = False) -> list[AgentAdapter]:
        assert verified_only
        return [adapter]

    monkeypatch.setattr(agent_module, "agent_adapters", adapters)
    monkeypatch.setattr(agent_module, "enumerate_sessions", lambda _root, _agent: [(session_id, "", tmp_path)])
    monkeypatch.setattr(
        agent_module,
        "ingest_session",
        lambda *_args, **_kwargs: SimpleNamespace(status="ingested"),
    )
    monkeypatch.setattr(agent_module, "report_ingestion", lambda _result: "agent-session: ingested")

    def usage_failure(*_args, **_kwargs) -> None:
        raise ValueError(f"invalid usage for {session_id}")

    monkeypatch.setattr(agent_module, "record_agent_usage", usage_failure)
    state = _state()
    state.config.agent.sources["fixture"] = str(tmp_path)

    assert sync_sessions(state) == 1
    assert isinstance(state.stderr, io.StringIO)
    assert "usage not recorded for this session: invalid usage for <session>" in state.stderr.getvalue()
    assert "fixture: 1 checked" in state.stderr.getvalue()


def test_usage_sync_normalizes_candidate_record_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adapter = AgentAdapter(
        "fixture",
        "Fixture",
        "",
        "fixture",
        False,
        lambda _path, _session_id, _cwd: ParsedSession([], "a" * 64, "fixture"),
        None,
    )

    def adapters(*, verified_only: bool = False) -> list[AgentAdapter]:
        assert verified_only
        return [adapter]

    monkeypatch.setattr(agent_module, "agent_adapters", adapters)
    monkeypatch.setattr(agent_module, "enumerate_usage_sessions", lambda _root, _agent: [("fixture-id", "", tmp_path)])

    def record_failure(*_args, **_kwargs) -> None:
        raise OSError("source vanished")

    monkeypatch.setattr(agent_module, "record_agent_usage", record_failure)
    state = _state()
    state.config.agent.sources["fixture"] = str(tmp_path)

    with pytest.raises(DotError, match="failed to record usage for Fixture: source vanished"):
        sync_usage(state)


def test_usage_and_session_empty_cli_contracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    migrated: list[bool] = []

    def capture_migration(_stream, *, apply: bool = False) -> None:
        migrated.append(apply)

    monkeypatch.setattr(agent_module, "migrate_legacy_sessions", capture_migration)

    usage = CliRunner().invoke(app, ["agent", "usage", "list"])
    shown = CliRunner().invoke(app, ["agent", "session", "show"])
    migration = CliRunner().invoke(app, ["agent", "session", "migrate", "--apply"])

    assert usage.exit_code == 0
    assert usage.stdout == "No usage records found.\n"
    assert shown.exit_code == 1
    assert isinstance(shown.exception, DotError)
    assert str(shown.exception) == "show requires a session or lineage identity"
    assert migration.exit_code == 0
    assert migrated == [True]


def test_clean_defaults_to_all_targets_and_unlinks_nested_symlinks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "preserve.md"
    victim.write_text("preserve", encoding="utf-8")
    prompts = tmp_path / ".agents/prompts"
    prompts.mkdir(parents=True)
    (prompts / "outside-link").symlink_to(outside, target_is_directory=True)
    state = _state(runner=GitRootRunner(tmp_path))
    monkeypatch.setattr(agent_module, "state_from", lambda _context: state)

    result = CliRunner().invoke(app, ["agent", "clean"])

    assert result.exit_code == 0
    assert victim.read_text(encoding="utf-8") == "preserve"
    assert list(prompts.iterdir()) == []
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue().count("✓ Cleaned") == 3

    invalid = CliRunner().invoke(app, ["agent", "clean", "unknown"])
    assert invalid.exit_code == 1
    assert isinstance(invalid.exception, DotError)
    assert "unknown target 'unknown'" in str(invalid.exception)


def test_session_ingestion_handles_invalid_duplicate_and_usage_failure_contracts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state()

    with pytest.raises(DotError, match="unknown session hook agent"):
        agent_module.ingest_agent_session(state, "unknown", "session-id")
    with pytest.raises(DotError, match="missing session_id"):
        agent_module.ingest_agent_session(state, "copilot")
    with pytest.raises(DotError, match="invalid session_id format"):
        agent_module.ingest_agent_session(state, "copilot", "invalid/id")

    halted = _state(stdin='{"conversationId":"agy-id","fullyIdle":false}')
    agent_module.ingest_agent_session(halted, "agy", hook=True)
    assert isinstance(halted.stdout, io.StringIO)
    assert halted.stdout.getvalue() == '{"decision":""}\n'

    missing = tmp_path / "missing.jsonl"
    state.stdin = io.StringIO(json.dumps({"sessionId": "claude-id", "transcriptPath": str(missing)}))
    with pytest.raises(DotError, match="transcript from hook payload is unavailable"):
        agent_module.ingest_agent_session(state, "claude")

    source = tmp_path / "claude"
    state.config.agent.sources["claude"] = str(source)
    duplicate = source / "nested/duplicate-id.jsonl"
    _write_jsonl(duplicate, {"type": "user", "message": {"content": "ask"}})
    existing = SimpleNamespace(lineage_id="lineage", source_fingerprint=agent_module.fingerprint_file(duplicate))
    monkeypatch.setattr(agent_module, "stored_generation", lambda *_args: existing)
    monkeypatch.setattr(agent_module, "report_ingestion", lambda _result: "agent-session: duplicate")
    state.stdin = io.StringIO()
    agent_module.ingest_agent_session(state, "claude", "duplicate-id")
    assert isinstance(state.stderr, io.StringIO)
    assert state.stderr.getvalue().endswith("agent-session: duplicate\n")

    ingested = source / "nested/ingested-id.jsonl"
    _write_jsonl(ingested, {"type": "user", "message": {"content": "ask"}})
    monkeypatch.setattr(agent_module, "stored_generation", lambda *_args: None)
    monkeypatch.setattr(agent_module, "ingest_session", lambda *_args, **_kwargs: SimpleNamespace(status="ingested"))
    monkeypatch.setattr(agent_module, "report_ingestion", lambda _result: "agent-session: ingested")

    def fail_usage(*_args, **_kwargs) -> None:
        raise ValueError("usage unavailable")

    monkeypatch.setattr(agent_module, "record_agent_usage", fail_usage)
    agent_module.ingest_agent_session(state, "claude", "ingested-id")
    assert state.stderr.getvalue().endswith("claude: usage not recorded for this session: usage unavailable\n")


def test_ingest_agent_session_rejects_corrupt_duplicate_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    session_id = "corrupt-duplicate"
    source_root = tmp_path / ".claude/projects"
    transcript = source_root / "project" / f"{session_id}.jsonl"
    _write_jsonl(transcript, {"type": "user", "message": {"content": "ask"}})
    state = _state()
    state.config.agent.sources["claude"] = str(source_root)

    agent_module.ingest_agent_session(state, "claude", session_id)
    fingerprint = agent_module.fingerprint_file(transcript)
    generation = (
        tmp_path
        / ".agents/sessions/v1/claude"
        / agent_module.session_lineage_id("claude", session_id)
        / agent_module.session_generation_id(fingerprint)
    )
    normalized = generation / "transcript.jsonl"
    normalized.write_text("{}\n", encoding="utf-8")
    state.stderr = io.StringIO()

    with pytest.raises(ValueError, match="session transcript fingerprint mismatch"):
        agent_module.ingest_agent_session(state, "claude", session_id)

    assert state.stderr.getvalue() == ""
    assert normalized.read_text(encoding="utf-8") == "{}\n"


def test_usage_recording_resolves_sources_and_rejects_unverified_adapters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _state()
    written = []
    monkeypatch.setattr(agent_module, "write_usage_record", written.append)

    with pytest.raises(DotError, match="unknown usage hook agent"):
        agent_module.record_agent_usage(state, "unknown-agent", "session-id")

    adapter = AgentAdapter(
        "fixture",
        "Fixture",
        "",
        "fixture",
        False,
        lambda _path, _session_id, _cwd: ParsedSession([], "a" * 64, "fixture"),
        None,
    )
    monkeypatch.setitem(agent_module.AGENT_ADAPTERS, "fixture", adapter)
    state.config.agent.sources["fixture"] = str(tmp_path)
    with pytest.raises(DotError, match="no verified usage parser"):
        agent_module.record_agent_usage(state, "fixture", "session-id")

    grok_root = tmp_path / "grok"
    transcript = grok_root / "%2Fwork%2Fproject/grok-id/updates.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.touch()
    (transcript.parent / "signals.json").write_text(
        '{"primaryModelId":"grok","contextTokensUsed":4,"turnCount":1}', encoding="utf-8"
    )
    state.config.agent.sources["grok"] = str(grok_root)
    agent_module.record_agent_usage(state, "grok", "grok-id")

    claude_root = tmp_path / "claude"
    claude = claude_root / "nested/claude-id.jsonl"
    _write_jsonl(
        claude,
        {
            "type": "assistant",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {"usage": {"input_tokens": 1}},
        },
    )
    state.config.agent.sources["claude"] = str(claude_root)
    agent_module.record_agent_usage(state, "claude", "claude-id")

    assert [(record.harness, record.cwd) for record in written] == [
        ("grok", "/work/project"),
        ("claude", ""),
    ]


def test_doctor_configuration_and_source_checks_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    persona = tmp_path / ".agents/AGENTS.md"
    persona.parent.mkdir(parents=True)
    persona.touch()
    definition = agent_module.DoctorIntegration("fixture", "~/.agents/AGENTS.md")

    assert agent_module._check_discovery(definition) == ("skills-missing", False)  # noqa: SLF001
    skills = tmp_path / ".agents/skills"
    skills.mkdir()
    broken_skills = agent_module.DoctorIntegration("fixture", "~/.agents/AGENTS.md", skills_path="~/.fixture/skills")
    assert agent_module._check_discovery(broken_skills) == ("skills-broken", False)  # noqa: SLF001
    malformed = tmp_path / ".fixture/config.yaml"
    malformed.parent.mkdir()
    malformed.write_text("[", encoding="utf-8")
    malformed_config = agent_module.DoctorIntegration(
        "fixture", "~/.agents/AGENTS.md", skills_config="~/.fixture/config.yaml"
    )
    assert agent_module._check_discovery(malformed_config) == ("skills-broken", False)  # noqa: SLF001
    malformed.write_text("skills: []\n", encoding="utf-8")
    assert agent_module._check_discovery(malformed_config) == ("skills-broken", False)  # noqa: SLF001

    unsupported = tmp_path / "config.txt"
    unsupported.touch()
    with pytest.raises(ValueError, match="unsupported configuration format"):
        agent_module._load_configuration(unsupported, "text")  # noqa: SLF001
    assert agent_module._command_arguments("other command") == ()  # noqa: SLF001

    state = _state()
    assert agent_module._inspect_source(state, definition).status == "unconfigured"  # noqa: SLF001
    linked = tmp_path / "linked-source"
    linked.symlink_to(tmp_path)
    state.config.agent.sources["fixture"] = str(linked)
    assert agent_module._inspect_source(state, definition).status == "linked"  # noqa: SLF001


def test_doctor_database_lineage_and_failure_evidence_remain_conservative(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    fallback = datetime(2026, 1, 1, tzinfo=UTC)
    database = tmp_path / "source.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript("CREATE TABLE sessions(updated_at TEXT); INSERT INTO sessions VALUES(NULL);")
    definition = agent_module.DoctorIntegration(
        "fixture",
        "~/.agents/AGENTS.md",
        source_time_query="SELECT MAX(updated_at) FROM sessions",
    )
    assert agent_module._database_source_time(database, definition, fallback) is None  # noqa: SLF001
    broken_query = agent_module.DoctorIntegration(
        "fixture",
        "~/.agents/AGENTS.md",
        source_time_query="SELECT missing FROM sessions",
    )
    assert agent_module._database_source_time(database, broken_query, fallback) == fallback  # noqa: SLF001

    lineage = tmp_path / ".agents/sessions/v1/fixture"
    lineage.parent.mkdir(parents=True)
    lineage.symlink_to(tmp_path, target_is_directory=True)
    state = _state()
    assert agent_module._inspect_lineage(state, definition).unreadable  # noqa: SLF001

    failures = tmp_path / ".agents/hook-failures/v1"
    failures.mkdir(parents=True)
    (failures / "new.json").write_text("[]", encoding="utf-8")
    assert agent_module._inspect_last_hook_failure(state, "fixture") == ("unreadable", False)  # noqa: SLF001

    source = agent_module._SourceInspection("present", fallback + timedelta(hours=2), True, True)  # noqa: SLF001
    summary = agent_module._LineageSummary(  # noqa: SLF001
        last_complete=fallback,
        latest=fallback + timedelta(hours=1),
        latest_partial=True,
    )
    ingestion, lag, healthy = agent_module._summarize_lineage(  # noqa: SLF001
        state,
        definition,
        fallback + timedelta(hours=2),
        source,
        summary,
    )
    assert ingestion.endswith(":newer-partial")
    assert lag == "unknown"
    assert not healthy
