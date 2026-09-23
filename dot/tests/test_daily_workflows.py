from __future__ import annotations

import io
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dot_tasks import release as maintenance
from fmind_dot import repository
from fmind_dot.archive import parsers as agent_parsers
from fmind_dot.archive.query import SessionQuery, query_session_summaries, show_session
from fmind_dot.archive.statistics import prompt_statistics, session_statistics
from fmind_dot.archive.store import SessionLog, SessionSource, ingest_session, session_bundle_path
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, write_usage_stats
from fmind_dot.cli import app
from fmind_dot.config import Config, PullConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


def state_with(config: Config | None = None) -> State:
    state = State(stdout=io.StringIO(), stderr=io.StringIO(), stdin=io.StringIO())
    state.__dict__["_config"] = config or Config()
    return state


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_jsonl_unicode_preserves_valid_conversation(separator: str, tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    content = f"private{separator}message"
    raw = {
        "type": "response_item",
        "timestamp": "2026-09-09T10:00:00Z",
        "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": content}]},
    }
    path.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")
    parsed = agent_parsers.parse_codex_session(path, "test-session")
    assert parsed.malformed == 0
    assert [log.content for log in parsed.logs] == [content]


def test_recaptured_sessions_and_statistics_do_not_double_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [
        SessionLog("2026-09-01T10:00:00Z", "codex", "example", "user", "private two words", "/work"),
        SessionLog("2026-09-01T10:00:01Z", "codex", "example", "assistant", "private answer", "/work"),
    ]
    ingest_session("codex", "example", logs, SessionSource(fingerprint="b" * 64, skipped=4))
    ingest_session("codex", "example", logs, SessionSource(fingerprint="a" * 64, skipped=4))
    assert len(query_session_summaries()) == 1
    assert show_session(SessionQuery(identity="example"), include_content=True).records == logs
    archive = session_statistics(SessionQuery())
    assert archive["schema"] == "dot.agent.sessions.stats/v2"
    assert archive["sessions"] == 1
    assert archive["ignored_records"] == 4
    assert archive["archive_bytes"] == session_bundle_path("codex", "example").stat().st_size
    assert "generations" not in archive
    prompts = prompt_statistics(
        SessionQuery(since=datetime(2026, 9, 1, tzinfo=UTC), until=datetime(2026, 9, 2, tzinfo=UTC))
    )
    assert prompts["prompts"] == 1
    assert prompts["rows"][0]["words"] == 3
    assert prompts["rows"][0]["responses"] == 1
    assert "private" not in json.dumps(prompts)
    assert prompt_statistics(SessionQuery(since=datetime(2026, 9, 3, tzinfo=UTC)))["prompts"] == 0


def test_project_dot_and_prompt_json_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    ingest_session(
        "codex",
        "project",
        [SessionLog("2026-09-09T10:00:00Z", "codex", "project", "user", "hidden text", str(tmp_path))],
    )
    runner = CliRunner()
    listing = runner.invoke(app, ["agent", "session", "list", "--project", ".", "--json"])
    assert listing.exit_code == 0
    assert len(json.loads(listing.stdout)["sessions"]) == 1
    result = runner.invoke(app, ["agent", "stats", "--prompts-only", "--project", ".", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["prompts"]["prompts"] == 1
    assert "hidden text" not in result.stdout


def test_mixed_models_unknown_cost_and_comparable_statistics(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    rows = []
    for model, total in (("first", 100), ("second", 150)):
        rows.extend(
            [
                {"type": "turn_context", "payload": {"model": model}},
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"total_token_usage": {"input_tokens": total, "total_tokens": total}},
                    },
                },
            ]
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    record = agent_parsers.parse_codex_session(path, "example").usage
    assert record is not None
    assert record.model == "mixed"
    assert record.total_tokens == 150
    assert record.to_dict()["cost_usd"] is None
    estimate = UsageRecord(
        harness="agy", session_id="estimate", measurement_kind="estimated", total_tokens=50
    ).finalize(fallback_timestamp="2026-09-01T00:00:00Z")
    stats = aggregate_usage([record, estimate], by_model=True)
    output = io.StringIO()
    write_usage_stats(output, stats, by_model=True)
    assert "unknown" in output.getvalue()
    assert "No combined total" in output.getvalue()
    assert all(row.to_dict()["cost_usd"] is None for row in stats)


def git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, text=True, capture_output=True).stdout


def test_real_repository_selection_and_attention_statistics(tmp_path: Path) -> None:
    checkout = tmp_path / "repository"
    checkout.mkdir()
    git(checkout, "init", "-b", "main")
    git(
        checkout,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "fixture",
    )
    git(checkout, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(checkout, "config", "remote.origin.url", str(tmp_path / "nonexistent-remote"))
    git(checkout, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
    git(checkout, "config", "branch.main.remote", "origin")
    git(checkout, "config", "branch.main.merge", "refs/heads/main")
    git(
        checkout,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "ahead",
    )
    state = state_with(Config(pull=PullConfig(directories=[str(checkout)])))
    assert repository.find_git_repositories(state) == [checkout]
    report = repository.run_status(state, paths=[checkout], as_json=True, stats=True)
    assert report[0].ahead == 1
    assert isinstance(state.stdout, io.StringIO)
    assert json.loads(state.stdout.getvalue())["ahead"] == 1
    state.stdout = io.StringIO()
    repository.run_pull(state, paths=[checkout], dry_run=True, as_json=True)
    assert json.loads(state.stdout.getvalue())["repositories"] == [str(checkout)]
    assert not (checkout / ".git/FETCH_HEAD").exists()
    (checkout / "dirty.txt").write_text("local changes", encoding="utf-8")
    state.stdout = io.StringIO()
    result = repository.run_pull(state, paths=[checkout], as_json=True)
    assert result[0].skipped == "dirty worktree"
    assert not (checkout / ".git/FETCH_HEAD").exists()


def test_status_failure_remains_json_and_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    status = [repository.RepositoryStatus("repo", "work", error="inspection failed")]
    monkeypatch.setattr(repository, "gather_status", lambda *_args: status)
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code != 0
    assert json.loads(result.stdout)["complete"] is False


def test_targeted_sync_preview_preserves_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / "claude"
    source.mkdir()
    (source / "selected.jsonl").write_text(
        json.dumps({"type": "user", "timestamp": "2026-09-01T10:00:00Z", "message": {"content": "hidden"}}) + "\n",
        encoding="utf-8",
    )
    state = state_with()
    state.config.agent.sources["claude"] = str(source)
    assert sync_sessions(state, agent="claude", session="selected", dry_run=True, as_json=True).selected == 1
    assert isinstance(state.stdout, io.StringIO)
    assert json.loads(state.stdout.getvalue())["selected"] == 1
    assert not (tmp_path / ".agents/sessions").exists()
    with pytest.raises(DotError, match="unknown"):
        sync_sessions(state, agent="typo")


@pytest.mark.parametrize("alias", ["direct", "parent", "symlink"])
def test_managed_config_edit_routes_to_source_and_validates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, alias: str
) -> None:
    config = tmp_path / "dot.yaml"
    config.write_text("{}\n")
    selected = config
    if alias == "parent":
        (tmp_path / "nested").mkdir()
        selected = tmp_path / "nested/../dot.yaml"
    elif alias == "symlink":
        selected = tmp_path / "linked.yaml"
        selected.symlink_to(config)
    calls = []
    monkeypatch.setattr(Runner, "which", lambda _self, name: Path("/tools") / name)

    def inventory(_self, args, **_kwargs):
        assert args == ["chezmoi", "managed", "--path-style=absolute", "--nul-path-separator"]
        return CommandResult(str(config) + "\0", "", 0)

    def edit(_self, args, **_kwargs):
        calls.append(args)
        config.write_text("unknown_key: true\n")
        return 0

    monkeypatch.setattr(Runner, "run", inventory)
    monkeypatch.setattr(Runner, "interactive", edit)
    cli = CliRunner()
    initialized = cli.invoke(app, ["--config", str(selected), "config", "init", "--force"])
    assert initialized.exit_code != 0
    assert config.read_text() == "{}\n"
    edited = cli.invoke(app, ["--config", str(selected), "config", "edit"])
    assert edited.exit_code != 0
    assert calls == [["chezmoi", "edit", "--apply", "--force", str(config)]]
    assert "valid" not in edited.stdout


@pytest.mark.parametrize("outcome", ["success", "failure", "wrong-head", "missing-assets", "draft", "truncated"])
def test_release_wait_requires_exact_cd_and_public_artifacts(monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    head = "a" * 40
    monkeypatch.setattr(maintenance, "_git_output", lambda *_args: head)
    ticks = iter([0, 0, 0, 0.5, 1, 2, 3, 4, 5])
    monkeypatch.setattr(maintenance, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(maintenance, "sleep", lambda _seconds: None)
    calls = []

    class ReleaseRunner(Runner):
        def run_bounded(self, args, **_kwargs):
            calls.append(args)
            if args[1:3] == ["run", "list"]:
                assert args[args.index("--commit") + 1] == head
                assert args[args.index("--branch") + 1] == "v2.2.0"
                value = [
                    {
                        "headSha": "b" * 40 if outcome == "wrong-head" else head,
                        "status": "completed",
                        "conclusion": "failure" if outcome == "failure" else "success",
                    }
                ]
            else:
                value = {
                    "tagName": "v2.2.0",
                    "isDraft": outcome == "draft",
                    "assets": [{"name": "dot.whl"}, {"name": None if outcome == "missing-assets" else "dot.tar.gz"}],
                }
            return CommandResult(json.dumps(value), "", 0, stdout_truncated=outcome == "truncated")

    state = state_with()
    state.runner = ReleaseRunner()
    assert isinstance(state.stdout, io.StringIO)
    if outcome == "success":
        assert maintenance.wait_for_release(state, "v2.2.0", timeout_seconds=1).endswith("/v2.2.0")
        assert "Published" in state.stdout.getvalue()
    else:
        with pytest.raises(DotError):
            maintenance.wait_for_release(state, "v2.2.0", timeout_seconds=1)
        assert "Published" not in state.stdout.getvalue()
    if outcome in {"failure", "wrong-head", "truncated"}:
        assert len(calls) == 1


@pytest.mark.parametrize("failures", [1, 4])
def test_release_wait_retries_transient_github_failures(monkeypatch: pytest.MonkeyPatch, failures: int) -> None:
    head = "a" * 40
    monkeypatch.setattr(maintenance, "_git_output", lambda *_args: head)
    monkeypatch.setattr(maintenance, "monotonic", lambda: 0.0)
    monkeypatch.setattr(maintenance, "sleep", lambda _seconds: None)
    responses = [CommandResult("", "HTTP 502", 1) for _ in range(failures)] + [
        CommandResult(json.dumps([{"headSha": head, "status": "completed", "conclusion": "success"}]), "", 0),
        CommandResult(
            json.dumps({"tagName": "v2.2.0", "isDraft": False, "assets": [{"name": "d.whl"}, {"name": "d.tar.gz"}]}),
            "",
            0,
        ),
    ]

    class FlakyRunner(Runner):
        def run_bounded(self, args, **kwargs):
            assert args[0] == "gh"
            assert kwargs["check"] is False
            return responses.pop(0)

    state = state_with()
    state.runner = FlakyRunner()
    if failures <= maintenance._WAIT_RETRIES:  # noqa: SLF001 - the retry budget is the contract under test.
        assert maintenance.wait_for_release(state, "v2.2.0", timeout_seconds=1).endswith("/v2.2.0")
    else:
        with pytest.raises(DotError, match="GitHub queries kept failing"):
            maintenance.wait_for_release(state, "v2.2.0", timeout_seconds=1)
    assert isinstance(state.stderr, io.StringIO)
    assert "GitHub query failed; retrying (1/3)" in state.stderr.getvalue()
    assert "HTTP 502" not in state.stderr.getvalue()


def test_prompt_stats_report_timestamp_and_archive_gaps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "missing-time", [SessionLog("", "codex", "missing-time", "user", "text")])
    bounded = SessionQuery(since=datetime(2026, 9, 1, tzinfo=UTC))
    report = prompt_statistics(bounded, by_project=True)
    assert report["invalid_timestamps"] == 1
    assert not report["complete"]
    assert not report["prompts"]
    # The CLI boundary rejects an inverted window; the library selects nothing for it.
    inverted = SessionQuery(since=datetime(2026, 9, 2, tzinfo=UTC), until=datetime(2026, 9, 1, tzinfo=UTC))
    assert prompt_statistics(inverted)["prompts"] == 0
    rejected = CliRunner().invoke(app, ["agent", "stats", "--since", "2026-09-02", "--until", "2026-09-01"])
    assert rejected.exit_code == 2
    result = CliRunner().invoke(app, ["agent", "session", "stats", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["sessions"] == 1


def test_prompt_stats_validate_selected_sessions_and_report_corruption(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [SessionLog("2026-09-09T10:00:00Z", "codex", "example", "user", "private text")]
    ingest_session("codex", "example", logs, SessionSource(fingerprint="a" * 64))
    other = [SessionLog("2026-09-09T10:00:00Z", "claude", "other", "user", "other text")]
    ingest_session("claude", "other", other)
    path = session_bundle_path("codex", "example")
    header = path.read_bytes().split(b"\n", 1)[0]
    assert prompt_statistics(SessionQuery(agent="codex"))["complete"]
    human = CliRunner().invoke(app, ["agent", "stats", "--prompts-only", "--agent", "codex"])
    assert human.exit_code == 0
    assert "Prompt activity · 1 archived user messages" in human.stdout
    assert "Sessions: 1 · Prompts: 1 · Responses: 0" in human.stdout
    assert "Prompt coverage: complete" in human.stdout
    assert "private text" not in human.stdout
    path.write_bytes(header + b"\ncorrupt\n")
    broken = CliRunner().invoke(app, ["agent", "stats", "--prompts-only", "--json", "--agent", "codex"])
    assert broken.exit_code != 0
    document = json.loads(broken.stdout)["prompts"]
    assert not document["complete"]
    assert document["excluded_sessions"] == 1
    assert not document["prompts"]
