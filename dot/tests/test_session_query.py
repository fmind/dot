from __future__ import annotations

import io
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot import session_query
from fmind_dot.cli import app
from fmind_dot.session_query import (
    SESSION_EXPORT_SCHEMA,
    SessionQuery,
    compact_session_generations,
    discover_session_generations,
    export_sessions,
    parse_session_date,
    query_session_summaries,
    show_session,
)
from fmind_dot.session_store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SessionLog,
    SessionManifest,
    SessionSource,
    ingest_session,
    session_store_root,
)


def _ingest(
    agent: str,
    session_id: str,
    *,
    fingerprint: str,
    cwd: str = "/work",
    content: str = "private prompt",
    malformed: int = 0,
) -> Path:
    result = ingest_session(
        agent,
        session_id,
        [SessionLog("2026-09-01T12:00:00Z", agent, session_id, "user", content, cwd)],
        SessionSource(fingerprint=fingerprint, type="fixture", malformed=malformed),
    )
    return session_store_root() / agent / result.lineage_id / result.generation_id


def _rewrite_manifest(generation: Path, **changes: object) -> None:
    path = generation / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update(changes)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _ingest_records(agent: str, session_id: str, fingerprint: str, count: int, *, malformed: int = 0) -> Path:
    result = ingest_session(
        agent,
        session_id,
        [
            SessionLog(f"2026-09-01T12:00:{index:02d}Z", agent, session_id, "user", f"record-{index}")
            for index in range(count)
        ],
        SessionSource(fingerprint=fingerprint, type="fixture", malformed=malformed),
    )
    return session_store_root() / agent / result.lineage_id / result.generation_id


def test_compaction_dry_run_and_apply_retain_best_complete_and_partial_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    stale = _ingest_records("codex", "session-1", "a" * 64, 1)
    complete = _ingest_records("codex", "session-1", "b" * 64, 2)
    partial = _ingest_records("codex", "session-1", "c" * 64, 3, malformed=1)
    output = io.StringIO()

    result = compact_session_generations(output)

    assert result.generations == 3
    assert result.retained == 2
    assert result.removed == 0
    assert result.reclaimable_bytes > 0
    assert all(path.exists() for path in (stale, complete, partial))
    assert output.getvalue().count("\n") == 1
    assert "mode=dry-run" in output.getvalue()

    applied = compact_session_generations(io.StringIO(), apply=True)

    assert applied.removed == 1
    assert not stale.exists()
    assert complete.exists()
    assert partial.exists()


def test_compaction_fails_closed_before_deleting_any_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    first = _ingest_records("codex", "session-1", "d" * 64, 1)
    corrupt = _ingest_records("codex", "session-1", "e" * 64, 2)
    (corrupt / "transcript.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint mismatch"):
        compact_session_generations(io.StringIO(), apply=True)

    assert first.exists()
    assert corrupt.exists()


def test_compaction_preserves_divergent_generations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for fingerprint, content in (("f" * 64, "branch-left"), ("0" * 64, "branch-right")):
        ingest_session(
            "claude",
            "shared-id",
            [SessionLog("2026-09-01T12:00:00Z", "claude", "shared-id", "user", content)],
            SessionSource(fingerprint=fingerprint, type="fixture"),
        )

    result = compact_session_generations(io.StringIO(), apply=True)

    assert result.retained == 2
    assert result.removable == 0
    assert result.removed == 0


def test_parse_session_date_preserves_whole_day_and_rfc3339_contract() -> None:
    assert parse_session_date("2026-07-31") == datetime(2026, 7, 31, tzinfo=UTC)
    assert parse_session_date("2026-07-31", end_of_day=True) == datetime.max.replace(
        year=2026, month=7, day=31, tzinfo=UTC
    )
    assert parse_session_date("2026-07-31T10:30:00+02:00") == datetime(2026, 7, 31, 8, 30, tzinfo=UTC)
    assert parse_session_date("2026-07-31T10:30:00Z", end_of_day=True) == datetime(2026, 7, 31, 10, 30, tzinfo=UTC)
    assert parse_session_date("") is None

    for invalid in (
        "yesterday",
        "2026-07",
        "2026-07-31 10:30:00Z",
        "2026-07-31T10:30:00",
        "2026-07-31T24:00:00Z",
    ):
        with pytest.raises(ValueError, match="expected RFC3339 or YYYY-MM-DD"):
            parse_session_date(invalid)


def test_query_filters_metadata_and_keeps_lineage_status_global(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    old = _ingest("codex", "session-1", fingerprint="a" * 64, cwd="/work/project-a")
    current = _ingest("codex", "session-1", fingerprint="b" * 64, cwd="/work/project-a")
    partial = _ingest("claude", "session-2", fingerprint="c" * 64, cwd="/work/project-b", malformed=2)
    _rewrite_manifest(old, ingested_at="2026-07-30T10:00:00Z")
    _rewrite_manifest(current, ingested_at="2026-07-31T10:00:00Z")
    _rewrite_manifest(partial, ingested_at="2026-08-01T10:00:00Z")
    duplicate = old.with_name("duplicate-generation")
    shutil.copytree(old, duplicate)

    summaries = query_session_summaries(
        SessionQuery(
            agent="codex",
            cwd="/work/project-a",
            since=parse_session_date("2026-07-30"),
            until=parse_session_date("2026-07-31", end_of_day=True),
        )
    )

    assert [summary.ingested_at for summary in summaries] == [
        "2026-07-31T10:00:00Z",
        "2026-07-30T10:00:00Z",
        "2026-07-30T10:00:00Z",
    ]
    assert all(summary.records == [] for summary in summaries)
    assert summaries[0].status == ["current"]
    assert {tuple(summary.status) for summary in summaries[1:]} == {("duplicate", "stale")}
    assert query_session_summaries(SessionQuery(identity="session-2"))[0].status == ["partial"]
    assert query_session_summaries(SessionQuery(identity=current.name))[0].generation_id == current.name
    assert query_session_summaries(SessionQuery(agent="codex", cwd="/work/other")) == []


def test_empty_store_and_malformed_time_metadata_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert discover_session_generations(missing) == []
    with pytest.raises(ValueError, match="--since must not be after --until"):
        query_session_summaries(
            SessionQuery(
                since=datetime(2026, 9, 2, tzinfo=UTC),
                until=datetime(2026, 9, 1, tzinfo=UTC),
            ),
            root=missing,
        )


def test_manifest_filter_avoids_decoding_unselected_corrupt_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    selected = _ingest("codex", "selected", fingerprint="d" * 64)
    unselected = _ingest("claude", "unselected", fingerprint="e" * 64)
    (unselected / "transcript.jsonl").write_bytes(b"corrupt\n")

    summaries = query_session_summaries(SessionQuery(agent="codex"))

    assert [summary.session_id for summary in summaries] == ["selected"]
    assert summaries[0].status == ["current"]
    assert query_session_summaries(SessionQuery(agent="claude"))[0].status == ["current"]
    assert query_session_summaries(SessionQuery(agent="claude"), include_content=True)[0].status == ["invalid"]
    assert selected.is_dir()


def test_query_surfaces_partial_unsupported_and_invalid_generations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    generation = _ingest("agy", "unsupported", fingerprint="f" * 64, malformed=1)
    _rewrite_manifest(generation, schema_version=SESSION_SCHEMA_VERSION + 1)

    summary = query_session_summaries()[0]

    assert summary.status == ["partial", "unsupported"]
    assert summary.cwd == "/work"
    assert summary.records == []

    _rewrite_manifest(generation, schema_version=SESSION_SCHEMA_VERSION, parser_version=SESSION_PARSER_VERSION)
    (generation / "transcript.jsonl").write_bytes(b"not-json\n")
    assert query_session_summaries()[0].status == ["partial"]
    assert query_session_summaries(include_content=True)[0].status == ["invalid", "partial"]


def test_show_is_metadata_only_by_default_and_guides_ambiguous_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    first = _ingest("codex", "shared", fingerprint="1" * 64, content="secret-one")
    second = _ingest("codex", "shared", fingerprint="2" * 64, content="secret-two")
    third = _ingest("claude", "shared", fingerprint="3" * 64, content="secret-three")
    _rewrite_manifest(first, ingested_at="2026-09-01T10:00:00Z")
    _rewrite_manifest(second, ingested_at="2026-09-02T10:00:00Z")
    _rewrite_manifest(third, ingested_at="2026-09-03T10:00:00Z")

    with pytest.raises(ValueError, match=r"across agents claude, codex; add --agent"):
        show_session(SessionQuery(identity="shared"))
    with pytest.raises(ValueError, match=r"2 generations of this codex session") as ambiguity:
        show_session(SessionQuery(agent="codex", identity="shared"))
    assert "--agent" not in str(ambiguity.value)
    assert first.name in str(ambiguity.value)
    assert second.name in str(ambiguity.value)

    metadata = show_session(SessionQuery(identity=second.name))
    assert metadata.records == []
    assert "records" not in metadata.to_dict(include_records=False)
    assert show_session(SessionQuery(identity=second.name), include_content=True).records[0].content == "secret-two"
    with pytest.raises(ValueError, match="session not found"):
        show_session(SessionQuery(identity="missing"))


def test_export_json_and_ndjson_keep_content_opt_in(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _ingest("claude", "historic", fingerprint="4" * 64, content="old secret")
    _ingest("codex", "current", fingerprint="5" * 64, content="new secret")

    metadata_output = io.StringIO()
    export_sessions(metadata_output)
    metadata = json.loads(metadata_output.getvalue())
    assert metadata["schema"] == SESSION_EXPORT_SCHEMA
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
    _ingest("codex", "cli-session", fingerprint="6" * 64, cwd="/repo", content="cli secret")
    runner = CliRunner()

    listed = runner.invoke(
        app,
        ["agent", "session", "list", "--agent", "codex", "--project", "/repo", "--until", "2026-12-31"],
    )
    shown = runner.invoke(app, ["agent", "session", "show", "cli-session"])
    shown_with_content = runner.invoke(app, ["agent", "session", "show", "cli-session", "--content"])

    assert listed.exit_code == 0
    assert "codex cli-session records=1 status=current cwd=/repo" in listed.stdout
    assert "cli secret" not in listed.stdout
    assert shown.exit_code == 0
    assert "records" not in json.loads(shown.stdout)
    assert json.loads(shown_with_content.stdout)["records"][0]["content"] == "cli secret"


def test_cli_list_defaults_to_latest_bounded_rows_and_supports_json_status_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    old = _ingest("codex", "shared", fingerprint="a" * 64, cwd="/old")
    current = _ingest("codex", "shared", fingerprint="b" * 64, cwd="/current")
    other = _ingest("claude", "other", fingerprint="c" * 64, cwd="/other")
    _rewrite_manifest(old, ingested_at="2026-09-01T10:00:00Z")
    _rewrite_manifest(current, ingested_at="2026-09-02T10:00:00Z")
    _rewrite_manifest(other, ingested_at="2026-09-03T10:00:00Z")
    runner = CliRunner()

    latest = runner.invoke(app, ["agent", "session", "list", "--json", "--limit", "1"])
    stale = runner.invoke(
        app,
        ["agent", "session", "list", "--json", "--all-generations", "--status", "stale"],
    )

    assert latest.exit_code == 0
    assert [row["session_id"] for row in json.loads(latest.stdout)] == ["other"]
    assert stale.exit_code == 0
    assert [row["cwd"] for row in json.loads(stale.stdout)] == ["/old"]


def test_query_can_select_latest_status_and_limit_without_reading_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    old = _ingest("codex", "shared", fingerprint="d" * 64, cwd="/old")
    current = _ingest("codex", "shared", fingerprint="e" * 64, cwd="/current")
    _rewrite_manifest(old, ingested_at="2026-09-01T10:00:00Z")
    _rewrite_manifest(current, ingested_at="2026-09-02T10:00:00Z")

    summaries = query_session_summaries(latest_only=True, statuses={"current"}, limit=1)

    assert [(item.cwd, item.status) for item in summaries] == [("/current", ["current"])]


@pytest.mark.parametrize("include_content", [False, True])
def test_query_reads_only_matching_transcripts_and_preserves_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, include_content: bool
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    old = _ingest("codex", "shared", fingerprint="a" * 64)
    current = _ingest("codex", "shared", fingerprint="b" * 64)
    _ingest("codex", "other-project", fingerprint="c" * 64, cwd="/other")
    fallback = _ingest("codex", "missing-cwd", fingerprint="d" * 64)
    invalid = _ingest("codex", "invalid", fingerprint="e" * 64)
    _rewrite_manifest(old, ingested_at="2026-09-01T10:00:00Z")
    _rewrite_manifest(current, ingested_at="2026-09-02T10:00:00Z")
    _rewrite_manifest(fallback, cwd="")
    (invalid / "transcript.jsonl").write_text("corrupt", encoding="utf-8")
    reads: list[Path] = []
    validate = session_query.validate_session_generation

    def track_reads(path: Path, manifest: SessionManifest) -> list[SessionLog]:
        reads.append(path)
        return validate(path, manifest)

    monkeypatch.setattr(session_query, "validate_session_generation", track_reads)
    summaries = query_session_summaries(
        SessionQuery(cwd="/work"),
        latest_only=True,
        include_content=include_content,
        validate_content=True,
    )

    assert set(reads) == {current, fallback, invalid}
    assert len(reads) == 3
    assert {item.session_id: item.status for item in summaries} == {
        "shared": ["current"],
        "missing-cwd": ["current"],
        "invalid": ["invalid"],
    }
    assert all(item.cwd == "/work" for item in summaries)
    assert sum(len(item.records) for item in summaries) == (2 if include_content else 0)


def test_discovery_rejects_broken_links_public_entries_and_unreadable_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    broken_root = tmp_path / "broken-store"
    broken_root.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        discover_session_generations(broken_root)

    generation = _ingest("codex", "unsafe", fingerprint="7" * 64)
    manifest = generation / "manifest.json"
    manifest.chmod(0o644)
    with pytest.raises(ValueError, match="not owner-only"):
        query_session_summaries()
    manifest.chmod(0o600)

    unreadable = session_store_root() / "unreadable"
    unreadable.mkdir(mode=0o700)
    unreadable.chmod(0)
    try:
        with pytest.raises(OSError, match=r"failed to scan session store .*Permission denied"):
            query_session_summaries()
    finally:
        unreadable.chmod(0o700)


def test_malformed_manifest_error_includes_path_and_cause(tmp_path: Path) -> None:
    generation = tmp_path / "codex" / "lineage" / "generation"
    generation.mkdir(mode=0o700, parents=True)
    for directory in (tmp_path / "codex", tmp_path / "codex" / "lineage", generation):
        directory.chmod(0o700)
    manifest = generation / "manifest.json"
    manifest.write_text("{broken\n", encoding="utf-8")
    manifest.chmod(0o600)

    with pytest.raises(ValueError, match="failed to read session manifest") as failure:
        discover_session_generations(tmp_path)

    assert str(manifest) in str(failure.value)
    assert "Expecting property name" in str(failure.value)


def test_time_filter_excludes_non_rfc3339_manifest_timestamp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    generation = _ingest("codex", "bad-time", fingerprint="8" * 64)
    _rewrite_manifest(generation, ingested_at="2026-09-01T12:00:00")

    assert query_session_summaries(SessionQuery(since=datetime(2026, 9, 1, tzinfo=UTC))) == []

    # A value can match the RFC3339 shape while still naming an impossible day.
    _rewrite_manifest(generation, ingested_at="2026-02-30T12:00:00Z")
    assert query_session_summaries(SessionQuery(since=datetime(2026, 2, 1, tzinfo=UTC))) == []
