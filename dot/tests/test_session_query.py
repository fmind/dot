from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive import query as session_query
from fmind_dot.archive.query import (
    SESSION_EXPORT_SCHEMA,
    SessionQuery,
    discover_sessions,
    export_sessions,
    query_session_summaries,
    show_session,
)
from fmind_dot.archive.store import (
    SESSION_SCHEMA_VERSION,
    SessionLog,
    SessionManifest,
    SessionSource,
    ingest_session,
    session_bundle_path,
)
from fmind_dot.cli import app
from fmind_dot.errors import DotError


def _ingest(
    agent: str,
    session_id: str,
    *,
    cwd: str = "/work",
    content: str = "private prompt",
    malformed: int = 0,
) -> Path:
    ingest_session(
        agent,
        session_id,
        [SessionLog("2026-09-01T12:00:00Z", agent, session_id, "user", content, cwd)],
        SessionSource(type="fixture", malformed=malformed),
    )
    return session_bundle_path(agent, session_id)


def _rewrite_manifest(path: Path, **changes: object) -> None:
    header, rest = path.read_bytes().split(b"\n", 1)
    path.write_bytes(json.dumps(json.loads(header) | changes).encode() + b"\n" + rest)


def _corrupt_transcript(path: Path) -> None:
    header = path.read_bytes().split(b"\n", 1)[0]
    path.write_bytes(header + b"\nnot-json\n")


def test_query_filters_metadata_and_reports_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    older = _ingest("codex", "session-1", cwd="/work/project-a")
    newer = _ingest("codex", "session-3", cwd="/work/project-a")
    partial = _ingest("claude", "session-2", cwd="/work/project-b", malformed=2)
    _rewrite_manifest(older, ingested_at="2026-07-30T10:00:00Z", parser_version="4")
    _rewrite_manifest(newer, ingested_at="2026-07-31T10:00:00Z")
    _rewrite_manifest(partial, ingested_at="2026-08-01T10:00:00Z")

    summaries = query_session_summaries(
        SessionQuery(
            agent="codex",
            cwd="/work/project-a",
            since=datetime(2026, 7, 30, tzinfo=UTC),
            until=datetime.max.replace(year=2026, month=7, day=31, tzinfo=UTC),
        )
    )

    assert [(summary.session_id, summary.status) for summary in summaries] == [
        ("session-3", ["current"]),
        ("session-1", ["legacy"]),
    ]
    assert all(summary.records == [] for summary in summaries)
    assert query_session_summaries(SessionQuery(identity="session-2"))[0].status == ["partial"]
    assert query_session_summaries(SessionQuery(agent="codex", cwd="/work/other")) == []


def test_empty_store_and_inverted_window(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert discover_sessions(missing) == []
    # The CLI rejects an inverted window once; the library simply selects nothing.
    inverted = SessionQuery(since=datetime(2026, 9, 2, tzinfo=UTC), until=datetime(2026, 9, 1, tzinfo=UTC))
    assert query_session_summaries(inverted, root=missing) == []


def test_manifest_filter_avoids_decoding_unselected_corrupt_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _ingest("codex", "selected")
    _corrupt_transcript(_ingest("claude", "unselected"))

    summaries = query_session_summaries(SessionQuery(agent="codex"))

    assert [summary.session_id for summary in summaries] == ["selected"]
    assert summaries[0].status == ["current"]
    assert query_session_summaries(SessionQuery(agent="claude"))[0].status == ["current"]
    assert query_session_summaries(SessionQuery(agent="claude"), include_content=True)[0].status == ["invalid"]


def test_query_surfaces_partial_unsupported_and_invalid_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = _ingest("agy", "unsupported", malformed=1)
    _rewrite_manifest(path, schema_version=SESSION_SCHEMA_VERSION + 1)

    with pytest.raises(ValueError, match="unsupported session format"):
        query_session_summaries()

    _rewrite_manifest(path, schema_version=SESSION_SCHEMA_VERSION)
    _corrupt_transcript(path)
    assert query_session_summaries()[0].status == ["partial"]
    assert query_session_summaries(include_content=True)[0].status == ["invalid", "partial"]


def test_show_is_metadata_only_by_default_and_guides_ambiguous_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _ingest("codex", "shared", content="secret-two")
    _ingest("claude", "shared", content="secret-three")

    with pytest.raises(ValueError, match=r"ambiguous across agents claude, codex; add --agent"):
        show_session(SessionQuery(identity="shared"))

    metadata = show_session(SessionQuery(agent="codex", identity="shared"))
    assert metadata.records == []
    assert "records" not in metadata.to_dict(include_records=False)
    assert {"lineage_id", "generation_id"}.isdisjoint(metadata.to_dict())
    assert show_session(SessionQuery(agent="codex", identity="shared"), include_content=True).records[0].content == (
        "secret-two"
    )
    with pytest.raises(ValueError, match="session not found"):
        show_session(SessionQuery(identity="missing"))


def test_export_json_and_ndjson_keep_content_opt_in(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _ingest("claude", "historic", content="old secret")
    _ingest("codex", "current", content="new secret")

    metadata_output = io.StringIO()
    export_sessions(metadata_output)
    metadata = json.loads(metadata_output.getvalue())
    assert metadata["schema"] == SESSION_EXPORT_SCHEMA == "dot.agent.sessions/v2"
    assert all("records" not in session for session in metadata["sessions"])
    assert "secret" not in metadata_output.getvalue()

    content_output = io.StringIO()
    export_sessions(content_output, SessionQuery(agent="codex"), include_content=True)
    assert json.loads(content_output.getvalue())["sessions"][0]["records"][0]["content"] == "new secret"

    redacted_output = io.StringIO()
    export_sessions(redacted_output, redact_content=True, format="ndjson")
    rows = [json.loads(line) for line in redacted_output.getvalue().splitlines()]
    assert len(rows) == 2
    assert all(row["schema"] == SESSION_EXPORT_SCHEMA for row in rows)
    assert {row["session"]["records"][0]["content"] for row in rows} == {"[redacted]"}
    assert "secret" not in redacted_output.getvalue()

    with pytest.raises(ValueError, match="mutually exclusive"):
        export_sessions(io.StringIO(), include_content=True, redact_content=True)
    with pytest.raises(ValueError, match=r"unsupported export format 'csv': expected json or ndjson"):
        export_sessions(io.StringIO(), format="csv")


def test_cli_list_is_text_and_show_is_json_without_default_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _ingest("codex", "cli-session", cwd="/repo", content="cli secret")
    runner = CliRunner()

    listed = runner.invoke(
        app,
        ["agent", "session", "list", "--agent", "codex", "--project", "/repo", "--until", "2099-12-31"],
    )
    shown = runner.invoke(app, ["agent", "session", "show", "cli-session"])
    shown_with_content = runner.invoke(app, ["agent", "session", "show", "cli-session", "--content"])

    assert listed.exit_code == 0
    assert listed.stdout.rstrip().endswith("codex cli-session records=1 status=current cwd=/repo")
    assert "cli secret" not in listed.stdout
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["schema"] == "dot.agent.session.show/v2"
    assert "records" not in json.loads(shown.stdout)["session"]
    assert json.loads(shown_with_content.stdout)["session"]["records"][0]["content"] == "cli secret"


def test_cli_list_is_bounded_and_filters_json_by_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    legacy = _ingest("codex", "legacy", cwd="/old")
    current = _ingest("codex", "current", cwd="/current")
    other = _ingest("claude", "other", cwd="/other")
    _rewrite_manifest(legacy, ingested_at="2026-09-01T10:00:00Z", parser_version="3")
    _rewrite_manifest(current, ingested_at="2026-09-02T10:00:00Z")
    _rewrite_manifest(other, ingested_at="2026-09-03T10:00:00Z")
    runner = CliRunner()

    latest = runner.invoke(app, ["agent", "session", "list", "--json", "--limit", "1"])
    flagged = runner.invoke(app, ["agent", "session", "list", "--json", "--status", "legacy"])
    unknown = runner.invoke(app, ["agent", "session", "list", "--status", "stale"])
    removed = runner.invoke(app, ["agent", "session", "list", "--all-generations"])

    assert latest.exit_code == 0
    assert json.loads(latest.stdout)["schema"] == "dot.agent.session.list/v2"
    assert [row["session_id"] for row in json.loads(latest.stdout)["sessions"]] == ["other"]
    assert flagged.exit_code == 0
    assert [row["cwd"] for row in json.loads(flagged.stdout)["sessions"]] == ["/old"]
    assert unknown.exit_code == removed.exit_code == 2


def test_query_selects_status_and_limit_without_reading_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _rewrite_manifest(_ingest("codex", "old", cwd="/old"), ingested_at="2026-09-01T10:00:00Z")
    _rewrite_manifest(_ingest("codex", "new", cwd="/current"), ingested_at="2026-09-02T10:00:00Z")
    monkeypatch.setattr(session_query, "read_session_bundle", lambda _path: pytest.fail("content must not be read"))

    summaries = query_session_summaries(statuses={"current"}, limit=1)

    assert [(item.cwd, item.status) for item in summaries] == [("/current", ["current"])]


@pytest.mark.parametrize("include_content", [False, True])
def test_query_reads_only_matching_transcripts_and_preserves_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, include_content: bool
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    current = _ingest("codex", "shared")
    _ingest("codex", "other-project", cwd="/other")
    fallback = _ingest("codex", "missing-cwd")
    invalid = _ingest("codex", "invalid")
    _rewrite_manifest(fallback, cwd="")
    _corrupt_transcript(invalid)
    reads: list[Path] = []
    read = session_query.read_session_bundle

    def track_reads(path: Path) -> tuple[SessionManifest, list[SessionLog]]:
        reads.append(path)
        return read(path)

    monkeypatch.setattr(session_query, "read_session_bundle", track_reads)
    summaries = query_session_summaries(
        SessionQuery(cwd="/work"), include_content=include_content, validate_content=True
    )

    assert sorted(reads) == sorted([current, fallback, invalid])
    assert {item.session_id: item.status for item in summaries} == {
        "shared": ["current"],
        "missing-cwd": ["current"],
        "invalid": ["invalid"],
    }
    assert all(item.cwd == "/work" for item in summaries)
    assert sum(len(item.records) for item in summaries) == (2 if include_content else 0)


def test_malformed_manifest_error_includes_path_and_cause(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = _ingest("codex", "broken")
    path.write_text("{broken\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid session manifest") as failure:
        discover_sessions()

    assert str(path) in str(failure.value)
    assert "Expecting property name" in str(failure.value)


def test_time_filter_excludes_non_rfc3339_manifest_timestamp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = _ingest("codex", "bad-time")
    _rewrite_manifest(path, ingested_at="2026-09-01T12:00:00")

    assert query_session_summaries(SessionQuery(since=datetime(2026, 9, 1, tzinfo=UTC))) == []

    # A value can match the RFC3339 shape while still naming an impossible day.
    _rewrite_manifest(path, ingested_at="2026-02-30T12:00:00Z")
    assert query_session_summaries(SessionQuery(since=datetime(2026, 2, 1, tzinfo=UTC))) == []


@pytest.mark.parametrize(
    ("older", "newer"),
    [
        ("2026-09-20T12:00:00Z", "2026-09-20T12:00:00.500Z"),
        ("2026-09-20T12:00:00+02:00", "2026-09-20T11:00:00Z"),
    ],
)
def test_session_limit_selects_latest_instant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, older: str, newer: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _rewrite_manifest(_ingest("codex", "old"), ingested_at=older)
    _rewrite_manifest(_ingest("codex", "new"), ingested_at=newer)

    assert query_session_summaries(limit=1)[0].session_id == "new"


@pytest.mark.parametrize("timestamp", ["0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"])
def test_out_of_range_utc_timestamps_do_not_crash_queries_or_prompt_statistics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timestamp: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "bad-time", [SessionLog(timestamp, "codex", "bad-time", "user", "synthetic")])
    _rewrite_manifest(session_bundle_path("codex", "bad-time"), ingested_at=timestamp)

    assert query_session_summaries(SessionQuery(since=datetime(2026, 9, 1, tzinfo=UTC))) == []
    result = CliRunner().invoke(app, ["agent", "stats", "--no-sync", "--since", "2026-09-01", "--json"])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    report = json.loads(result.stdout)["prompts"]
    assert report["invalid_timestamps"] == 1
    assert report["prompts"] == 0
    assert report["complete"] is False
