from __future__ import annotations

import json
import os
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
    parse_copilot_session,
    parse_opencode_session,
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
                "message": {
                    "role": "assistant",
                    "content": "pre-fork",
                    "usage": {"input": 999, "output": 888, "cost": {"total": 9.99}},
                },
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
            (
                json.dumps(
                    [
                        "https://x",
                        "file://evil.example/repo",
                        "file:///tmp/bad%00path",
                        (tmp_path / "proj").as_uri(),
                    ]
                ),
            ),
        )
        conn.execute("INSERT INTO conversation_summaries VALUES ('agy-bad-json', '{bad')")
    assert agy_workspaces(brain) == {"agy-1": str(tmp_path / "proj")}
    assert AGENT_ADAPTERS["agy"].enumerate(brain)[0][1] == str(tmp_path / "proj")

    monkeypatch.setattr(pmod, "_AGY_SUMMARIES_LIMIT", 0)
    with pytest.raises(ValueError, match="exceed"):
        agy_workspaces(brain)

    cl = tmp_path / "claude"
    _w_jsonl(cl / "proj/s1.jsonl", [{"type": "user"}])
    _w_jsonl(cl / "proj/memory.jsonl", [{"type": "user"}])
    assert [sid for sid, _, _ in AGENT_ADAPTERS["claude"].enumerate(cl)] == ["s1"]


def test_parse_copilot_session_token_details_samples_and_legacy_fallback(tmp_path: Path) -> None:
    db = tmp_path / "session-store.db"
    proj = tmp_path / "proj"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, turn_index INTEGER, "
            "user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, "
            "turn_index INTEGER, model TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, "
            "cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER, "
            "token_details_json TEXT, created_at TEXT);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-1', ?, '2026-11-17T14:00:00Z')", (str(proj),))
        conn.execute(
            "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES "
            "('cop-1', 0, 'check status', 'all green', '2026-11-17T14:03:00Z')"
        )
        details = json.dumps(
            [
                {"tokenType": "input", "tokenCount": 3},
                {"tokenType": "cache_read", "tokenCount": 38148},
                {"tokenType": "cache_write", "tokenCount": 123},
                {"tokenType": "output", "tokenCount": 417},
            ]
        )
        conn.execute(
            "INSERT INTO assistant_usage_events (session_id, turn_index, model, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, reasoning_tokens, token_details_json, created_at) "
            "VALUES ('cop-1', 0, 'gpt-6.1-terra', 38274, 417, 38148, 123, 309, ?, '2026-11-17T14:03:02.808Z')",
            (details,),
        )
        # Second event without token_details_json exercises OpenAI prompt-inclusive subtraction fallback.
        conn.execute(
            "INSERT INTO assistant_usage_events (session_id, turn_index, model, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, reasoning_tokens, token_details_json, created_at) "
            "VALUES ('cop-1', 0, 'gpt-6-luna', 100, 20, 80, 10, 5, NULL, '2026-11-17T14:03:10.000Z')"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-bad', ?, '2026-11-17T14:00:00Z')", (str(proj),))
        conn.execute(
            "INSERT INTO assistant_usage_events (session_id, turn_index, model, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, reasoning_tokens, token_details_json, created_at) "
            "VALUES ('cop-bad', 0, 'gpt-6-luna', 10, 5, 0, 0, 0, '{bad', '2026-11-17T14:04:00Z')"
        )

    db.with_name("session-store.db-wal").write_bytes(b"wal-bytes")
    assert [sid for sid, _, _ in AGENT_ADAPTERS["copilot"].enumerate(db)] == ["cop-1", "cop-bad"]

    parsed = parse_copilot_session(db, "cop-1")
    assert [ln.role for ln in parsed.logs] == ["user", "assistant"]
    assert parsed.logs[0].model == "gpt-6-luna"
    assert parsed.usage is not None
    assert parsed.usage.model == "mixed"
    assert parsed.usage.input_tokens == 13
    assert parsed.usage.cached_tokens == 38228
    assert parsed.usage.cache_write_tokens == 133
    assert parsed.usage.output_tokens == 437
    assert parsed.usage.total_tokens == 13 + 38228 + 133 + 437
    assert len(parsed.usage.samples) == 2
    assert 0 < parsed.usage.source_bytes < db.stat().st_size

    assert parse_copilot_session(db, "cop-bad").usage_error is not None
    with pytest.raises(ValueError, match="disappeared"):
        parse_copilot_session(db, "cop-missing")
    with pytest.raises(ValueError, match="invalid copilot session id"):
        parse_copilot_session(db, "../bad")

    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("INSERT INTO sessions VALUES ('cop-no-inp', ?, '2026-11-17T14:00:00Z')", (str(proj),))
        conn.execute(
            "INSERT INTO assistant_usage_events (session_id, turn_index, model, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, reasoning_tokens, token_details_json, created_at) "
            "VALUES ('cop-no-inp', 0, 'claude-sonnet-4-5', 100, 10, 80, 0, 0, ?, '2026-11-17T14:05:00Z')",
            (json.dumps([{"tokenType": "cache_read", "tokenCount": 80}]),),
        )
    assert parse_copilot_session(db, "cop-no-inp").usage_error is not None


def test_parse_opencode_v2_and_v1_sessions_forks_and_sidechains(tmp_path: Path) -> None:
    db = tmp_path / "opencode.db"
    proj = tmp_path / "proj"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, parent_id TEXT, fork_session_id TEXT, directory TEXT, time_created INTEGER);"
            "CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INTEGER, time_created INTEGER, data TEXT);"
            "CREATE TABLE session_part (message_id TEXT, session_id TEXT, ordinal INTEGER, type TEXT, time_created INTEGER, data TEXT);"
        )
        conn.execute(
            "INSERT INTO session_v2 VALUES ('oc-fork', NULL, 'oc-orig', ?, 2000)",
            (str(proj),),
        )
        # Pre-fork copied message (time_created < 2000) must be excluded.
        conn.execute(
            "INSERT INTO session_message VALUES ('m0', 'oc-fork', 'assistant', 1, 1000, ?)",
            (
                json.dumps(
                    {
                        "model": {"providerID": "openrouter", "id": "anthropic/claude-sonnet-4-5"},
                        "tokens": {"input": 999, "output": 999, "reasoning": 0, "cache": {"read": 0, "write": 0}},
                        "cost": 9.99,
                    }
                ),
            ),
        )
        conn.execute("INSERT INTO session_message VALUES ('m1', 'oc-fork', 'user', 2, 2100, '{}')")
        conn.execute(
            "INSERT INTO session_part VALUES ('m1', 'oc-fork', 0, 'text', 2100, ?)",
            (json.dumps({"text": "audit repo"}),),
        )
        conn.execute(
            "INSERT INTO session_part VALUES ('m1', 'oc-fork', 1, 'text', 2101, ?)",
            (json.dumps({"text": "hidden", "synthetic": True}),),
        )
        conn.execute(
            "INSERT INTO session_message VALUES ('m2', 'oc-fork', 'assistant', 3, 2200, ?)",
            (
                json.dumps(
                    {
                        "model": {"providerID": "openrouter", "id": "anthropic/claude-sonnet-4-5"},
                        "tokens": {"input": 100, "output": 40, "reasoning": 10, "cache": {"read": 50, "write": 20}},
                        "cost": 0.05,
                        "time": {"completed": 2500},
                    }
                ),
            ),
        )
        conn.execute(
            "INSERT INTO session_part VALUES ('m2', 'oc-fork', 0, 'text', 2200, ?)",
            (json.dumps({"text": "done"}),),
        )
        # Subagent child session
        conn.execute("INSERT INTO session_v2 VALUES ('oc-sub', 'oc-fork', NULL, ?, 2300)", (str(proj),))
        conn.execute(
            "INSERT INTO session_message VALUES ('ms1', 'oc-sub', 'assistant', 1, 2400, ?)",
            (
                json.dumps(
                    {
                        "summary": True,
                        "model": {"providerID": "anthropic", "id": "claude-sonnet-4-5"},
                        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
                        "cost": 0.01,
                    }
                ),
            ),
        )

    assert [sid for sid, _, _ in AGENT_ADAPTERS["opencode"].enumerate(db)] == ["oc-fork", "oc-sub"]
    parent_res = parse_opencode_session(db, "oc-fork")
    assert [ln.content for ln in parent_res.logs] == ["audit repo", "done"]
    assert parent_res.sidechain is False
    assert parent_res.usage is not None
    assert parent_res.usage.model == "openrouter/anthropic/claude-sonnet-4-5"
    assert parent_res.usage.input_tokens == 100
    assert parent_res.usage.output_tokens == 50
    assert parent_res.usage.reasoning_tokens == 10
    assert parent_res.usage.cached_tokens == 50
    assert parent_res.usage.cache_write_tokens == 20
    assert parent_res.usage.total_tokens == 220
    assert parent_res.usage.cost_usd == pytest.approx(0.05)

    sub_res = parse_opencode_session(db, "oc-sub")
    assert sub_res.sidechain is True
    assert sub_res.parent_session_id == "oc-fork"
    assert sub_res.logs == []
    assert sub_res.usage is not None
    assert sub_res.usage.total_tokens == 15

    # Legacy 1.x fallback
    v1_db = tmp_path / "opencode_v1.db"
    with closing(sqlite3.connect(v1_db)) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT);
            CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT);
            CREATE TABLE part (id TEXT PRIMARY KEY, session_id TEXT, message_id TEXT, time_created INTEGER, data TEXT);
            """
        )
        conn.execute("INSERT INTO session VALUES ('v1-1', ?)", (str(proj),))
        conn.execute(
            "INSERT INTO message VALUES ('m1', 'v1-1', 1000, ?)",
            (
                json.dumps(
                    {
                        "role": "assistant",
                        "modelID": "claude-sonnet-4-5",
                        "tokens": {"input": 10, "output": 5, "reasoning": 2},
                        "cost": 0.01,
                    }
                ),
            ),
        )
        conn.execute(
            "INSERT INTO part VALUES ('p1', 'v1-1', 'm1', 1000, ?)",
            (json.dumps({"type": "text", "text": "v1 reply"}),),
        )
    v1_res = parse_opencode_session(v1_db, "v1-1")
    assert [ln.content for ln in v1_res.logs] == ["v1 reply"]
    assert v1_res.usage is not None
    assert v1_res.usage.output_tokens == 7
    assert 0 < v1_res.usage.source_bytes < v1_db.stat().st_size

    # Partial assistant usage (one measured + one unmeasured assistant turn) drops session usage; blob time_created stays hashable.
    with closing(sqlite3.connect(v1_db)) as conn, conn:
        conn.execute("INSERT INTO message VALUES ('m2', 'v1-1', ?, ?)", (b"bad-ts", json.dumps({"role": "assistant"})))
    mixed_res = parse_opencode_session(v1_db, "v1-1")
    assert mixed_res.usage is None
    assert mixed_res.fingerprint != v1_res.fingerprint


def test_sqlite_parsers_empty_wal_mtime_invariance_and_missing_fork_time(tmp_path: Path) -> None:
    empty_db = tmp_path / "empty.db"
    with closing(sqlite3.connect(empty_db)) as conn, conn:
        conn.execute("CREATE TABLE placeholder(id TEXT)")
    assert AGENT_ADAPTERS["copilot"].enumerate(empty_db) == []
    assert AGENT_ADAPTERS["opencode"].enumerate(empty_db) == []

    # Untimed Copilot session fingerprint stays invariant when shared DB mtime changes (real WAL writes).
    cop_db = tmp_path / "copilot_wal.db"
    proj = tmp_path / "proj"
    with closing(sqlite3.connect(cop_db)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, turn_index INTEGER, "
            "user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, "
            "turn_index INTEGER, model TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, "
            "cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-nt', ?, NULL)", (str(proj),))
        conn.execute(
            "INSERT INTO turns (session_id, turn_index, user_message, assistant_response) VALUES ('cop-nt', 0, 'q', 'a')"
        )
        conn.execute(
            "INSERT INTO assistant_usage_events (session_id, turn_index, model, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, reasoning_tokens) VALUES ('cop-nt', 0, 'gpt-6-luna', 10, 5, 0, 0, 0)"
        )
        conn.commit()
    os.utime(cop_db, (1_700_000_000, 1_700_000_000))
    first = parse_copilot_session(cop_db, "cop-nt")
    os.utime(cop_db, (1_700_000_999, 1_700_000_999))
    second = parse_copilot_session(cop_db, "cop-nt")
    assert first.fingerprint == second.fingerprint
    assert first.usage is not None
    assert second.usage is not None
    assert first.usage.timestamp != second.usage.timestamp

    # Missing time_created column in forked OpenCode fails closed instead of accepting epoch 0.
    oc_db = tmp_path / "opencode_noforkts.db"
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, directory TEXT, fork_session_id TEXT);"
            "CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INTEGER, time_created INTEGER, data TEXT);"
            "CREATE TABLE session_part (id TEXT PRIMARY KEY, session_id TEXT, message_id TEXT, type TEXT, ordinal INTEGER, time_created INTEGER, data TEXT);"
        )
        conn.execute("INSERT INTO session_v2 VALUES ('oc-f', ?, 'orig')", (str(proj),))
    with pytest.raises(ValueError, match="requires valid time_created"):
        parse_opencode_session(oc_db, "oc-f")

    # Copilot Gemini/Grok cache-inclusive fallback subtracts cache tokens when token_details_json is absent,
    # while Anthropic Claude models stay uncached-native.
    fam_db = tmp_path / "copilot_families.db"
    with closing(sqlite3.connect(fam_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns (id INTEGER PRIMARY KEY, session_id TEXT, turn_index INT, user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events (id INTEGER PRIMARY KEY, session_id TEXT, model TEXT, "
            "input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT, "
            "token_details_json TEXT, created_at TEXT);"
        )
        for sid, model, raw_in, cache_r, cache_w in (
            ("cop-gem", "gemini-2.5-pro", 100, 70, 10),
            ("cop-grok", "x-ai/grok-4", 90, 50, 0),
            ("cop-cl", "claude-sonnet-4-5", 20, 80, 10),
            ("cop-bad-gem", "google/gemini-3-flash", 40, 50, 0),
        ):
            conn.execute("INSERT INTO sessions VALUES (?, ?, '2026-11-18T00:00:00Z')", (sid, str(proj)))
            conn.execute(
                "INSERT INTO assistant_usage_events (session_id, model, input_tokens, output_tokens, "
                "cache_read_tokens, cache_write_tokens, reasoning_tokens, token_details_json, created_at) "
                "VALUES (?, ?, ?, 15, ?, ?, 0, NULL, '2026-11-18T00:01:00Z')",
                (sid, model, raw_in, cache_r, cache_w),
            )
    gem = parse_copilot_session(fam_db, "cop-gem")
    grok = parse_copilot_session(fam_db, "cop-grok")
    cl = parse_copilot_session(fam_db, "cop-cl")
    bad_gem = parse_copilot_session(fam_db, "cop-bad-gem")
    assert gem.usage is not None
    assert gem.usage.input_tokens == 20
    assert grok.usage is not None
    assert grok.usage.input_tokens == 40
    assert cl.usage is not None
    assert cl.usage.input_tokens == 20
    assert bad_gem.usage is None
    assert bad_gem.usage_error is not None
    assert "smaller than cached" in str(bad_gem.usage_error)


def test_sqlite_session_stamps_handle_blobs_nan_collisions_and_schema_drift(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    # OpenCode: BLOB and non-finite REAL values stay hashable, and enumerate_stamped matches parse().session_stamp.
    oc_db = tmp_path / "oc_stamp.db"
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, directory TEXT, time_created ANY);"
            "CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INT, time_created ANY, data TEXT);"
            "CREATE TABLE session_part (id TEXT PRIMARY KEY, session_id TEXT, message_id TEXT, type TEXT, ordinal INT, time_created ANY, data TEXT);"
        )
        conn.execute("INSERT INTO session_v2 VALUES ('oc-edge', ?, ?)", (str(proj), float("inf")))
        conn.execute(
            "INSERT INTO session_message VALUES ('m1', 'oc-edge', 'assistant', 1, ?, ?)",
            (b"bad-ts", json.dumps({"role": "assistant"})),
        )
        conn.execute(
            "INSERT INTO session_part VALUES ('p1', 'oc-edge', 'm1', 'text', 0, ?, ?)",
            (float("inf"), json.dumps({"type": "text", "text": "aaaa"})),
        )
    oc_stamped = AGENT_ADAPTERS["opencode"].enumerate_stamped
    assert oc_stamped is not None
    [(sid, _, _, oc_stamp1)] = oc_stamped(oc_db)
    assert sid == "oc-edge"
    assert oc_stamp1 == parse_opencode_session(oc_db, "oc-edge").session_stamp
    # Equal-length JSON content edit invalidates OpenCode stamp.
    with closing(sqlite3.connect(oc_db)) as conn, conn:
        conn.execute(
            "UPDATE session_part SET data = ? WHERE id = 'p1'",
            (json.dumps({"type": "text", "text": "bbbb"}),),
        )
    [(_, _, _, oc_stamp2)] = oc_stamped(oc_db)
    assert oc_stamp2 != oc_stamp1
    assert oc_stamp2 == parse_opencode_session(oc_db, "oc-edge").session_stamp

    # Copilot: BLOB turn_index, NULL->0 token transitions, equal-length model/details edits, and turn_index edits.
    cop_db = tmp_path / "cop_stamp.db"
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns (id INTEGER PRIMARY KEY, session_id TEXT, turn_index ANY, user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events (id INTEGER PRIMARY KEY, session_id TEXT, turn_index INT, model TEXT, "
            "input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT, "
            "token_details_json TEXT, created_at TEXT);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-edge', ?, '2026-11-18T00:00:00Z')", (str(proj),))
        conn.execute("INSERT INTO turns VALUES (1, 'cop-edge', ?, 'hi', 'ok', '2026-11-18T00:00:00Z')", (b"blob-idx",))
        conn.execute(
            "INSERT INTO assistant_usage_events VALUES (1, 'cop-edge', 0, 'gpt-4o', NULL, NULL, 0, 0, 0, ?, '2026-11-18T00:01:00Z')",
            (json.dumps([{"tokenType": "input", "tokenCount": 100}]),),
        )
    cop_stamped = AGENT_ADAPTERS["copilot"].enumerate_stamped
    assert cop_stamped is not None
    [(_, _, _, s_null)] = cop_stamped(cop_db)
    assert s_null == parse_copilot_session(cop_db, "cop-edge").session_stamp
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute("UPDATE assistant_usage_events SET input_tokens = 0, output_tokens = 0 WHERE id = 1")
    [(_, _, _, s_zero)] = cop_stamped(cop_db)
    assert s_zero != s_null
    assert s_zero == parse_copilot_session(cop_db, "cop-edge").session_stamp
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute("UPDATE assistant_usage_events SET model = 'gpt-5o' WHERE id = 1")
    [(_, _, _, s_model)] = cop_stamped(cop_db)
    assert s_model != s_zero
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute(
            "UPDATE assistant_usage_events SET token_details_json = ? WHERE id = 1",
            (json.dumps([{"tokenType": "input", "tokenCount": 900}]),),
        )
    [(_, _, _, s_details)] = cop_stamped(cop_db)
    assert s_details != s_model
    with closing(sqlite3.connect(cop_db)) as conn, conn:
        conn.execute("UPDATE assistant_usage_events SET turn_index = 1 WHERE id = 1")
    [(_, _, _, s_tidx)] = cop_stamped(cop_db)
    assert s_tidx != s_details
    assert s_tidx == parse_copilot_session(cop_db, "cop-edge").session_stamp

    # Copilot usage schema drift falls back to empty stamps without aborting scan, preserving transcript parsing.
    drift_db = tmp_path / "cop_drift.db"
    with closing(sqlite3.connect(drift_db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, created_at TEXT);"
            "CREATE TABLE turns (id INTEGER PRIMARY KEY, session_id TEXT, turn_index INT, user_message TEXT, assistant_response TEXT, timestamp TEXT);"
            "CREATE TABLE assistant_usage_events (id INTEGER PRIMARY KEY, session_id TEXT, model TEXT, input_tokens INT);"
        )
        conn.execute("INSERT INTO sessions VALUES ('cop-d', ?, '2026-11-18T00:00:00Z')", (str(proj),))
        conn.execute("INSERT INTO turns VALUES (1, 'cop-d', 0, 'q', 'a', '2026-11-18T00:00:00Z')")
        conn.execute("INSERT INTO assistant_usage_events VALUES (1, 'cop-d', 'gpt-4o', 10)")
    assert cop_stamped(drift_db) == [("cop-d", str(proj), drift_db, "")]
    drift_parsed = parse_copilot_session(drift_db, "cop-d")
    assert [ln.content for ln in drift_parsed.logs] == ["q", "a"]
    assert drift_parsed.usage_error is not None
    assert drift_parsed.session_stamp == ""
