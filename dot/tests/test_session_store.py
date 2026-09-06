from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import fmind_dot.session_store as session_store
from fmind_dot.session_store import (
    SessionIngestionResult,
    SessionLog,
    SessionManifest,
    SessionSource,
    fingerprint_bytes,
    fingerprint_file,
    fingerprint_json,
    fingerprint_logs,
    ingest_session,
    is_valid_session_id,
    marshal_session_logs,
    publish_owner_only,
    read_session_manifest,
    report_ingestion,
    session_generation_id,
    session_lineage_id,
    session_store_root,
    stored_generation,
    validate_session_generation,
)


def _generation(agent: str, session_id: str, fingerprint: str) -> tuple[Path, SessionManifest]:
    logs = [SessionLog("2026-08-01T12:00:00Z", agent, session_id, "user", "private")]
    result = ingest_session(agent, session_id, logs, SessionSource(fingerprint=fingerprint))
    assert result.manifest is not None
    path = session_store_root() / agent / result.lineage_id / result.generation_id
    return path, result.manifest


def _write_generation(path: Path, manifest: SessionManifest, transcript: bytes) -> None:
    path.mkdir(mode=0o700, parents=True)
    path.chmod(0o700)
    transcript_path = path / "transcript.jsonl"
    transcript_path.write_bytes(transcript)
    transcript_path.chmod(0o600)
    manifest_path = path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)


def _manifest_for(
    transcript: bytes, *, record_count: int = 1, high_water: str = "2026-08-01T12:00:00Z"
) -> SessionManifest:
    return SessionManifest(
        parser_version="1",
        agent="codex",
        session_id="session-1",
        lineage_id=session_lineage_id("codex", "session-1"),
        source_type="fixture",
        source_fingerprint="a" * 64,
        high_water_mark=high_water,
        ingested_at="2026-08-01T12:00:00Z",
        completeness="complete",
        transcript_sha256=fingerprint_bytes(transcript),
        schema_version=1,
        record_count=record_count,
        malformed_records=0,
        skipped_records=0,
    )


def test_v1_identity_and_atomic_private_generation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (
        session_lineage_id("codex", "session-1") == "b540336b2c776814303a05b68a90ac255ba738a435985fdb1709c224fd9416cc"
    )
    assert session_generation_id("a" * 64) == "b58b6c93ff1f72bb13e5553fc922e6b3e34b54126fe128b34ac672488f4fa0db"
    logs = [SessionLog("2026-08-01T12:00:00Z", "codex", "session-1", "user", "private", "/work")]
    source = SessionSource(type="codex-jsonl", fingerprint="a" * 64)
    result = ingest_session("codex", "session-1", logs, source)
    assert result.status == "ingested"
    assert result.manifest is not None
    generation = session_store_root() / "codex" / result.lineage_id / result.generation_id
    assert validate_session_generation(generation, result.manifest) == logs
    assert stat.S_IMODE(generation.stat().st_mode) == 0o700
    assert stat.S_IMODE((generation / "manifest.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((generation / "transcript.jsonl").stat().st_mode) == 0o600
    assert ingest_session("codex", "session-1", logs, source).status == "duplicate"


def test_concurrent_ingestion_converges_and_corruption_fails(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [SessionLog("", "claude", "same", "assistant", "answer")]
    source = SessionSource(fingerprint="b" * 64)
    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(executor.map(lambda _: ingest_session("claude", "same", logs, source).status, range(4)))
    assert statuses.count("ingested") == 1
    assert statuses.count("duplicate") == 3
    lineage = session_lineage_id("claude", "same")
    generation = session_store_root() / "claude" / lineage / session_generation_id("b" * 64)
    (generation / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        ingest_session("claude", "same", logs, source)


def test_transcript_is_compact_utf8_jsonl(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = ingest_session(
        "agy",
        "unicode",
        [SessionLog("", "agy", "unicode", "user", "café <ok>")],
        SessionSource(fingerprint="c" * 64),
    )
    path = session_store_root() / "agy" / result.lineage_id / result.generation_id / "transcript.jsonl"
    assert json.loads(path.read_text(encoding="utf-8"))["content"] == "café <ok>"
    assert b"caf\xc3\xa9 <ok>" in path.read_bytes()


def test_ingestion_rejects_agent_paths_before_touching_outside_store(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    agent = str(outside)

    with pytest.raises(ValueError, match="invalid agent format"):
        ingest_session(
            agent,
            "session-1",
            [SessionLog("", agent, "session-1", "user", "private")],
            SessionSource(fingerprint="d" * 64),
        )

    assert not outside.exists()


def test_duplicate_ingestion_rejects_generation_with_public_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [SessionLog("", "codex", "private-session", "user", "secret")]
    source = SessionSource(fingerprint="e" * 64)
    result = ingest_session("codex", "private-session", logs, source)
    generation = session_store_root() / "codex" / result.lineage_id / result.generation_id
    transcript = generation / "transcript.jsonl"
    transcript.chmod(0o644)

    with pytest.raises(ValueError, match="not owner-only"):
        ingest_session("codex", "private-session", logs, source)


def test_publish_owner_only_fails_if_parent_is_swapped_after_open(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    parent = tmp_path / "store"
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    parent.mkdir(mode=0o700)
    outside.mkdir(mode=0o700)
    target = parent / "record.json"
    original_open = session_store.os.open
    swapped = False

    def swap_parent(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if isinstance(path, str) and path.startswith(f".{target.name}.") and not swapped:
            parent.rename(moved)
            parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(session_store.os, "open", swap_parent)

    with pytest.raises(ValueError, match="parent changed during publication"):
        session_store.publish_owner_only(target, b"private")

    assert not (outside / target.name).exists()
    assert (moved / target.name).read_bytes() == b"private"

    with pytest.raises(OSError, match="store"):
        session_store.publish_owner_only(parent / "second.json", b"secret")
    assert not (outside / "second.json").exists()


def test_atomic_publication_fsyncs_generation_lineage_and_target_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    synced_directories: set[tuple[int, int]] = set()
    real_fsync = session_store.os.fsync

    def record_fsync(descriptor: int) -> None:
        info = os.fstat(descriptor)
        if stat.S_ISDIR(info.st_mode):
            synced_directories.add((info.st_dev, info.st_ino))
        real_fsync(descriptor)

    monkeypatch.setattr(session_store.os, "fsync", record_fsync)
    result = ingest_session(
        "codex",
        "durable",
        [SessionLog("", "codex", "durable", "user", "private")],
        SessionSource(fingerprint="f" * 64),
    )
    generation = session_store_root() / "codex" / result.lineage_id / result.generation_id
    target = tmp_path / "usage" / "record.json"
    publish_owner_only(target, b"private")

    expected = {
        (generation.stat().st_dev, generation.stat().st_ino),
        (generation.parent.stat().st_dev, generation.parent.stat().st_ino),
        (target.parent.stat().st_dev, target.parent.stat().st_ino),
    }
    assert expected <= synced_directories


def test_publish_owner_only_is_private_concurrent_and_cleans_failed_temps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "private" / "state.json"
    publish_owner_only(target, b"initial")
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.stat().st_mode) == 0o600

    target.chmod(0o644)
    payloads = [f"writer-{number}:".encode() + bytes([number]) * 65_536 for number in range(8)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda payload: publish_owner_only(target, payload), payloads))

    assert target.read_bytes() in payloads
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(target.parent.glob(f".{target.name}.*")) == []

    retained = target.read_bytes()
    with monkeypatch.context() as scoped:
        scoped.setattr(session_store.os, "fchmod", lambda *_args: (_ for _ in ()).throw(OSError("chmod failed")))
        with pytest.raises(OSError, match="chmod failed"):
            publish_owner_only(target, b"unpublished")
    assert target.read_bytes() == retained
    assert list(target.parent.glob(f".{target.name}.*")) == []

    with monkeypatch.context() as scoped:
        scoped.setattr(
            session_store.os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("rename failed"))
        )
        with pytest.raises(OSError, match="rename failed"):
            publish_owner_only(target, b"unpublished")
    assert target.read_bytes() == retained
    assert list(target.parent.glob(f".{target.name}.*")) == []


def test_fingerprints_preserve_file_bytes_go_json_escaping_and_log_encoding(tmp_path: Path) -> None:
    content = b"a" * (1024 * 1024 + 1)
    source = tmp_path / "source.jsonl"
    source.write_bytes(content)
    assert fingerprint_file(source) == hashlib.sha256(content).hexdigest()

    structured = {"html": "<&>\u2028\u2029", "utf8": "café"}
    go_encoded = b'{"html":"\\u003c\\u0026\\u003e\\u2028\\u2029","utf8":"caf\xc3\xa9"}'
    assert fingerprint_json(structured) == hashlib.sha256(go_encoded).hexdigest()

    logs = [SessionLog("", "codex", "session-1", "user", "café <&>\u2028\u2029", "/repo", "gpt")]
    encoded = marshal_session_logs(logs)
    go_transcript = (
        b'{"ts":"","agent":"codex","sid":"session-1","role":"user","content":"caf\xc3\xa9 '
        b'<&>\\u2028\\u2029","cwd":"/repo","model":"gpt"}\n'
    )
    assert encoded == go_transcript
    assert json.loads(encoded)["cwd"] == "/repo"
    assert json.loads(encoded)["model"] == "gpt"
    assert fingerprint_logs(logs) == hashlib.sha256(go_transcript).hexdigest()


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"completeness": "unknown"}, "invalid completeness"),
        ({"agent": ""}, "invalid manifest field agent"),
        ({"record_count": True}, "invalid manifest field record_count"),
        ({"malformed_records": -1}, "invalid manifest field malformed_records"),
    ],
)
def test_manifest_rejects_invalid_fields(change: dict[str, object], match: str) -> None:
    transcript = marshal_session_logs([SessionLog("", "codex", "session-1", "user", "hello")])
    value = _manifest_for(transcript).to_dict()
    value.update(change)

    with pytest.raises(ValueError, match=match):
        SessionManifest.from_dict(value)


def test_manifest_and_records_reject_missing_or_wrong_typed_input(tmp_path: Path) -> None:
    transcript = marshal_session_logs([SessionLog("", "codex", "session-1", "user", "hello")])
    value = _manifest_for(transcript).to_dict()
    del value["schema_version"]
    with pytest.raises(ValueError, match="invalid session manifest"):
        SessionManifest.from_dict(value)

    required = {"ts": "", "agent": "codex", "sid": "session-1", "role": "user", "content": 1}
    with pytest.raises(ValueError, match="invalid normalized transcript record"):
        SessionLog.from_dict(required)
    required["content"] = "hello"
    required["cwd"] = []
    with pytest.raises(ValueError, match="invalid normalized transcript record"):
        SessionLog.from_dict(required)

    generation = tmp_path / "generation"
    generation.mkdir(mode=0o700)
    manifest_path = generation / "manifest.json"
    manifest_path.write_text("[]\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    with pytest.raises(ValueError, match="invalid session manifest"):
        read_session_manifest(generation)


@pytest.mark.parametrize(
    ("transcript", "record_count", "high_water", "match"),
    [
        (b"\xff", 1, "2026-08-01T12:00:00Z", "invalid normalized transcript record"),
        (b"{broken\n", 1, "2026-08-01T12:00:00Z", "invalid normalized transcript record 1"),
        (b"[]\n", 1, "2026-08-01T12:00:00Z", "invalid normalized transcript record 1"),
        (
            b'{"ts":"","agent":"codex","sid":"session-1","role":"user","content":1}\n',
            1,
            "2026-08-01T12:00:00Z",
            "invalid normalized transcript record 1",
        ),
        (
            b'{"ts":"","agent":"codex","sid":"session-1","role":"user","content":"ok","cwd":[]}\n',
            1,
            "2026-08-01T12:00:00Z",
            "invalid normalized transcript record 1",
        ),
        (
            b'{"ts":"2026-08-01T12:00:00Z","agent":"claude","sid":"session-1","role":"user","content":"ok"}\n',
            1,
            "2026-08-01T12:00:00Z",
            "mismatched lineage",
        ),
        (
            b'{"ts":"2026-08-01T12:00:00Z","agent":"codex","sid":"session-1","role":"user","content":"ok"}\n',
            2,
            "2026-08-01T12:00:00Z",
            "contains 1 records, expected 2",
        ),
        (
            b'{"ts":"2026-08-02T12:00:00Z","agent":"codex","sid":"session-1","role":"user","content":"ok"}\n',
            1,
            "2026-08-01T12:00:00Z",
            "high-water mark",
        ),
    ],
)
def test_generation_integrity_rejects_malformed_or_contradictory_transcripts(
    tmp_path: Path, transcript: bytes, record_count: int, high_water: str, match: str
) -> None:
    manifest = _manifest_for(transcript, record_count=record_count, high_water=high_water)
    generation = tmp_path / "generation"
    _write_generation(generation, manifest, transcript)

    with pytest.raises(ValueError, match=match):
        validate_session_generation(generation, manifest)


def test_generation_integrity_rejects_manifest_round_trip_mismatch(tmp_path: Path) -> None:
    transcript = marshal_session_logs([SessionLog("2026-08-01T12:00:00Z", "codex", "session-1", "user", "hello")])
    manifest = _manifest_for(transcript)
    generation = tmp_path / "generation"
    _write_generation(generation, manifest, transcript)

    with pytest.raises(ValueError, match="manifest did not round-trip"):
        validate_session_generation(generation, replace(manifest, source_type="other"))


def test_generation_validation_rejects_symlinks_and_hard_links(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    symlink_generation, symlink_manifest = _generation("codex", "symlinked", "1" * 64)
    moved_generation = tmp_path / "moved-generation"
    symlink_generation.rename(moved_generation)
    symlink_generation.symlink_to(moved_generation, target_is_directory=True)
    with pytest.raises(ValueError, match="directory is a symbolic link"):
        validate_session_generation(symlink_generation, symlink_manifest)

    file_generation, file_manifest = _generation("codex", "linked-file", "2" * 64)
    transcript = file_generation / "transcript.jsonl"
    outside_link = tmp_path / "outside-transcript.jsonl"
    outside_link.hardlink_to(transcript)
    with pytest.raises(ValueError, match="multiple hard links"):
        validate_session_generation(file_generation, file_manifest)

    manifest_generation, _ = _generation("codex", "manifest-link", "3" * 64)
    manifest_path = manifest_generation / "manifest.json"
    outside_manifest = tmp_path / "outside-manifest.json"
    manifest_path.rename(outside_manifest)
    manifest_path.symlink_to(outside_manifest)
    with pytest.raises(ValueError, match="file is a symbolic link"):
        read_session_manifest(manifest_generation)

    wrong_type_generation, wrong_type_manifest = _generation("codex", "wrong-type", "a" * 64)
    wrong_type_transcript = wrong_type_generation / "transcript.jsonl"
    wrong_type_transcript.unlink()
    wrong_type_transcript.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="path is not a file"):
        validate_session_generation(wrong_type_generation, wrong_type_manifest)


def test_ingestion_secures_directories_and_rejects_agent_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = session_store_root()
    agent_directory = root / "codex"
    lineage_directory = agent_directory / session_lineage_id("codex", "permissions")
    lineage_directory.mkdir(mode=0o755, parents=True)
    for path in (root, agent_directory, lineage_directory):
        path.chmod(0o755)

    ingest_session(
        "codex",
        "permissions",
        [SessionLog("", "codex", "permissions", "user", "private")],
        SessionSource(fingerprint="b" * 64),
    )

    assert all(stat.S_IMODE(path.stat().st_mode) == 0o700 for path in (root, agent_directory, lineage_directory))

    outside = tmp_path / "outside-agent"
    outside.mkdir(mode=0o700)
    (root / "claude").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="refusing symbolic link"):
        ingest_session(
            "claude",
            "linked-agent",
            [SessionLog("", "claude", "linked-agent", "user", "private")],
            SessionSource(fingerprint="c" * 64),
        )
    assert list(outside.iterdir()) == []


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

    assert result.manifest is not None
    assert [log.model for log in logs] == ["first", "first", "first", "second", "second"]
    assert result.manifest.source_type == "normalized"
    assert result.manifest.source_fingerprint == fingerprint_logs(logs)
    assert result.manifest.high_water_mark == "2026-08-01T14:00:00Z"
    assert result.manifest.completeness == "complete"


def test_ingestion_reports_skips_and_rejects_invalid_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    skipped = ingest_session("codex", "empty", [], SessionSource(type="fixture", malformed=2, skipped=3))
    assert skipped.status == "skipped"
    assert skipped.manifest is not None
    assert skipped.manifest.completeness == "partial"
    assert skipped.manifest.skipped_records == 3
    assert "records=0 malformed=2 skipped=3 completeness=partial" in report_ingestion(skipped)
    assert not session_store_root().exists()

    default_skip = ingest_session("codex", "empty-default", [])
    assert default_skip.manifest is not None
    assert default_skip.manifest.completeness == "complete"
    assert default_skip.manifest.skipped_records == 1
    with pytest.raises(ValueError, match="missing its manifest"):
        report_ingestion(SessionIngestionResult("skipped", "lineage"))

    valid = SessionLog("", "codex", "valid", "user", "hello")
    for invalid in ("", "../escape", "space separated"):
        with pytest.raises(ValueError, match="invalid session_id format"):
            ingest_session("codex", invalid, [replace(valid, sid=invalid)])
        assert not is_valid_session_id(invalid)
    assert is_valid_session_id("safe_ID-1")

    with pytest.raises(ValueError, match="record 1 does not match its lineage"):
        ingest_session("codex", "valid", [replace(valid, agent="claude")])
    for fingerprint in ("short", "g" * 64):
        with pytest.raises(ValueError, match="full SHA-256 digest"):
            ingest_session("codex", "valid", [valid], SessionSource(fingerprint=fingerprint))


def test_stored_generation_requires_exact_safe_immutable_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    fingerprint = "4" * 64
    assert stored_generation("codex", "stored", "") is None
    assert stored_generation(str(tmp_path / "outside"), "stored", fingerprint) is None
    assert stored_generation("codex", "../stored", fingerprint) is None
    assert stored_generation("codex", "stored", fingerprint) is None

    generation, manifest = _generation("codex", "stored", fingerprint)
    assert stored_generation("codex", "stored", fingerprint) == manifest

    manifest_path = generation / "manifest.json"
    original = manifest.to_dict()
    for field, value in (
        ("schema_version", 2),
        ("parser_version", "2"),
        ("agent", "claude"),
        ("session_id", "other"),
        ("lineage_id", "0" * 64),
        ("source_fingerprint", "5" * 64),
    ):
        changed = dict(original)
        changed[field] = value
        manifest_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")
        manifest_path.chmod(0o600)
        with pytest.raises(ValueError, match="stored session generation does not match its immutable identity"):
            stored_generation("codex", "stored", fingerprint)

    manifest_path.write_text("{broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid session manifest"):
        stored_generation("codex", "stored", fingerprint)


@pytest.mark.parametrize(
    ("damage", "match"),
    [
        ("missing", "could not be read"),
        ("corrupt", "fingerprint mismatch"),
        ("public", "not owner-only"),
        ("hard-linked", "multiple hard links"),
    ],
)
def test_stored_generation_validates_complete_transcript(
    damage: str, match: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    fingerprint = "d" * 64
    generation, _ = _generation("codex", "stored-transcript", fingerprint)
    transcript = generation / "transcript.jsonl"

    if damage == "missing":
        transcript.unlink()
    elif damage == "corrupt":
        transcript.write_text("{}\n", encoding="utf-8")
    elif damage == "public":
        transcript.chmod(0o644)
    else:
        (tmp_path / "outside-transcript.jsonl").hardlink_to(transcript)

    with pytest.raises(ValueError, match=match):
        stored_generation("codex", "stored-transcript", fingerprint)


def test_existing_generation_identity_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logs = [SessionLog("", "codex", "conflict", "user", "private")]
    source = SessionSource(fingerprint="6" * 64)
    generation, manifest = _generation("codex", "conflict", source.fingerprint)
    manifest_path = generation / "manifest.json"
    manifest_path.write_text(
        json.dumps(replace(manifest, source_fingerprint="7" * 64).to_dict()) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match its immutable identity"):
        ingest_session("codex", "conflict", logs, source)


@pytest.mark.parametrize("outcome", ["same", "mismatch", "missing"])
def test_ingestion_rename_races_converge_or_fail_without_temp_residue(
    outcome: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    session_id = f"race-{outcome}"
    logs = [SessionLog("", "codex", session_id, "user", "private")]
    fingerprint = "8" * 64

    lineage = session_store_root() / "codex" / session_lineage_id("codex", session_id)

    def race(source_name, destination_name, *, src_dir_fd=None, dst_dir_fd=None) -> None:
        assert src_dir_fd == dst_dir_fd
        if outcome == "missing":
            raise PermissionError("rename denied")
        temp = lineage / source_name
        final = lineage / destination_name
        shutil.copytree(temp, final)
        if outcome == "mismatch":
            manifest_path = final / "manifest.json"
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            value["source_fingerprint"] = "9" * 64
            manifest_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            manifest_path.chmod(0o600)
        raise FileExistsError("concurrent publication")

    monkeypatch.setattr(session_store.os, "rename", race)
    if outcome == "same":
        assert ingest_session("codex", session_id, logs, SessionSource(fingerprint=fingerprint)).status == "duplicate"
    elif outcome == "mismatch":
        with pytest.raises(ValueError, match="concurrent session generation has mismatched identity"):
            ingest_session("codex", session_id, logs, SessionSource(fingerprint=fingerprint))
    else:
        with pytest.raises(PermissionError, match="rename denied"):
            ingest_session("codex", session_id, logs, SessionSource(fingerprint=fingerprint))

    assert list(lineage.glob(".ingest-*")) == []


def test_ingestion_temp_generation_stays_confined_when_lineage_is_swapped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    session_id = "lineage-swap"
    lineage = session_lineage_id("codex", session_id)
    lineage_directory = session_store_root() / "codex" / lineage
    moved = tmp_path / "moved-lineage"
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    original_mkdir = session_store.os.mkdir
    swapped = False

    def swap_lineage(path, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if Path(path).name.startswith(".ingest-") and not swapped:
            lineage_directory.rename(moved)
            lineage_directory.symlink_to(outside, target_is_directory=True)
            swapped = True
        return original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(session_store.os, "mkdir", swap_lineage)

    with pytest.raises(ValueError, match="lineage changed during ingestion"):
        ingest_session(
            "codex",
            session_id,
            [SessionLog("", "codex", session_id, "user", "private")],
            SessionSource(fingerprint="a" * 64),
        )

    assert swapped
    assert list(outside.iterdir()) == []
    assert list(moved.iterdir()) == []
