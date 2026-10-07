"""Agent doctor: notify hooks, session sync, and archive readability per agent."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

import pytest
from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from fmind_dot.agent_doctor import HOSTS, gather_agent_doctor, run_agent_doctor
from fmind_dot.archive.parsers import AGENT_ADAPTERS
from fmind_dot.archive.store import SESSION_PARSER_VERSION, SessionLog, ingest_session, session_store_root
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.state import State


def _text(stream: IO[str]) -> str:
    assert isinstance(stream, io.StringIO)
    return stream.getvalue()


NOTIFY = {
    "agy": ["stop"],
    "claude": ["needs-input", "ready"],
    "codex": ["stop"],
    "grok": ["needs-input", "ready"],
    "copilot": ["stop"],
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _configure_hooks(home: Path, binary: str = "dot") -> None:
    def commands(agent: str) -> list[str]:
        return [f"{binary} agent hook notify {agent} {event}" for event in NOTIFY[agent]]

    _write(
        home / ".gemini/config/hooks.json",
        json.dumps({"notify": {"Stop": [{"type": "command", "command": commands("agy")[0]}]}}),
    )
    for agent, name in (("claude", ".claude/settings.json"), ("grok", ".grok/hooks/hooks.json")):
        _write(
            home / name,
            json.dumps(
                {
                    "hooks": {
                        "Notification": [
                            {"hooks": [{"type": "command", "command": command} for command in commands(agent)]}
                        ],
                    }
                }
            ),
        )
    _write(home / ".codex/config.toml", "[tui]\nnotifications = true\n")
    _write(home / ".copilot/settings.json", json.dumps({"notifications": True}))


def _configure_discovery(home: Path) -> None:
    """Lay out the shared persona, skills, and per-host links and profiles as chezmoi deploys them."""
    _write(home / ".agents/AGENTS.md", "# Persona\n")
    _write(home / ".agents/skills/sample/SKILL.md", "---\nname: sample\n---\n")
    for persona in (
        ".gemini/GEMINI.md",
        ".claude/CLAUDE.md",
        ".codex/AGENTS.md",
        ".grok/AGENTS.md",
        ".copilot/copilot-instructions.md",
        ".config/opencode/AGENTS.md",
    ):
        (home / persona).parent.mkdir(parents=True, exist_ok=True)
        (home / persona).symlink_to(home / ".agents/AGENTS.md")
    for link in (".gemini/config/skills", ".claude/skills", ".grok/skills"):
        (home / link).parent.mkdir(parents=True, exist_ok=True)
        (home / link).symlink_to(home / ".agents/skills", target_is_directory=True)
    for profile in (
        ".gemini/config/agents/reviewer.md",
        ".claude/agents/reviewer.md",
        ".codex/agents/reviewer.toml",
        ".grok/agents/reviewer.md",
        ".copilot/agents/reviewer.agent.md",
        ".config/opencode/agents/reviewer.md",
    ):
        _write(home / profile, "reviewer\n")


def _state(monkeypatch: pytest.MonkeyPatch, home: Path) -> State:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("OPENCODE_DISABLE_CLAUDE_CODE_SKILLS", "1")
    _configure_hooks(home)
    _configure_discovery(home)
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

    assert list(results) == ["agy", "claude", "codex", "grok", "copilot", "opencode"]
    assert results["opencode"].hooks == "not-required"
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
        (json.dumps({"hooks": {}}), "missing:needs-input,ready"),
        (json.dumps({"hooks": ["dot agent hook notify claude stop"]}), "missing:needs-input,ready"),
        (json.dumps({"hooks": ["/usr/bin/graphviz agent hook notify claude stop"]}), "missing:needs-input,ready"),
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

    assert {result.hooks for result in gather_agent_doctor(state)} == {"configured", "not-required"}


@pytest.mark.parametrize("problem", ["disabled", "wrong-event", "metadata-only", "wrong-type"])
def test_doctor_rejects_inactive_claude_hooks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, problem: str) -> None:
    _state(monkeypatch, tmp_path)
    path = tmp_path / ".claude/settings.json"
    config = json.loads(path.read_text())
    if problem == "disabled":
        config["disableAllHooks"] = True
    elif problem == "wrong-event":
        config["hooks"]["SessionStart"] = config["hooks"].pop("Notification")
    elif problem == "metadata-only":
        config["description"] = config.pop("hooks")
    else:
        config["hooks"]["Notification"][0]["hooks"][1]["type"] = "prompt"
    path.write_text(json.dumps(config))

    outcome = CliRunner().invoke(app, ["agent", "doctor", "--agent", "claude", "--json"])

    assert outcome.exit_code == 1
    document = json.loads(outcome.stdout)
    assert document["passed"] is False
    details = document["checks"][0]["details"]
    assert details["healthy"] is False
    assert details["hooks"] == (
        "disabled"
        if problem == "disabled"
        else {
            "wrong-event": "missing:needs-input,ready",
            "metadata-only": "missing:needs-input,ready",
            "wrong-type": "missing:ready",
        }[problem]
    )
    if problem == "disabled":
        assert "disableAllHooks" in details["next"]


@pytest.mark.parametrize("feature", ["hooks", "codex_hooks"])
def test_doctor_native_codex_notifications_do_not_require_hooks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, feature: str
) -> None:
    state = _state(monkeypatch, tmp_path)
    path = tmp_path / ".codex/config.toml"
    path.write_text(f"[features]\n{feature} = false\n" + path.read_text())

    [result] = gather_agent_doctor(state, agent="codex")

    assert result.hooks == "configured"
    assert result.healthy


@pytest.mark.parametrize("agent", ["codex", "copilot"])
def test_doctor_requires_native_attention_notifications(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str
) -> None:
    state = _state(monkeypatch, tmp_path)
    if agent == "codex":
        (tmp_path / ".codex/config.toml").write_text("[tui]\nnotifications = false\n")
    else:
        (tmp_path / ".copilot/settings.json").write_text('{"notifications": false}')
    [result] = gather_agent_doctor(state, agent=agent)
    assert result.hooks == "disabled"
    assert not result.healthy
    assert "notifications" in result.next


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
    unknown = CliRunner().invoke(app, ["agent", "doctor", "--agent", "unsupported"])
    assert unknown.exit_code == 2
    assert "'unsupported' is not one of" in unknown.stderr


def test_doctor_reports_retained_sessions_without_failing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    sync_state = session_store_root() / "grok/.sync.json"
    sync_state.parent.mkdir(parents=True, exist_ok=True)
    sync_state.write_text(
        json.dumps(
            {
                "schema": "dot.agent.session.sync-state/v1",
                "synced_at": "2026-09-01T10:00:00Z",
                "failed": 0,
                "retained": 3,
            }
        )
    )

    results = run_agent_doctor(state, agent="grok")

    assert (results[0].sync_retained, results[0].sync_failures) == (3, 0)
    assert (
        "note: 3 session(s) kept their archived copy (truncated source or a parse that would lose usage); "
        "dot agent session sync --agent grok reports each one"
    ) in _text(state.stdout)


@pytest.mark.parametrize("retained", [-1, True, "3"], ids=["negative", "boolean", "string"])
def test_doctor_rejects_an_invalid_retained_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, retained: object
) -> None:
    state = _state(monkeypatch, tmp_path)
    sync_state = session_store_root() / "grok/.sync.json"
    sync_state.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema": "dot.agent.session.sync-state/v1", "synced_at": "2026-09-01T10:00:00Z", "failed": 0}
    sync_state.write_text(json.dumps({**document, "retained": retained}))

    (result,) = gather_agent_doctor(state, agent="grok")

    assert (result.last_sync, result.sync_retained) == ("unreadable", 0)
    assert not result.healthy
    assert result.next == "dot agent session sync --agent grok"


@pytest.mark.parametrize("timestamp", ["", "invalid", "2026-09-01", "2026-09-01T10:00:00"])
@pytest.mark.parametrize("source_present", [False, True])
def test_doctor_rejects_invalid_sync_timestamps_even_without_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timestamp: str, source_present: bool
) -> None:
    state = _state(monkeypatch, tmp_path)
    if source_present:
        Path(state.config.agent.sources["grok"]).mkdir(parents=True)
    sync_state = session_store_root() / "grok/.sync.json"
    sync_state.parent.mkdir(parents=True)
    sync_state.write_text(
        json.dumps({"schema": "dot.agent.session.sync-state/v1", "synced_at": timestamp, "failed": 0})
    )

    with pytest.raises(DotError, match="unhealthy"):
        run_agent_doctor(state, agent="grok", as_json=True)

    report = json.loads(_text(state.stdout))
    assert report["passed"] is False
    assert report["checks"][0]["details"]["last_sync"] == "unreadable"


@pytest.mark.parametrize("parser_version", [None, "9"], ids=["unversioned", "previous-parser"])
@pytest.mark.parametrize("source_present", [False, True])
def test_doctor_reports_a_sync_by_another_parser_as_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, parser_version: str | None, source_present: bool
) -> None:
    state = _state(monkeypatch, tmp_path)
    if source_present:
        Path(state.config.agent.sources["grok"]).mkdir(parents=True)
    document = {"schema": "dot.agent.session.sync-state/v1", "synced_at": "2026-09-01T10:00:00Z", "failed": 0}
    if parser_version:
        document["parser_version"] = parser_version
    sync_state = session_store_root() / "grok/.sync.json"
    sync_state.parent.mkdir(parents=True)
    sync_state.write_text(json.dumps(document))

    (result,) = gather_agent_doctor(state, agent="grok")

    assert result.last_sync == "stale"
    # A missing source has nothing to recapture.
    assert result.healthy is not source_present
    assert result.next == ("dot agent session sync --agent grok" if source_present else "")


@pytest.mark.parametrize(
    ("notifications", "status"),
    [
        ('["agent-turn-complete", "approval-requested"]', "configured"),
        ("[]", "disabled"),
        ("[1]", "disabled"),
        ('"agent-turn-complete"', "disabled"),
    ],
)
def test_doctor_accepts_codex_notification_type_lists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, notifications: str, status: str
) -> None:
    state = _state(monkeypatch, tmp_path)
    (tmp_path / ".codex/config.toml").write_text(f"[tui]\nnotifications = {notifications}\n")

    (result,) = gather_agent_doctor(state, agent="codex")

    assert result.hooks == status


def test_doctor_reports_deeply_nested_settings_as_malformed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    (tmp_path / ".copilot/settings.json").write_text("[" * 1_000_000 + "]" * 1_000_000)

    (result,) = gather_agent_doctor(state, agent="copilot")

    assert result.hooks == "malformed"


def _sync_state(
    agent: str, name: str, synced_at: str, *, failed: int = 0, retained: int = 0, parser: str = SESSION_PARSER_VERSION
) -> None:
    path = session_store_root() / agent / name
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema": "dot.agent.session.sync-state/v1", "synced_at": synced_at, "failed": failed}
    path.write_text(json.dumps(document | {"retained": retained, "parser_version": parser}))


def test_windowed_sync_refreshes_last_sync_without_replacing_the_complete_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _state(monkeypatch, tmp_path)
    _claude_source(state)
    sync_sessions(state, agent="claude")
    complete = session_store_root() / "claude/.sync.json"
    _sync_state("claude", ".sync.json", "2026-09-01T10:00:00Z")
    before = complete.read_bytes()

    window_path = session_store_root() / "claude/.sync-window.json"
    # Session-filtered or dry passes prove nothing about the agent and record no state.
    sync_sessions(state, agent="claude", session="fixture-id", since=datetime(2026, 9, 1, tzinfo=UTC))
    sync_sessions(state, agent="claude", since=datetime(2026, 9, 1, tzinfo=UTC), dry_run=True)
    assert not window_path.exists()

    sync_sessions(state, agent="claude", since=datetime(2026, 9, 1, tzinfo=UTC))

    assert complete.read_bytes() == before
    window = json.loads(window_path.read_text())
    assert (window["failed"], window["since"]) == (0, "2026-09-01T00:00:00Z")
    (claude,) = gather_agent_doctor(state, agent="claude")
    assert (claude.last_sync, claude.healthy) == (window["synced_at"], True)


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        ({"synced_at": "2026-09-02T10:00:00Z"}, ("2026-09-02T10:00:00Z", 1, 2)),
        ({"synced_at": "2026-09-02T10:00:00Z", "failed": 3, "retained": 5}, ("2026-09-02T10:00:00Z", 3, 5)),
        ({"synced_at": "2026-08-31T10:00:00Z", "failed": 3, "retained": 5}, ("2026-09-01T10:00:00Z", 1, 2)),
        ({"synced_at": "2026-09-02T10:00:00Z", "parser": "1"}, ("2026-09-01T10:00:00Z", 1, 2)),
        ({"synced_at": "invalid"}, ("2026-09-01T10:00:00Z", 1, 2)),
    ],
    ids=["newer", "newer-counts", "older", "other-parser", "unreadable"],
)
def test_doctor_reports_the_newest_sync_and_keeps_complete_pass_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, window: dict[str, object], expected: tuple[str, int, int]
) -> None:
    state = _state(monkeypatch, tmp_path)
    _sync_state("grok", ".sync.json", "2026-09-01T10:00:00Z", failed=1, retained=2)
    _sync_state(
        "grok",
        ".sync-window.json",
        str(window["synced_at"]),
        failed=int(str(window.get("failed", 0))),
        retained=int(str(window.get("retained", 0))),
        parser=str(window.get("parser", SESSION_PARSER_VERSION)),
    )

    (result,) = gather_agent_doctor(state, agent="grok")

    assert (result.last_sync, result.sync_failures, result.sync_retained) == expected


@pytest.mark.parametrize("complete", [None, "9"], ids=["never", "stale"])
def test_doctor_requires_a_complete_pass_despite_windowed_syncs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, complete: str | None
) -> None:
    state = _state(monkeypatch, tmp_path)
    Path(state.config.agent.sources["grok"]).mkdir(parents=True)
    if complete:
        _sync_state("grok", ".sync.json", "2026-09-01T10:00:00Z", parser=complete)
    _sync_state("grok", ".sync-window.json", "2026-09-02T10:00:00Z")

    (result,) = gather_agent_doctor(state, agent="grok")

    assert (result.last_sync, result.healthy) == ("stale" if complete else "never", False)
    assert result.next == "dot agent session sync --agent grok"


def test_doctor_reports_broken_discovery_per_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = _state(monkeypatch, tmp_path)
    (tmp_path / ".grok/skills").unlink()
    (tmp_path / ".grok/skills").mkdir()
    (tmp_path / ".codex/AGENTS.md").unlink()
    (tmp_path / ".copilot/agents/reviewer.agent.md").unlink()

    with pytest.raises(DotError, match="unhealthy"):
        run_agent_doctor(state)

    results = {result.agent: result for result in gather_agent_doctor(state)}
    assert results["grok"].discovery == "broken:skills"
    assert results["codex"].discovery == "broken:persona"
    assert results["copilot"].discovery == "broken:agents"
    assert results["claude"].discovery == "ok"
    assert "chezmoi apply --force" in results["grok"].next


def test_doctor_notes_opencode_duplicate_skills_without_failing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = _state(monkeypatch, tmp_path)
    monkeypatch.delenv("OPENCODE_DISABLE_CLAUDE_CODE_SKILLS")

    result = gather_agent_doctor(state, agent="opencode")[0]

    # The caller's environment is not OpenCode's, so the opt-out is advisory only.
    assert (result.discovery, result.healthy, result.next) == ("ok", True, "")
    assert "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1" in result.note
    run_agent_doctor(state, agent="opencode")
    assert "  note: this environment lacks OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1" in _text(state.stdout)


def test_every_agent_adapter_has_one_host_deployment_and_notification_label() -> None:
    assert list(HOSTS) == list(AGENT_ADAPTERS)
    assert all(adapter.notify_label for adapter in AGENT_ADAPTERS.values())
