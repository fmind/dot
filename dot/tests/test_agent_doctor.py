"""Agent doctor: notify hooks, session sync, and archive readability per agent."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import IO

import pytest
from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from fmind_dot.agent_doctor import gather_agent_doctor, run_agent_doctor
from fmind_dot.archive.store import SessionLog, ingest_session, session_store_root
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.state import State


def _text(stream: IO[str]) -> str:
    assert isinstance(stream, io.StringIO)
    return stream.getvalue()


NOTIFY = {
    "agy": ["stop"],
    "claude": ["needs-input", "stop"],
    "codex": ["stop"],
    "grok": ["needs-input", "stop"],
    "copilot": ["stop"],
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _configure_hooks(home: Path, binary: str = "dot") -> None:
    def commands(agent: str) -> list[str]:
        return [f"{binary} agent hook notify {agent} {event}" for event in NOTIFY[agent]]

    _write(home / ".gemini/config/hooks.json", json.dumps({"notify": {"Stop": [{"command": commands("agy")[0]}]}}))
    _write(
        home / ".claude/settings.json",
        json.dumps({"hooks": {"Stop": [{"hooks": [{"command": command} for command in commands("claude")]}]}}),
    )
    _write(home / ".codex/config.toml", f'[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ncommand = "{commands("codex")[0]}"\n')
    _write(
        home / ".grok/hooks/hooks.json",
        json.dumps({"hooks": {"Stop": [{"hooks": [{"command": command} for command in commands("grok")]}]}}),
    )
    _write(
        home / ".copilot/hooks/session-log.json",
        json.dumps({"version": 1, "hooks": {"agentStop": [{"bash": commands("copilot")[0]}]}}),
    )


def _state(monkeypatch: pytest.MonkeyPatch, home: Path) -> State:
    monkeypatch.setenv("HOME", str(home))
    _configure_hooks(home)
    state = State(stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())
    for agent in state.config.agent.sources:
        state.config.agent.sources[agent] = str(home / "sources" / agent)
    return state


def _claude_source(state: State, session_id: str = "fixture-id") -> Path:
    source = Path(state.config.agent.sources["claude"]) / f"{session_id}.jsonl"
    _write(
        source,
        json.dumps({"type": "user", "timestamp": "2026-09-01T10:00:00Z", "message": {"content": "private prompt"}})
        + "\n",
    )
    return source


def test_doctor_reports_three_checks_per_agent_without_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    _claude_source(state)
    sync_sessions(state, agent="claude")

    results = {result.agent: result for result in run_agent_doctor(state)}

    assert list(results) == ["agy", "claude", "codex", "grok", "copilot"]
    claude = results["claude"]
    assert (claude.hooks, claude.source, claude.archive, claude.sessions, claude.sync_failures) == (
        "configured",
        "present",
        "readable",
        1,
        0,
    )
    assert claude.last_sync.endswith("Z")
    # A missing provider store needs no sync; an unused agent is healthy.
    assert (results["codex"].source, results["codex"].last_sync, results["codex"].healthy) == ("missing", "never", True)
    assert "private prompt" not in _text(state.stdout)


def test_doctor_asks_for_sync_when_a_present_source_was_never_synced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _state(monkeypatch, tmp_path)
    _claude_source(state)

    with pytest.raises(DotError, match="unhealthy"):
        run_agent_doctor(state, agent="claude")

    assert "✗ claude: hooks=configured source=present last_sync=never" in _text(state.stdout)
    assert "next: dot agent session sync --agent claude" in _text(state.stdout)


@pytest.mark.parametrize(
    ("content", "status"),
    [
        (None, "absent"),
        ("{", "malformed"),
        (json.dumps({"hooks": {}}), "missing:needs-input,stop"),
        (json.dumps({"hooks": ["dot agent hook notify claude stop"]}), "missing:needs-input"),
        (json.dumps({"hooks": ["/usr/bin/graphviz agent hook notify claude stop"]}), "missing:needs-input,stop"),
        (
            json.dumps(
                {
                    "hooks": [
                        "dot agent hook notify claude stop",
                        "dot agent hook notify claude needs-input",
                        "dot agent hook session claude",
                    ]
                }
            ),
            "retired-capture-hook",
        ),
    ],
)
def test_doctor_reads_notify_hooks_statically(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str | None, status: str
) -> None:
    state = _state(monkeypatch, tmp_path)
    settings = tmp_path / ".claude/settings.json"
    if content is None:
        settings.unlink()
    else:
        settings.write_text(content)

    [result] = gather_agent_doctor(state, agent="claude")

    assert result.hooks == status
    assert not result.healthy
    assert result.next.startswith("chezmoi diff ~/.claude/settings.json")


def test_doctor_accepts_an_absolute_dot_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    _configure_hooks(tmp_path, binary=str(tmp_path / ".local/bin/dot"))

    assert {result.hooks for result in gather_agent_doctor(state)} == {"configured"}


def test_doctor_reports_unreadable_archives_and_failed_syncs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    ingest_session("claude", "readable", [SessionLog("2026-09-01T10:00:00Z", "claude", "readable", "user", "hi")])
    (session_store_root() / "claude/broken.jsonl").write_text("{}\n")
    sync_state = session_store_root() / "codex/.sync.json"
    sync_state.parent.mkdir()
    sync_state.write_text(
        json.dumps({"schema": "dot.agent.session.sync-state/v1", "synced_at": "2026-09-01T10:00:00Z", "failed": 2})
    )
    (tmp_path / "sources/codex").mkdir(parents=True)

    results = {result.agent: result for result in gather_agent_doctor(state)}

    assert (results["claude"].archive, results["claude"].sessions, results["claude"].healthy) == (
        "unreadable:1",
        1,
        False,
    )
    assert (results["codex"].sync_failures, results["codex"].healthy) == (2, False)
    assert results["codex"].next == "dot agent session sync --agent codex"


def test_doctor_json_is_a_diagnostic_envelope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)

    run_agent_doctor(state, as_json=True, agent="grok")

    document = json.loads(_text(state.stdout))
    assert document["schema"] == "dot.diagnostics/v1"
    assert document["passed"] is True
    assert [check["name"] for check in document["checks"]] == ["grok"]
    assert document["checks"][0]["details"]["hooks"] == "configured"


def test_doctor_cli_keeps_only_json_and_agent_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = get_command(app)
    assert isinstance(root, TyperGroup)
    agent = root.commands["agent"]
    assert isinstance(agent, TyperGroup)
    doctor = agent.commands["doctor"]
    options = {option for parameter in doctor.params for option in parameter.opts}
    assert options == {"--agent", "--harness", "-a", "--json", "-j"}
    for removed in ("--fix", "--dry-run", "--deep", "--explain"):
        assert CliRunner().invoke(app, ["agent", "doctor", removed]).exit_code == 2
    unknown = CliRunner().invoke(app, ["agent", "doctor", "--agent", "opencode"])
    assert unknown.exit_code == 1
    assert "unknown agent 'opencode'" in str(unknown.exception)
