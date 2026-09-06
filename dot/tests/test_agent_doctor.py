from __future__ import annotations

import io
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer import _click
from typer.testing import CliRunner

import fmind_dot.agent as agent_module
from fmind_dot.agent import gather_agent_doctor, repair_agent_integrations, run_agent_doctor
from fmind_dot.cli import app
from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.session_store import SessionLog, SessionSource, fingerprint_file, ingest_session, session_store_root
from fmind_dot.state import State


class DoctorRunner(Runner):
    def __init__(self, tools: set[str] | None = None) -> None:
        self.tools = tools or {"agy", "claude", "codex", "copilot", "dot", "grok", "notify-send"}
        self.unavailable_commands: set[tuple[str, ...]] = set()
        self.calls: list[tuple[str, ...]] = []

    def which(self, command: str) -> Path | None:
        return Path("/tools") / command if command in self.tools else None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        del cwd, input_text, env, timeout
        call = tuple(args)
        self.calls.append(call)
        returncode = int(call in self.unavailable_commands)
        if check and returncode:
            raise DotError(f"command failed ({returncode}): {args[0]}")
        return CommandResult("", "", returncode)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _link(path: Path, target: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.symlink_to(target)


def _healthy_state(monkeypatch: pytest.MonkeyPatch, home: Path) -> tuple[State, DoctorRunner]:
    monkeypatch.setenv("HOME", str(home))
    persona = home / ".agents/AGENTS.md"
    skills = home / ".agents/skills"
    _write(persona, "# Shared persona\n")
    skills.mkdir(mode=0o700, parents=True)

    for path in (
        home / ".gemini/GEMINI.md",
        home / ".claude/CLAUDE.md",
        home / ".codex/AGENTS.md",
        home / ".grok/AGENTS.md",
        home / ".copilot/copilot-instructions.md",
    ):
        _link(path, persona)
    for path in (home / ".gemini/config/skills", home / ".claude/skills", home / ".grok/skills"):
        _link(path, skills)

    _write(
        home / ".gemini/config/hooks.json",
        json.dumps(
            {
                "hooks": [
                    "dot agent hook session agy",
                    "dot agent hook notify agy stop",
                    "dot agent hook usage agy",
                ]
            }
        ),
    )
    _write(
        home / ".claude/settings.json",
        json.dumps(
            {
                "hooks": [
                    "dot agent hook session claude",
                    "dot agent hook notify claude stop",
                    "dot agent hook usage claude",
                ]
            }
        ),
    )
    _write(
        home / ".codex/config.toml",
        "".join(
            f'[[hooks]]\ncommand = "{command}"\n'
            for command in (
                "dot agent hook session codex",
                "dot agent hook notify codex stop",
                "dot agent hook usage codex",
            )
        ),
    )
    _write(
        home / ".grok/hooks/hooks.json",
        json.dumps(
            {
                "hooks": [
                    "dot agent hook session grok",
                    "dot agent hook notify grok stop",
                    "dot agent hook usage grok",
                ]
            }
        ),
    )
    _write(
        home / ".copilot/hooks/session-log.json",
        json.dumps(
            {
                "version": 1,
                "hooks": ["dot agent hook copilot-session-end", "dot agent hook usage copilot"],
            }
        ),
    )
    runner = DoctorRunner()
    state = State(runner=runner, stdout=io.StringIO(), stderr=io.StringIO())
    state.__dict__["_config"] = Config()
    return state, runner


def _result(state: State, agent: str):
    return next(result for result in gather_agent_doctor(state) if result.agent == agent)


def test_doctor_reports_all_current_integrations_without_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)

    results = run_agent_doctor(state)

    assert [result.agent for result in results] == ["agy", "claude", "codex", "grok", "copilot"]
    assert all(result.healthy for result in results)
    assert isinstance(state.stdout, io.StringIO)
    report = state.stdout.getvalue()
    assert "Shared persona" not in report
    assert "transcript" not in report
    assert "ingestion=none" in report


def test_doctor_fails_closed_across_discovery_hooks_tools_and_command_surface(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state, runner = _healthy_state(monkeypatch, tmp_path)
    (tmp_path / ".claude/CLAUDE.md").unlink()
    _write(tmp_path / ".codex/config.toml", "[")
    runner.tools.remove("grok")
    runner.unavailable_commands.add(("/tools/dot", "agent", "hook", "usage", "--help"))

    results = {result.agent: result for result in gather_agent_doctor(state)}

    assert results["claude"].discovery == "persona-broken"
    assert results["codex"].hooks == "malformed"
    assert results["grok"].tools == "grok:missing"
    assert results["agy"].hooks == "command-unavailable"
    assert not all(result.healthy for result in results.values())


def test_doctor_rejects_unarchived_and_truncated_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    source = tmp_path / ".claude/projects"
    _write(source / "session-one.jsonl", "{}\n")

    unarchived = _result(state, "claude")

    assert unarchived.last_ingestion == "none"
    assert not unarchived.healthy

    state.config.agent.doctor.scan_limit = 1
    _write(source / "session-two.jsonl", "{}\n")
    truncated = _result(state, "claude")

    assert truncated.truncated
    assert not truncated.healthy
    with pytest.raises(DotError, match="unhealthy integrations"):
        run_agent_doctor(state)
    assert isinstance(state.stdout, io.StringIO)
    assert "truncated=true" in state.stdout.getvalue()
    assert "omitted=" not in state.stdout.getvalue()


def test_doctor_reconciles_every_file_backed_source_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    source = tmp_path / ".claude/projects"
    older = source / "older.jsonl"
    archived = source / "archived.jsonl"
    _write(older, '{"session":"older"}\n')
    _write(archived, '{"session":"archived"}\n')
    old = datetime.now(UTC) - timedelta(hours=1)
    os.utime(older, (old.timestamp(), old.timestamp()))
    ingest_session(
        "claude",
        "archived",
        [SessionLog("2026-09-01T00:00:00Z", "claude", "archived", "user", "private")],
        SessionSource(fingerprint=fingerprint_file(archived)),
    )

    result = _result(state, "claude")

    assert result.source == "unreconciled"
    assert result.archive_lag == "unknown"
    assert not result.healthy


def test_doctor_fails_closed_if_source_changes_during_archive_reconciliation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    source = tmp_path / ".claude/projects/session.jsonl"
    _write(source, "original source\n")
    archived = ingest_session(
        "claude",
        "session",
        [SessionLog("2026-09-01T00:00:00Z", "claude", "session", "user", "private")],
        SessionSource(fingerprint=fingerprint_file(source)),
    )
    assert archived.status == "ingested"
    original_mtime = source.stat().st_mtime_ns
    real_stored_generation = agent_module.stored_generation
    mutated = False

    def mutate_source(agent: str, session_id: str, fingerprint: str):
        nonlocal mutated
        source.write_text("modified source\n")
        os.utime(source, ns=(original_mtime, original_mtime))
        mutated = True
        return real_stored_generation(agent, session_id, fingerprint)

    monkeypatch.setattr(agent_module, "stored_generation", mutate_source)

    result = _result(state, "claude")

    assert mutated
    assert result.source == "unreadable"
    assert not result.healthy


def test_doctor_rejects_database_source_with_directory_kind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    source = tmp_path / ".copilot/session-store.db"
    source.mkdir(parents=True)

    result = _result(state, "copilot")

    assert result.source == "wrong-kind"
    assert not result.healthy


def test_doctor_validates_complete_partial_and_corrupt_archive_lineage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    complete = ingest_session(
        "claude",
        "complete",
        [SessionLog("2026-09-01T00:00:00Z", "claude", "complete", "user", "private")],
        SessionSource(fingerprint="a" * 64),
    )
    assert _result(state, "claude").healthy

    generation = session_store_root() / "claude" / complete.lineage_id / complete.generation_id
    manifest_path = generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["lineage_id"] = "wrong"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    corrupt = _result(state, "claude")
    assert corrupt.last_ingestion == "unreadable"
    assert not corrupt.healthy

    ingest_session(
        "codex",
        "partial",
        [SessionLog("2026-09-01T00:00:00Z", "codex", "partial", "user", "private")],
        SessionSource(fingerprint="b" * 64, completeness="partial"),
    )
    partial = _result(state, "codex")
    assert partial.last_ingestion == "partial-only"
    assert not partial.healthy


@pytest.mark.parametrize("damage", ["missing", "hash-mismatch", "public"])
def test_doctor_rejects_invalid_archive_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, damage: str
) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    archived = ingest_session(
        "claude",
        damage,
        [SessionLog("2026-09-01T00:00:00Z", "claude", damage, "user", "private")],
        SessionSource(fingerprint="d" * 64),
    )
    generation = session_store_root() / "claude" / archived.lineage_id / archived.generation_id
    transcript = generation / "transcript.jsonl"
    if damage == "missing":
        transcript.unlink()
    elif damage == "hash-mismatch":
        transcript.write_text("{}\n", encoding="utf-8")
    else:
        transcript.chmod(0o644)

    result = _result(state, "claude")

    assert result.last_ingestion == "unreadable"
    assert not result.healthy


def test_doctor_reports_bounded_hook_failure_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    spool = tmp_path / ".agents/hook-failures/v1"
    _write(spool / "20260902T000000Z-empty.json", "")
    _write(
        spool / "20260901T000000Z-record.json",
        json.dumps(
            {
                "occurred_at": "2026-09-01T00:00:00Z",
                "agent": "claude",
                "operation": "session",
                "detail": "secret failure detail",
            }
        ),
    )

    result = _result(state, "claude")

    assert result.last_failure == "2026-09-01T00:00:00Z:session"
    assert "secret" not in repr(result)


def test_doctor_calculates_stale_lag_without_exposing_archive_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state, _ = _healthy_state(monkeypatch, tmp_path)
    result = ingest_session(
        "claude",
        "stale",
        [SessionLog("2026-09-01T00:00:00Z", "claude", "stale", "user", "must-not-appear")],
        SessionSource(fingerprint="c" * 64),
    )
    generation = session_store_root() / "claude" / result.lineage_id / result.generation_id
    manifest_path = generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ingested = datetime.now(UTC) - timedelta(hours=72)
    manifest["ingested_at"] = ingested.isoformat().replace("+00:00", "Z")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source = tmp_path / ".claude/projects/stale.jsonl"
    _write(source, "new private source")
    os.utime(source, (datetime.now(UTC).timestamp(), datetime.now(UTC).timestamp()))

    doctor = _result(state, "claude")

    assert doctor.archive_lag != "0s"
    assert not doctor.healthy
    assert "must-not-appear" not in repr(doctor)
    assert "new private source" not in repr(doctor)


def test_repair_is_explicit_bounded_and_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, runner = _healthy_state(monkeypatch, tmp_path)

    with pytest.raises(DotError, match="--dry-run requires --fix"):
        run_agent_doctor(state, dry_run=True)

    repair_agent_integrations(state, dry_run=True)
    first = runner.calls[-1]
    repair_agent_integrations(state, dry_run=True)

    assert runner.calls[-1] == first
    assert first[:3] == ("chezmoi", "apply", "--dry-run")
    assert first[3] == "--force"
    assert str(tmp_path / ".gemini/GEMINI.md") in first
    assert str(tmp_path / ".claude/CLAUDE.md") in first


def test_doctor_cli_exposes_fix_and_preview_flags() -> None:
    result = CliRunner().invoke(app, ["agent", "doctor", "--help"])

    assert result.exit_code == 0
    output = _click.utils.strip_ansi(result.stdout)
    assert "--fix" in output
    assert "--dry-run" in output
