from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fmind_dot.archive.store import (
    BUNDLE_SUFFIX,
    READABLE_PARSER_VERSIONS,
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SessionLog,
    SessionManifest,
    SessionSource,
    discover_session_bundles,
    ingest_session,
    is_valid_session_id,
    parse_utc_instant,
    propagate_models,
    read_session_manifest,
    session_bundle_path,
    usage_window,
)


def _logs(agent: str = "claude", sid: str = "s1", count: int = 2, model: str = "m1") -> list[SessionLog]:
    return [
        SessionLog(
            f"2026-11-15T00:0{i}:00Z",
            agent,
            sid,
            "user" if i % 2 == 0 else "assistant",
            f"hi {i}",
            "/w",
            model if i else "",
        )
        for i in range(count)
    ]


def test_session_id_model_propagation_and_usage_window() -> None:
    assert is_valid_session_id("abc_123-z") is True
    assert is_valid_session_id("../bad") is False
    logs = [
        SessionLog("t1", "pi", "s", "user", "q"),
        SessionLog("t2", "pi", "s", "assistant", "a", model="sonnet"),
        SessionLog("t3", "pi", "s", "user", "q2"),
    ]
    propagate_models(logs)
    assert [ln.model for ln in logs] == ["sonnet", "sonnet", "sonnet"]
    assert logs[0].to_dict()["model"] == "sonnet"

    assert usage_window(None) == ("", "")
    assert usage_window({"samples": [{"timestamp": "2026-11-15T02:00:00Z"}, {"timestamp": "bad"}]}) == ("", "")
    w = usage_window({"samples": [{"timestamp": "2026-11-15T02:00:00Z"}, {"timestamp": "2026-11-15T01:00:00Z"}]})
    assert w == ("2026-11-15T01:00:00+00:00", "2026-11-15T02:00:00+00:00")
    assert parse_utc_instant("2026-11-15T00:00:00") == datetime(2026, 11, 15, tzinfo=UTC)


def test_manifest_validation_and_bundle_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    base = {
        "agent": "pi",
        "session_id": "s1",
        "parser_version": SESSION_PARSER_VERSION,
        "source_type": "pi-jsonl",
        "source_fingerprint": "fp",
        "ingested_at": "2026-11-15T00:00:00Z",
        "completeness": "complete",
        "record_count": 1,
        "schema_version": SESSION_SCHEMA_VERSION,
    }
    for pv in (READABLE_PARSER_VERSIONS[0], SESSION_PARSER_VERSION):
        assert SessionManifest.from_dict(base | {"parser_version": pv}).parser_version == pv
    with pytest.raises(ValueError, match="newer dot"):
        SessionManifest.from_dict(base | {"schema_version": SESSION_SCHEMA_VERSION + 1})
    with pytest.raises(ValueError, match="unsupported session format"):
        SessionManifest.from_dict(base | {"parser_version": "6"})
    with pytest.raises(ValueError, match="dot stats"):
        SessionManifest.from_dict(base | {"parser_version": "6"})
    with pytest.raises(ValueError, match="invalid session manifest"):
        SessionManifest.from_dict(base | {"usage": {}})
    with pytest.raises(ValueError, match="invalid session manifest"):
        SessionManifest.from_dict(base | {"record_count": True})
    with pytest.raises(ValueError, match="invalid session manifest"):
        SessionManifest.from_dict(base | {"sidechain": "yes"})
    with pytest.raises(ValueError, match="invalid session manifest identity"):
        SessionManifest.from_dict(base | {"session_id": "../bad"})
    with pytest.raises(ValueError, match="invalid session target"):
        session_bundle_path("pi", "../bad")

    assert discover_session_bundles() == []
    bundle = session_bundle_path("pi", "s1")
    bundle.parent.mkdir(parents=True)
    bundle.write_bytes(json.dumps(base | {"agent": "claude"}).encode() + b"\nnull\n")
    with pytest.raises(ValueError, match="does not match its path"):
        read_session_manifest(bundle)
    bundle.write_bytes(b"null\n")
    with pytest.raises(ValueError, match="invalid session manifest"):
        read_session_manifest(bundle)


def test_ingest_session_lifecycle_retains_stronger_usage_and_longer_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert ingest_session("claude", "empty", []).status == "skipped"

    with pytest.raises(ValueError, match="does not match its session"):
        ingest_session("claude", "s1", _logs(agent="pi"))

    usage = {
        "timestamp": "2026-11-15T00:01:00Z",
        "harness": "claude",
        "agent": "claude",
        "session_id": "s1",
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "measurement_kind": "provider-reported",
        "cost_usd": 0.1,
        "cost_known": True,
        "schema_version": "dot.agent.usage/v3",
        "extractor_version": "2",
    }
    r1 = ingest_session("claude", "s1", _logs(), SessionSource("claude-jsonl", "fp1", "sig1"), usage=usage)
    assert r1.status == "ingested"

    r2 = ingest_session("claude", "s1", _logs(), SessionSource("claude-jsonl", "fp1", "sig2"), usage=usage)
    assert r2.status == "unchanged"
    assert read_session_manifest(session_bundle_path("claude", "s1")).source_signature == "sig2"

    r3 = ingest_session("claude", "s1", _logs(count=1), SessionSource("claude-jsonl", "fp2", "sig3"), usage=usage)
    assert r3.status == "retained"
    assert r3.manifest.record_count == 2

    weaker = usage | {"measurement_kind": "estimated", "cost_usd": None, "cost_known": False}
    r4 = ingest_session("claude", "s1", _logs(count=2), SessionSource("claude-jsonl", "fp1", "sig4"), usage=weaker)
    assert r4.status == "retained"
    assert r4.current_transcript is True

    r5 = ingest_session("claude", "s1", _logs(count=3), SessionSource("claude-jsonl", "fp3", "sig5"), usage=weaker)
    assert r5.status == "retained"
    assert r5.manifest.record_count == 3
    assert r5.manifest.usage == usage
    assert len(discover_session_bundles()) == 1
    assert discover_session_bundles()[0].suffix == BUNDLE_SUFFIX
