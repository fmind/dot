from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from fmind_dot.archive import parsers as pmod
from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    agy_workspaces,
    claude_parent_session_id,
    claude_session_id,
    parse_agy_session,
    parse_claude_session,
    parse_pi_session,
    pi_session_id,
    resolve_cwd,
)


def _w_jsonl(path: Path, rows: list[dict[str, object] | str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [(json.dumps(r) if isinstance(r, dict) else r) + "\n" for r in rows]
    path.write_text("".join(lines), encoding="utf-8")
    return path


def test_resolve_cwd_and_agy_transcript_estimated_and_measured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_cwd("~/work") == str((tmp_path / "work").resolve())
    with monkeypatch.context() as mp:
        mp.setattr(Path, "expanduser", lambda _self: (_ for _ in ()).throw(RuntimeError("bad")))
        with pytest.raises(ValueError, match="cannot expand"):
            resolve_cwd("~/bad")

    path = _w_jsonl(
        tmp_path / "agy.jsonl",
        [
            {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hello", "created_at": "2026-11-15T00:00:00Z"},
            {
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "world",
                "thinking": "plan",
                "created_at": "2026-11-15T00:01:00Z",
            },
            {"type": "RUN_COMMAND", "content": "ls", "truncated_fields": ["content"]},
            "{bad json",
            "123",
        ],
    )
    est = parse_agy_session(path, "agy-1", "~/repo")
    assert len(est.logs) == 2
    assert est.malformed == 2
    assert est.usage is not None
    assert est.usage.measurement_kind == "estimated"
    assert est.usage.turn_count == 1
    assert parse_agy_session(path, "agy-1", "~/other").fingerprint != est.fingerprint

    measured_path = _w_jsonl(
        tmp_path / "agy_m.jsonl",
        [
            {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "q", "created_at": "2026-11-15T01:00:00Z"},
            {
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "a",
                "created_at": "2026-11-15T01:01:00Z",
                "input_tokens": 8,
                "output_tokens": 4,
                "cache_read_tokens": 2,
            },
        ],
    )
    res = parse_agy_session(measured_path, "agy-2")
    assert res.usage is not None
    assert res.usage.measurement_kind == "provider-reported"
    assert res.usage.total_tokens == 14

    bad_u = _w_jsonl(
        tmp_path / "agy_bad.jsonl",
        [{"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "a", "input_tokens": -1}],
    )
    assert parse_agy_session(bad_u, "agy-3").usage_error is not None

    # A null/zero-cache counter row without any measured input/output falls back to byte estimates.
    null_u = _w_jsonl(
        tmp_path / "agy_null.jsonl",
        [
            {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hello", "created_at": "2026-11-15T01:00:00Z"},
            {
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "world",
                "created_at": "2026-11-15T01:01:00Z",
                "input_tokens": None,
                "cache_read_tokens": 0,
            },
        ],
    )
    est_fallback = parse_agy_session(null_u, "agy-4")
    assert est_fallback.usage is not None
    assert est_fallback.usage.measurement_kind == "estimated"
    assert est_fallback.usage.input_tokens > 0


def test_parse_claude_session_dedup_cache_cost_and_sidechain(tmp_path: Path) -> None:
    assert claude_session_id(tmp_path / "memory.jsonl") == ""
    assert claude_session_id(tmp_path / "abc.jsonl") == "abc"
    sub = tmp_path / "parent-1/subagents/agent-1.jsonl"
    assert claude_parent_session_id(sub) == "parent-1"

    path = _w_jsonl(
        sub,
        [
            {
                "type": "user",
                "timestamp": "2026-11-15T00:00:00Z",
                "cwd": str(tmp_path),
                "isMeta": True,
                "message": {"content": "sys"},
            },
            {
                "type": "assistant",
                "requestId": "req1",
                "timestamp": "2026-11-15T00:01:00Z",
                "message": {
                    "id": "msg1",
                    "model": "claude-sonnet-4-5",
                    "content": [{"type": "text", "text": "step 1"}],
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_creation": {"ephemeral_1h_input_tokens": 2},
                    },
                },
            },
            {
                "type": "assistant",
                "requestId": "req1",
                "timestamp": "2026-11-15T00:02:00Z",
                "message": {
                    "id": "msg1",
                    "model": "<synthetic>",
                    "content": [],
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 12,
                        "cache_read_input_tokens": 3,
                        "cache_creation_input_tokens": 4,
                    },
                },
            },
            {"type": "cost-state", "totalCostUSD": 0.42, "hasUnknownModelCost": False},
            {"type": "cost-state", "hasUnknownModelCost": False},
        ],
    )
    parsed = parse_claude_session(path, "agent-1")
    assert parsed.sidechain is True
    assert parsed.parent_session_id == "parent-1"
    assert parsed.logs[0].meta is True
    assert parsed.logs[0].model == "claude-sonnet-4-5"
    assert parsed.usage is not None
    assert (parsed.usage.output_tokens, parsed.usage.cache_write_1h_tokens, parsed.usage.cost_usd) == (12, 2, 0.42)

    bad_cwd = _w_jsonl(
        tmp_path / "c_bad_cwd.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-11-15T00:00:00Z",
                "cwd": "~no-such-claude-user/proj",
                "message": {"content": "hello"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-11-15T00:01:00Z",
                "message": {"model": "claude-sonnet-4-5", "content": [{"type": "text", "text": "ok"}]},
            },
        ],
    )
    bad_cwd_res = parse_claude_session(bad_cwd, "c_bad_cwd")
    assert len(bad_cwd_res.logs) == 2
    assert bad_cwd_res.logs[0].cwd == ""
    assert bad_cwd_res.usage_error is not None

    bad_cost = _w_jsonl(tmp_path / "c_bad.jsonl", [{"type": "cost-state", "hasUnknownModelCost": "yes"}])
    assert parse_claude_session(bad_cost, "c_bad").usage_error is not None


def test_parse_pi_session_forks_tool_results_and_cost(tmp_path: Path) -> None:
    assert pi_session_id(tmp_path / "2026-11-15_pi-123.jsonl") == "pi-123"
    forked = _w_jsonl(
        tmp_path / "2026_pi-1.jsonl",
        [
            {"type": "session", "cwd": str(tmp_path), "parentSession": "orig", "timestamp": "2026-11-15T02:00:00Z"},
            {
                "type": "message",
                "timestamp": "2026-11-15T01:00:00Z",
                "message": {"role": "user", "content": "pre-fork"},
            },
            {
                "type": "message",
                "timestamp": "2026-11-15T02:01:00Z",
                "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            },
            {
                "type": "message",
                "timestamp": "2026-11-15T02:02:00Z",
                "message": {
                    "role": "assistant",
                    "model": "gpt-5",
                    "content": [{"type": "text", "text": "ok"}],
                    "usage": {"input": 5, "output": 3, "cacheWrite": 2, "cacheWrite1h": 1, "cost": {"total": 0.02}},
                },
            },
            {
                "type": "message",
                "timestamp": "2026-11-15T02:03:00Z",
                "message": {"role": "toolResult", "usage": {"input": 1, "output": 1, "cost": {"total": 0.01}}},
            },
        ],
    )
    res = parse_pi_session(forked, "pi-1")
    assert [ln.content for ln in res.logs] == ["hi", "ok"]
    assert res.usage is not None
    assert res.usage.input_tokens == 6
    assert res.usage.cost_usd == pytest.approx(0.03)
    assert res.usage.cwd == str(tmp_path.resolve())

    bad_fork = _w_jsonl(
        tmp_path / "bad_pi.jsonl",
        [
            {"type": "session", "parentSession": "p", "timestamp": "bad"},
            {
                "type": "message",
                "timestamp": "2026-11-15T02:00:00Z",
                "message": {"role": "assistant", "usage": {"input": 1}},
            },
        ],
    )
    assert parse_pi_session(bad_fork, "bad").usage_error is not None


def test_agent_adapters_enumeration_and_agy_workspaces(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = tmp_path / "brain"
    (brain / "agy-1/.system_generated/logs").mkdir(parents=True)
    _w_jsonl(brain / "agy-1/.system_generated/logs/transcript_full.jsonl", [{"type": "x"}])
    db = tmp_path / pmod.AGY_SUMMARIES_NAME
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE conversation_summaries(conversation_id TEXT, workspace_uris TEXT)")
        conn.execute(
            "INSERT INTO conversation_summaries VALUES ('agy-1', ?)",
            (json.dumps(["https://x", (tmp_path / "proj").as_uri()]),),
        )
    assert agy_workspaces(brain) == {"agy-1": str(tmp_path / "proj")}
    assert AGENT_ADAPTERS["agy"].enumerate(brain)[0][1] == str(tmp_path / "proj")

    monkeypatch.setattr(pmod, "_AGY_SUMMARIES_LIMIT", 0)
    with pytest.raises(ValueError, match="exceed"):
        agy_workspaces(brain)

    cl = tmp_path / "claude"
    _w_jsonl(cl / "proj/s1.jsonl", [{"type": "user"}])
    _w_jsonl(cl / "proj/memory.jsonl", [{"type": "user"}])
    assert [sid for sid, _, _ in AGENT_ADAPTERS["claude"].enumerate(cl)] == ["s1"]
