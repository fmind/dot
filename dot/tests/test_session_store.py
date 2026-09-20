"""One private, atomically replaced bundle per agent session."""

from __future__ import annotations

import hashlib
import json
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionLog,
    SessionManifest,
    SessionSource,
    discover_session_bundles,
    fingerprint_json,
    fingerprint_logs,
    ingest_session,
    is_valid_session_id,
    marshal_session_logs,
    read_session_bundle,
    read_session_manifest,
    report_ingestion,
    session_bundle_path,
    session_store_root,
)


def _logs(count: int, session_id: str = "session-1", agent: str = "codex") -> list[SessionLog]:
    return [
        SessionLog(f"2026-08-01T12:0{index}:00Z", agent, session_id, "user", f"private {index}", "/work")
        for index in range(count)
    ]


def _manifest_value(**changes: object) -> dict[str, object]:
    value = SessionManifest(
        agent="codex",
        session_id="session-1",
        parser_version=SESSION_PARSER_VERSION,
        source_type="fixture",
        source_fingerprint="a" * 64,
        ingested_at="2026-08-01T12:00:00Z",
        completeness="complete",
        record_count=1,
    ).to_dict()
    value.update(changes)
    return value


def _write_bundle(home: Path, header: dict[str, object] | bytes, transcript: bytes) -> Path:
    path = home / ".agents/sessions/v3/codex/session-1.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = header if isinstance(header, bytes) else (json.dumps(header) + "\n").encode()
    path.write_bytes(content + transcript)
    return path


def test_ingestion_publishes_one_private_bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = _logs(2)
    usage = {"harness": "codex", "session_id": "session-1"}

    result = ingest_session("codex", "session-1", logs, SessionSource(type="codex-jsonl", signature="1:2"), usage=usage)

    path = session_bundle_path("codex", "session-1")
    assert result.status == "ingested"
    assert path == session_store_root() / "codex/session-1.jsonl"
    assert discover_session_bundles() == [path]
    manifest, records = read_session_bundle(path)
    assert records == logs
    assert manifest == read_session_manifest(path) == result.manifest
    assert (manifest.cwd, manifest.source_signature, manifest.usage, manifest.record_count) == (
        "/work",
        "1:2",
        usage,
        2,
    )
    assert stat.S_IMODE(session_store_root().stat().st_mode) == 0o700
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert sorted(item.name for item in path.parent.iterdir()) == ["session-1.jsonl"]


def test_replacement_never_shrinks_the_archived_transcript(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = session_bundle_path("codex", "session-1")

    assert ingest_session("codex", "session-1", _logs(2), SessionSource(fingerprint="a" * 64)).status == "ingested"
    # A truncated or rotated source keeps the longer archived copy.
    retained = ingest_session("codex", "session-1", _logs(1), SessionSource(fingerprint="b" * 64))
    assert (retained.status, retained.manifest.record_count) == ("retained", 2)
    assert read_session_manifest(path).source_fingerprint == "a" * 64
    # The same record count, or more, replaces the copy.
    assert ingest_session("codex", "session-1", _logs(2), SessionSource(fingerprint="c" * 64)).status == "ingested"
    assert ingest_session("codex", "session-1", _logs(3), SessionSource(fingerprint="d" * 64)).status == "ingested"
    manifest, records = read_session_bundle(path)
    assert (manifest.source_fingerprint, len(records)) == ("d" * 64, 3)


def test_unchanged_content_keeps_capture_time_and_refreshes_signature(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    first = ingest_session("codex", "session-1", _logs(1), SessionSource(fingerprint="a" * 64, signature="old"))
    path = session_bundle_path("codex", "session-1")
    content = path.read_bytes()

    assert ingest_session(
        "codex", "session-1", _logs(1), SessionSource(fingerprint="a" * 64, signature="old")
    ).status == ("unchanged")
    assert path.read_bytes() == content
    touched = ingest_session("codex", "session-1", _logs(1), SessionSource(fingerprint="a" * 64, signature="new"))

    assert touched.status == "unchanged"
    stored = read_session_manifest(path)
    assert (stored.source_signature, stored.ingested_at) == ("new", first.manifest.ingested_at)


def test_concurrent_ingestion_converges_without_temporary_residue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = _logs(1, "same", "claude")

    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(
            executor.map(
                lambda index: ingest_session("claude", "same", logs, SessionSource(fingerprint=f"{index}" * 64)).status,
                range(4),
            )
        )

    assert set(statuses) <= {"ingested", "unchanged"}
    path = session_bundle_path("claude", "same")
    assert read_session_bundle(path)[1] == logs
    assert [item.name for item in path.parent.iterdir()] == ["same.jsonl"]


def test_bundle_content_is_compact_native_utf8(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("agy", "unicode", [SessionLog("", "agy", "unicode", "user", "café <ok>\u2028")])

    content = session_bundle_path("agy", "unicode").read_bytes()

    assert "café <ok>\u2028".encode() in content
    assert content.count(b"\n") == 2
    assert read_session_bundle(session_bundle_path("agy", "unicode"))[1][0].content == "café <ok>\u2028"


def test_fingerprints_preserve_native_unicode_json() -> None:
    structured = {"html": "<&>\u2028\u2029", "utf8": "café"}
    native_encoded = '{"html":"<&>\u2028\u2029","utf8":"café"}'.encode()
    assert fingerprint_json(structured) == hashlib.sha256(native_encoded).hexdigest()

    logs = [SessionLog("", "codex", "session-1", "user", "café <&>\u2028\u2029", "/repo", "gpt")]
    encoded = marshal_session_logs(logs)
    native_transcript = (
        b'{"ts":"","agent":"codex","sid":"session-1","role":"user","content":"caf\xc3\xa9 '
        + '<&>\u2028\u2029","cwd":"/repo","model":"gpt"}\n'.encode()
    )
    assert encoded == native_transcript
    assert fingerprint_logs(logs) == hashlib.sha256(native_transcript).hexdigest()


def test_ingestion_normalizes_models_and_default_source_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [
        SessionLog("2026-08-01T10:00:00Z", "codex", "models", "user", "one"),
        SessionLog("2026-08-01T11:00:00Z", "codex", "models", "assistant", "two", model="first"),
        SessionLog("2026-08-01T12:00:00Z", "codex", "models", "user", "three"),
        SessionLog("2026-08-01T13:00:00Z", "codex", "models", "assistant", "four", model="second"),
        SessionLog("2026-08-01T14:00:00Z", "codex", "models", "user", "five"),
    ]

    result = ingest_session("codex", "models", logs)

    assert [log.model for log in logs] == ["first", "first", "first", "second", "second"]
    assert result.manifest.source_type == "normalized"
    assert result.manifest.source_fingerprint == fingerprint_logs(logs)
    assert result.manifest.high_water_mark == "2026-08-01T14:00:00Z"
    assert result.manifest.completeness == "complete"
    assert ingest_session(
        "codex", "partial", _logs(1, "partial"), SessionSource(malformed=1)
    ).manifest.completeness == ("partial")


def test_ingestion_skips_empty_sessions_and_rejects_unsafe_identities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    skipped = ingest_session("codex", "empty", [], SessionSource(type="fixture", malformed=2, skipped=3))
    assert skipped.status == "skipped"
    assert "skipped codex records=0 malformed=2 skipped=3 completeness=partial" in report_ingestion(skipped)
    assert not (tmp_path / ".agents").exists()

    valid = _logs(1, "valid")[0]
    for invalid in ("", "..", "../escape", "a/b", "space separated", "dot.ted"):
        assert not is_valid_session_id(invalid)
        with pytest.raises(ValueError, match="invalid session_id format"):
            ingest_session("codex", invalid, [replace(valid, sid=invalid)])
        with pytest.raises(ValueError, match="invalid agent format"):
            ingest_session(invalid, "valid", [replace(valid, agent=invalid)])
    assert is_valid_session_id("safe_ID-1")
    with pytest.raises(ValueError, match="record 1 does not match its session"):
        ingest_session("codex", "valid", [replace(valid, agent="claude")])
    assert not (tmp_path / ".agents").exists()


def test_corrupt_stored_bundle_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "session-1", _logs(1))
    path = session_bundle_path("codex", "session-1")
    path.write_text("{}\n")

    with pytest.raises(ValueError, match="unsupported session format"):
        ingest_session("codex", "session-1", _logs(2))
    assert path.read_text() == "{}\n"


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"schema_version": 2}, "unsupported session format; recapture available sources"),
        ({"parser_version": "2"}, "unsupported session format"),
        ({"completeness": "unknown"}, "invalid manifest field completeness"),
        ({"agent": ""}, "invalid manifest field agent"),
        ({"session_id": "../escape"}, "invalid session manifest identity"),
        ({"record_count": True}, "invalid manifest field record_count"),
        ({"malformed_records": -1}, "invalid manifest field malformed_records"),
        ({"usage": []}, "invalid manifest field usage"),
    ],
)
def test_manifest_rejects_invalid_fields(change: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SessionManifest.from_dict(_manifest_value(**change))


def test_manifest_and_records_reject_missing_or_wrong_typed_input() -> None:
    value = _manifest_value()
    del value["record_count"]
    with pytest.raises(ValueError, match="invalid session manifest"):
        SessionManifest.from_dict(value)

    required = {"ts": "", "agent": "codex", "sid": "session-1", "role": "user", "content": 1}
    with pytest.raises(ValueError, match="invalid normalized transcript record"):
        SessionLog.from_dict(required)
    required["content"] = "hello"
    required["cwd"] = []
    with pytest.raises(ValueError, match="invalid normalized transcript record"):
        SessionLog.from_dict(required)


@pytest.mark.parametrize(
    ("header", "transcript", "match"),
    [
        (b"[]\n", b"", "invalid session manifest"),
        (b"{broken\n", b"", "invalid session manifest"),
        (_manifest_value(session_id="other"), b"", "does not match its path"),
        (_manifest_value(), b"\xff\n", "invalid normalized transcript record 1"),
        (_manifest_value(), b"{broken\n", "invalid normalized transcript record 1"),
        (
            _manifest_value(),
            b'{"ts":"","agent":"claude","sid":"session-1","role":"user","content":"ok"}\n',
            "record 1 does not match its session",
        ),
        (
            _manifest_value(record_count=2),
            b'{"ts":"","agent":"codex","sid":"session-1","role":"user","content":"ok"}\n',
            "contains 1 records, expected 2",
        ),
    ],
)
def test_bundle_reads_reject_malformed_or_contradictory_content(
    tmp_path: Path, header: dict[str, object] | bytes, transcript: bytes, match: str
) -> None:
    path = _write_bundle(tmp_path, header, transcript)
    with pytest.raises(ValueError, match=match):
        read_session_bundle(path)


def test_discovery_ignores_temporary_files_sync_state_and_unsafe_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ingest_session("codex", "session-1", _logs(1))
    directory = session_store_root() / "codex"
    (directory / ".session-1.jsonl.abc.tmp").write_text("partial")
    (directory / ".sync.json").write_text("{}")
    (directory / "unsafe.name.jsonl").write_text("{}")
    (session_store_root() / "bad agent").mkdir()

    assert discover_session_bundles() == [directory / "session-1.jsonl"]


def test_archive_validation_does_not_echo_transcripts_or_manifest_values() -> None:
    import traceback

    transcript = {"ts": "", "agent": "codex", "sid": "one", "role": "user", "content": {"private-marker": 1}}
    manifest = _manifest_value(source_type={"private-marker": 1})
    with pytest.raises(ValueError, match="invalid normalized transcript record") as transcript_error:
        SessionLog.from_dict(transcript)
    with pytest.raises(ValueError, match="invalid manifest field source_type") as manifest_error:
        SessionManifest.from_dict(manifest)
    for error in (transcript_error, manifest_error):
        assert "private-marker" not in "".join(traceback.format_exception(error.value))


def test_transcript_serialization_preserves_empty_required_fields_and_optional_order() -> None:
    log = SessionLog("", "codex", "one", "user", "café", model="test")
    assert marshal_session_logs([log]) == (
        '{"ts":"","agent":"codex","sid":"one","role":"user","content":"café","model":"test"}\n'.encode()
    )
    assert SessionLog.from_dict(log.to_dict() | {"future": "ignored"}) == log
