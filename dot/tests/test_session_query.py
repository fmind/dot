from __future__ import annotations

import hashlib
import io
import json
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from fmind_dot.cli import app
from fmind_dot.session_query import (
    SESSION_EXPORT_SCHEMA,
    SessionQuery,
    _read_legacy,
    discover_session_generations,
    export_sessions,
    migrate_legacy_sessions,
    parse_session_date,
    query_session_summaries,
    show_session,
)
from fmind_dot.session_store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SessionLog,
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


def _write_legacy(path: Path, records: list[dict[str, object] | bytes]) -> bytes:
    content = b"".join(
        record + (b"" if record.endswith(b"\n") else b"\n")
        if isinstance(record, bytes)
        else json.dumps(record, separators=(",", ":")).encode() + b"\n"
        for record in records
    )
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o600)
    return content


def _record(agent: str, session_id: str, content: str, *, cwd: str = "/work") -> dict[str, object]:
    return {
        "ts": "2026-09-01T12:00:00Z",
        "agent": agent,
        "sid": session_id,
        "role": "user",
        "content": content,
        "cwd": cwd,
    }


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
    migration = io.StringIO()
    migrate_legacy_sessions(migration, root=missing)
    assert migration.getvalue() == (
        "migration: dry-run selected=0 duplicate=0 partial=0 skipped=0 malformed_files=0 legacy_preserved=true\n"
    )

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
    assert query_session_summaries(SessionQuery(agent="claude"))[0].status == ["invalid"]
    assert selected.is_dir()


def test_query_surfaces_partial_unsupported_and_invalid_generations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    generation = _ingest("agy", "unsupported", fingerprint="f" * 64, malformed=1)
    _rewrite_manifest(generation, schema_version=SESSION_SCHEMA_VERSION + 1)

    summary = query_session_summaries()[0]

    assert summary.status == ["partial", "unsupported"]
    assert summary.cwd == ""
    assert summary.records == []

    _rewrite_manifest(generation, schema_version=SESSION_SCHEMA_VERSION, parser_version=SESSION_PARSER_VERSION)
    (generation / "transcript.jsonl").write_bytes(b"not-json\n")
    assert query_session_summaries()[0].status == ["invalid", "partial"]


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


def test_migrate_dry_run_and_apply_selects_best_without_removing_legacy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".agents" / "sessions"
    legacy = root / "2026-07-31"
    session_id = "migration-session"
    short_path = legacy / f"090000_codex_{session_id}.jsonl"
    long_path = legacy / f"100000_codex_{session_id}.jsonl"
    short_content = _write_legacy(short_path, [_record("codex", session_id, "one")])
    long_content = _write_legacy(
        long_path,
        [_record("codex", session_id, "one"), _record("codex", session_id, "two")],
    )
    _write_legacy(legacy / "unrecognized.jsonl", [b"evidence"])
    root.chmod(0o700)

    dry_run = io.StringIO()
    migrate_legacy_sessions(dry_run, root=root)

    assert session_id not in dry_run.getvalue()
    assert (
        "dry-run selected=1 duplicate=1 partial=0 skipped=0 malformed_files=1 legacy_preserved=true"
        in dry_run.getvalue()
    )
    assert not (root / "v1").exists()

    applied = io.StringIO()
    migrate_legacy_sessions(applied, apply=True, root=root)
    summary = show_session(SessionQuery(identity=session_id), include_content=True)
    assert summary.record_count == 2
    assert [record.content for record in summary.records] == ["one", "two"]
    assert short_path.read_bytes() == short_content
    assert long_path.read_bytes() == long_content
    assert "legacy_preserved=true" in applied.getvalue()
    assert not list((root / "v1").rglob(".ingest-*"))
    for path in (root / "v1").rglob("*"):
        expected = 0o700 if path.is_dir() else 0o600
        assert stat.S_IMODE(path.stat().st_mode) == expected


def test_migrate_counts_partial_skipped_and_malformed_legacy_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".agents" / "sessions"
    legacy = root / "2026-08-01"
    # Missing legacy fields decode to their Go zero values; invalid UTF-8 stays
    # malformed evidence instead of aborting the rest of the archive.
    _write_legacy(
        legacy / "100000_codex_partial.jsonl",
        [{"agent": "codex", "sid": "partial"}, b"\xff", _record("codex", "partial", "valid")],
    )
    _write_legacy(legacy / "110000_claude_empty.jsonl", [b"not-json"])
    _write_legacy(legacy / "bad-name.jsonl", [b"evidence"])
    root.chmod(0o700)

    output = io.StringIO()
    migrate_legacy_sessions(output, apply=True, root=root)

    assert (
        "apply selected=2 duplicate=0 partial=2 skipped=1 malformed_files=1 legacy_preserved=true" in output.getvalue()
    )
    summary = show_session(SessionQuery(identity="partial"), include_content=True)
    assert summary.record_count == 2
    assert summary.malformed_records == 1
    assert summary.status == ["partial"]
    assert summary.records[0].role == ""
    assert query_session_summaries(SessionQuery(identity="empty")) == []


@pytest.mark.parametrize("unsafe", ["symlink", "public"])
def test_migrate_rejects_unsafe_legacy_files(unsafe: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".agents" / "sessions"
    legacy = root / "2026-08-02"
    outside = tmp_path / "outside.jsonl"
    _write_legacy(outside, [_record("codex", "unsafe", "secret")])
    candidate = legacy / "100000_codex_unsafe.jsonl"
    candidate.parent.mkdir(mode=0o700, parents=True)
    root.chmod(0o700)
    if unsafe == "symlink":
        candidate.symlink_to(outside)
        match = "symbolic link"
    else:
        shutil.copyfile(outside, candidate)
        candidate.chmod(0o644)
        match = "not owner-only"

    with pytest.raises(ValueError, match=match):
        migrate_legacy_sessions(io.StringIO(), apply=True, root=root)

    assert not (root / "v1").exists()


def test_migrate_scan_failure_keeps_path_context(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    blocked = root / "blocked"
    blocked.mkdir(mode=0o700, parents=True)
    root.chmod(0o700)
    blocked.chmod(0)
    try:
        with pytest.raises(OSError, match=r"failed to scan legacy session archive .*Permission denied"):
            migrate_legacy_sessions(io.StringIO(), root=root)
    finally:
        blocked.chmod(0o700)


def test_legacy_fingerprint_matches_consumed_bytes_when_source_is_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "legacy.jsonl"
    original = _write_legacy(source, [_record("codex", "snapshot", "original")])
    replacement = tmp_path / "replacement.jsonl"
    _write_legacy(replacement, [_record("codex", "snapshot", "replacement with different size")])
    parse = SessionLog.from_dict

    def replace_after_parsing(value: dict[str, Any]) -> SessionLog:
        log = parse(value)
        replacement.replace(source)
        return log

    monkeypatch.setattr(SessionLog, "from_dict", staticmethod(replace_after_parsing))
    candidate = _read_legacy(source, "codex", "snapshot")

    assert candidate.logs[0].content == "original"
    assert candidate.fingerprint == hashlib.sha256(original).hexdigest()
    assert candidate.size == len(original)


def test_migrate_apply_failure_names_the_lineage_and_preserves_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".agents" / "sessions"
    source = root / "2026-08-03" / "100000_codex_conflict.jsonl"
    legacy_content = _write_legacy(source, [_record("codex", "conflict", "evidence")])
    root.chmod(0o700)
    migrate_legacy_sessions(io.StringIO(), apply=True, root=root)
    summary = show_session(SessionQuery(identity="conflict"))
    transcript = root / "v1" / "codex" / summary.lineage_id / summary.generation_id / "transcript.jsonl"
    transcript.write_bytes(b"corrupt\n")
    transcript.chmod(0o600)

    with pytest.raises(ValueError, match=rf"failed to migrate lineage {summary.lineage_id[:12]}:"):
        migrate_legacy_sessions(io.StringIO(), apply=True, root=root)

    assert source.read_bytes() == legacy_content
