"""Public CLI regression cases for the simplified command contract."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive.store import SessionLog, ingest_session
from fmind_dot.archive.usage import UsageRecord
from fmind_dot.cli import app


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)


@pytest.mark.parametrize("command", [["pull"], ["agent", "stats"], ["login", "google"]])
def test_help_works_with_invalid_config(command: list[str], tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text("pull:\n  typo: true\n")
    result = CliRunner().invoke(app, ["--config", str(config), *command, "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ["pull", "--dirty", "typo"],
        ["agent", "session", "show"],
        ["agent", "stats", "--since", "invalid"],
        ["agent", "stats", "--since", "2026-09-16", "--until", "2026-09-15"],
        ["agent", "usage", "list", "--limit", "-1"],
        ["agent", "session", "list", "--limit", "-1"],
        ["agent", "stats", "--tokens-only", "--prompts-only"],
        ["agent", "stats", "--monthly", "--billing"],
        ["agent", "doctor", "--dry-run"],
    ],
)
def test_usage_errors_exit_two(arguments: list[str]) -> None:
    assert CliRunner().invoke(app, arguments).exit_code == 2


def test_reports_include_whole_until_day_and_exact_timestamp() -> None:
    for identity, timestamp in [("day", "2026-09-15T12:00:00Z"), ("next", "2026-09-16T00:00:00Z")]:
        usage = UsageRecord(timestamp=timestamp, harness="codex", session_id=identity, input_tokens=10).finalize(
            fallback_timestamp="2026-09-01T00:00:00Z"
        )
        ingest_session(
            "codex",
            identity,
            [SessionLog(timestamp, "codex", identity, "user", "hello", "/work")],
            usage=usage.to_dict(),
        )
    runner = CliRunner()
    for command in [["agent", "stats"], ["agent", "stats", "--prompts-only"], ["agent", "stats", "--tokens-only"]]:
        result = runner.invoke(app, [*command, "--since", "2026-09-15", "--until", "2026-09-15", "--json"])
        assert result.exit_code == 0, result.output
        document = json.loads(result.stdout)
        assert document["schema"] == "dot.agent.stats/v2"
        if document["prompts"] is not None:
            assert document["prompts"]["prompts"] == 1
        if document["usage"]:
            assert document["usage"][0]["total_tokens"] == 10
    result = runner.invoke(app, ["agent", "stats", "--until", "2026-09-15T00:00:00Z", "--json"])
    document = json.loads(result.stdout)
    assert document["prompts"]["prompts"] == 0
    assert document["usage"] == []


def test_removed_cleanup_cannot_delete_retained_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = tmp_path / ".agents/reports/design.md"
    report.parent.mkdir(parents=True)
    report.write_text("retained work")
    result = CliRunner().invoke(app, ["agent", "clean", "--apply"])
    assert result.exit_code == 2
    assert report.read_text() == "retained work"


def test_google_login_dry_run_names_its_scope() -> None:
    result = CliRunner().invoke(app, ["login", "google", "--dry-run"])
    assert result.exit_code == 0
    assert "gws auth login" in result.stdout
    assert "gcloud auth login" in result.stdout
    assert "gh auth" not in result.stdout


@pytest.mark.parametrize("command", [["agent", "prompts", "stats"], ["agent", "usage", "stats"]])
def test_removed_report_routes_are_usage_errors(command: list[str]) -> None:
    result = CliRunner().invoke(app, [*command, "--json"])
    assert result.exit_code == 2
    assert result.stdout == ""


@pytest.mark.parametrize("flag", ["--agent", "--harness", "-a"])
def test_agent_filter_aliases_select_the_same_usage(flag: str) -> None:
    for agent in ["codex", "claude"]:
        record = UsageRecord(
            timestamp="2026-09-15T12:00:00Z", harness=agent, session_id=agent, input_tokens=10
        ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
        ingest_session(agent, agent, [], usage=record.to_dict())
    result = CliRunner().invoke(app, ["agent", "usage", "list", flag, "codex", "--limit", "0", "--json"])
    assert result.exit_code == 0
    assert [record["harness"] for record in json.loads(result.stdout)["records"]] == ["codex"]


def test_invalid_config_still_blocks_archive_reads(tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text("pull:\n  typo: true\n")
    result = CliRunner().invoke(app, ["--config", str(config), "agent", "session", "show", "missing"])
    assert result.exit_code == 1
    assert "validation error" in str(result.exception)
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("command", "key"),
    [(["agent", "session", "list"], "sessions"), (["agent", "usage", "list"], "records"), (["pull"], "repositories")],
)
def test_empty_json_has_versioned_envelope(command: list[str], key: str) -> None:
    result = CliRunner().invoke(app, [*command, "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document["schema"].startswith("dot.")
    assert document[key] == []


def test_stats_are_readable_in_a_narrow_terminal_and_preserve_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "60")
    timestamp = "2026-09-15T12:00:00Z"
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        session_id="readable",
        model="unknown-model",
        input_tokens=1234567,
        measurement_kind="provider-reported",
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    ingest_session(
        "codex",
        "readable",
        [SessionLog(timestamp, "codex", "readable", "user", "private words")],
        usage=record.to_dict(),
    )
    runner = CliRunner()
    human = runner.invoke(app, ["agent", "stats", "--by-model"])
    assert human.exit_code == 0, human.output
    assert "Prompt activity" in human.stdout
    assert "Total tokens: 1,234,567" in human.stdout
    assert "API equivalent: unknown" in human.stdout
    assert "Recorded cost: unknown" in human.stdout
    assert "private words" not in human.stdout
    assert "\t" not in human.stdout
    assert max(map(len, human.stdout.splitlines())) <= 60
    document = json.loads(runner.invoke(app, ["agent", "stats", "--by-model", "--json"]).stdout)
    assert document["schema"] == "dot.agent.stats/v2"
    assert document["usage"][0]["total_tokens"] == 1234567
    assert document["usage"][0]["api_equivalent_usd"] is None
    assert document["prompts"]["prompts"] == 1
