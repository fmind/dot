from __future__ import annotations

import json
import sqlite3
from contextlib import closing

import pytest

from fmind_dot import agent_parsers as parser_module
from fmind_dot.agent_parsers import (
    agent_adapters,
    enumerate_sessions,
    enumerate_usage_sessions,
    extract_agy_usage,
    extract_claude_usage,
    extract_codex_usage,
    extract_copilot_usage,
    extract_grok_usage,
    find_transcript,
    parse_agy_session,
    parse_claude_session,
    parse_codex_session,
    parse_copilot_session,
    parse_grok_session,
)
from fmind_dot.session_store import fingerprint_bytes, fingerprint_file


def _jsonl(path, rows) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_file_transcript_parsers_and_usage(tmp_path) -> None:
    agy = tmp_path / "agy.jsonl"
    _jsonl(
        agy,
        [
            {"created_at": "2026-01-01T00:00:00Z", "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hello"},
            {
                "created_at": "2026-01-01T00:00:01Z",
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "world",
                "thinking": "why",
            },
            {"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "old", "is_truncated": True},
        ],
    )
    assert [line.role for line in parse_agy_session(agy, "agy-id").logs] == ["user", "assistant"]
    assert extract_agy_usage(agy, "agy-id").total_tokens == 5

    claude = tmp_path / "claude.jsonl"
    _jsonl(
        claude,
        [
            {
                "type": "user",
                "timestamp": "2026-01-01T00:00:02Z",
                "cwd": "/work",
                "message": {"content": "prompt"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-01-01T00:00:03Z",
                "message": {
                    "model": "sonnet",
                    "content": [{"type": "text", "text": "answer"}],
                    "usage": {"input_tokens": 2, "output_tokens": 3, "cache_read_input_tokens": 4},
                },
            },
        ],
    )
    parsed = parse_claude_session(claude, "claude-id")
    assert [line.content for line in parsed.logs] == ["prompt", "answer"]
    assert all(line.model == "sonnet" for line in parsed.logs)
    assert extract_claude_usage(claude, "claude-id").total_tokens == 9

    codex = tmp_path / "rollout.jsonl"
    _jsonl(
        codex,
        [
            {
                "timestamp": "2026-01-01T00:00:04Z",
                "type": "turn_context",
                "payload": {"cwd": "/repo", "model": "gpt"},
            },
            {
                "timestamp": "2026-01-01T00:00:05Z",
                "type": "response_item",
                "payload": {"role": "user", "content": [{"text": "ask"}]},
            },
            {
                "timestamp": "2026-01-01T00:00:06Z",
                "type": "response_item",
                "payload": {"role": "assistant", "content": "reply"},
            },
            {
                "timestamp": "2026-01-01T00:00:07Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "cached_input_tokens": 2,
                            "reasoning_output_tokens": 1,
                            "total_tokens": 17,
                        }
                    },
                },
            },
        ],
    )
    parsed = parse_codex_session(codex, "codex-id")
    assert [(line.role, line.model, line.cwd) for line in parsed.logs] == [
        ("user", "gpt", "/repo"),
        ("assistant", "gpt", "/repo"),
    ]
    usage = extract_codex_usage(codex, "codex-id")
    assert (usage.total_tokens, usage.turn_count, usage.reasoning_tokens) == (17, 1, 1)


@pytest.mark.parametrize(
    ("parser", "row"),
    [
        (
            parse_agy_session,
            {"created_at": "t1", "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "first"},
        ),
        (parse_claude_session, {"type": "user", "timestamp": "t1", "message": {"content": "first"}}),
        (
            parse_codex_session,
            {"timestamp": "t1", "type": "response_item", "payload": {"role": "user", "content": "first"}},
        ),
        (
            parse_grok_session,
            {
                "timestamp": 1,
                "params": {
                    "_meta": {"promptId": "p"},
                    "update": {"sessionUpdate": "user_message_chunk", "content": {"text": "first"}},
                },
            },
        ),
    ],
    ids=["agy", "claude", "codex", "grok"],
)
def test_jsonl_parser_binds_logs_and_fingerprint_to_one_snapshot(
    tmp_path, monkeypatch: pytest.MonkeyPatch, parser, row
) -> None:
    transcript = tmp_path / "session.jsonl"
    _jsonl(transcript, [row])
    snapshot = transcript.read_bytes()
    appended = False

    def append_once() -> None:
        nonlocal appended
        if appended:
            return
        appended = True
        with transcript.open("a", encoding="utf-8") as stream:
            stream.write("{}\n")

    def fingerprint_live(path) -> str:
        append_once()
        return fingerprint_file(path)

    def fingerprint_snapshot(content: bytes) -> str:
        append_once()
        return fingerprint_bytes(content)

    # The live-path patch reproduces the old post-parse hash race; the byte
    # patch places the same append after the replacement snapshot read.
    monkeypatch.setattr(parser_module, "fingerprint_file", fingerprint_live, raising=False)
    monkeypatch.setattr(parser_module, "fingerprint_bytes", fingerprint_snapshot)

    parsed = parser(transcript, "session-id")

    assert appended
    assert [log.content for log in parsed.logs] == ["first"]
    assert parsed.fingerprint == fingerprint_bytes(snapshot)
    assert parsed.fingerprint != fingerprint_file(transcript)


@pytest.mark.parametrize(
    "rows",
    [
        [
            {"type": "assistant", "message": {"usage": {"input_tokens": -1}}},
            {"type": "assistant", "message": {"usage": {"input_tokens": 2}}},
        ],
        [
            {"type": "cost-state", "totalCostUSD": float("inf")},
            {"type": "cost-state", "totalCostUSD": 0.25},
        ],
    ],
    ids=["negative-tokens", "infinite-cost"],
)
def test_claude_usage_rejects_invalid_numeric_metrics(tmp_path, rows) -> None:
    transcript = tmp_path / "claude.jsonl"
    _jsonl(transcript, rows)

    with pytest.raises(ValueError, match=r"input_tokens|cost_usd"):
        extract_claude_usage(transcript, "claude-id")


def test_grok_stream_groups_chunks_and_reports_observable_usage(tmp_path) -> None:
    updates = tmp_path / "updates.jsonl"
    _jsonl(
        updates,
        [
            {
                "timestamp": 1,
                "params": {
                    "_meta": {"promptId": "p"},
                    "update": {
                        "sessionUpdate": "user_message_chunk",
                        "_meta": {"modelId": "grok-4"},
                        "content": {"text": "he"},
                    },
                },
            },
            {
                "timestamp": 1,
                "params": {
                    "_meta": {"promptId": "p"},
                    "update": {"sessionUpdate": "user_message_chunk", "content": {"text": "llo"}},
                },
            },
            {
                "timestamp": 2,
                "params": {
                    "_meta": {"promptId": "p"},
                    "update": {"sessionUpdate": "agent_message_chunk", "content": {"text": "answer"}},
                },
            },
        ],
    )
    parsed = parse_grok_session(updates, "grok-id", "/work")
    assert [(line.role, line.content, line.model) for line in parsed.logs] == [
        ("user", "hello", "grok-4"),
        ("assistant", "answer", "grok-4"),
    ]
    (tmp_path / "signals.json").write_text(
        '{"primaryModelId":"grok-4","contextTokensUsed":21,"turnCount":3}', encoding="utf-8"
    )
    usage = extract_grok_usage(tmp_path, "grok-id")
    assert (usage.input_tokens, usage.output_tokens, usage.total_tokens, usage.turn_count) == (21, 0, 21, 3)


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), 10**100], ids=["nan", "infinity", "out-of-range"])
def test_grok_parser_ignores_unrepresentable_timestamps(tmp_path, timestamp: int | float) -> None:
    updates = tmp_path / "updates.jsonl"
    _jsonl(
        updates,
        [
            {
                "timestamp": timestamp,
                "params": {
                    "_meta": {"promptId": "p"},
                    "update": {"sessionUpdate": "user_message_chunk", "content": {"text": "hello"}},
                },
            }
        ],
    )

    parsed = parse_grok_session(updates, "grok-id")

    assert [(log.ts, log.content) for log in parsed.logs] == [("", "hello")]


def test_copilot_database_parser_and_usage(tmp_path) -> None:
    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
            CREATE TABLE turns(id INTEGER, session_id TEXT, turn_index INTEGER, user_message TEXT, assistant_response TEXT, timestamp TEXT);
            CREATE TABLE assistant_usage_events(session_id TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);
            INSERT INTO sessions VALUES('cp-id','/repo','2026-01-01T00:00:00Z');
            INSERT INTO turns VALUES(1,'cp-id',1,'ask','reply','2026-01-01T00:00:01Z');
            INSERT INTO assistant_usage_events VALUES('cp-id','gpt',10,5,2,3,1);"""
        )
    parsed = parse_copilot_session(database, "cp-id")
    assert [line.role for line in parsed.logs] == ["user", "assistant"]
    usage = extract_copilot_usage(database, "cp-id")
    assert (usage.model, usage.total_tokens, usage.reasoning_tokens) == ("gpt", 20, 1)


def test_public_discovery_contracts_cover_each_verified_store(tmp_path) -> None:
    agy_root = tmp_path / "agy"
    agy_logs = agy_root / "agy-id/.system_generated/logs"
    agy_logs.mkdir(parents=True)
    (agy_logs / "transcript.jsonl").touch()
    preferred_agy = agy_logs / "transcript_full.jsonl"
    preferred_agy.touch()
    (agy_root / "ignore.txt").touch()

    claude_root = tmp_path / "claude"
    direct_claude = claude_root / "-work-project/claude-direct.jsonl"
    direct_claude.parent.mkdir(parents=True)
    direct_claude.touch()
    fallback_claude = claude_root / "fallback/claude-fallback.jsonl"
    fallback_claude.parent.mkdir()
    fallback_claude.touch()
    (fallback_claude.parent / "memory.jsonl").touch()

    codex_root = tmp_path / "codex"
    codex_root.mkdir()
    codex = codex_root / "rollout-2026-01-01T00-00-00-codex-id.jsonl"
    codex.touch()
    (codex_root / "unrecognized.jsonl").touch()

    grok_root = tmp_path / "grok"
    grok = grok_root / "%2Fwork%2Fgrok/grok-id/updates.jsonl"
    grok.parent.mkdir(parents=True)
    grok.touch()
    signals_only = grok_root / "%2Fwork%2Fgrok/signals-id"
    signals_only.mkdir()

    assert [adapter.name for adapter in agent_adapters(verified_only=True)] == [
        "agy",
        "claude",
        "codex",
        "grok",
        "copilot",
    ]
    assert find_transcript(agy_root, "agy", "agy-id") == preferred_agy
    assert find_transcript(claude_root, "claude", "claude-direct", "/work/project") == direct_claude
    assert find_transcript(claude_root, "claude", "claude-fallback") == fallback_claude
    assert find_transcript(codex_root, "codex", "codex-id") == codex
    assert find_transcript(grok_root, "grok", "grok-id", "/work/grok") == grok
    assert enumerate_sessions(agy_root, "agy") == [("agy-id", "", preferred_agy)]
    assert {candidate[0] for candidate in enumerate_sessions(claude_root, "claude")} == {
        "claude-direct",
        "claude-fallback",
    }
    assert enumerate_sessions(codex_root, "codex") == [("codex-id", "", codex)]
    assert enumerate_sessions(grok_root, "grok") == [("grok-id", "/work/grok", grok)]
    assert {candidate[0] for candidate in enumerate_usage_sessions(grok_root, "grok")} == {
        "grok-id",
        "signals-id",
    }

    with pytest.raises(FileNotFoundError, match="missing"):
        find_transcript(grok_root, "grok", "missing")
    with pytest.raises(ValueError, match="no verified session parser"):
        enumerate_sessions(tmp_path, "unknown")


def test_copilot_discovery_is_read_only_and_filters_invalid_session_ids(tmp_path) -> None:
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        enumerate_sessions(missing, "copilot")
    assert not missing.exists()

    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
            INSERT INTO sessions VALUES('valid-id',NULL,'2026-01-01T00:00:00Z');
            INSERT INTO sessions VALUES('invalid/id','/private','2026-01-01T00:00:00Z');"""
        )

    assert enumerate_sessions(database, "copilot") == [("valid-id", "", database)]
    for operation in (parse_copilot_session, extract_copilot_usage):
        with pytest.raises(ValueError, match="invalid copilot session id"):
            operation(database, "invalid/id")


def test_parsers_account_for_malformed_and_unsupported_records(tmp_path) -> None:
    agy = tmp_path / "agy.jsonl"
    agy.write_text(
        "\n".join(
            (
                '{"created_at":"2026-01-01T00:00:00Z","source":"USER_EXPLICIT","type":"USER_INPUT","content":"ask"}',
                '{"source":"MODEL","type":"PLANNER_RESPONSE","content":"old","is_truncated":true}',
                '{"source":"MODEL","type":"OTHER","content":"ignored"}',
                "[]",
                "{",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    parsed_agy = parse_agy_session(agy, "agy-id")
    assert (len(parsed_agy.logs), parsed_agy.malformed, parsed_agy.skipped) == (1, 2, 2)
    agy_usage = extract_agy_usage(agy, "agy-id")
    assert (agy_usage.turn_count, agy_usage.input_tokens, agy_usage.output_tokens) == (1, 1, 1)

    claude = tmp_path / "claude.jsonl"
    claude.write_text(
        "\n".join(
            (
                '{"type":"user","timestamp":"t","message":{"content":"ask"}}',
                '{"type":"assistant","message":{"content":[{"type":"tool","text":"ignored"},null]}}',
                '{"type":"assistant","message":"invalid"}',
                "false",
                "{",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    parsed_claude = parse_claude_session(claude, "claude-id")
    assert (len(parsed_claude.logs), parsed_claude.malformed, parsed_claude.skipped) == (1, 2, 2)


def test_codex_accepts_supported_legacy_record_shapes_and_rejects_bad_metrics(tmp_path) -> None:
    transcript = tmp_path / "rollout.jsonl"
    transcript.write_text(
        "\n".join(
            (
                '{"created_at":"t1","role":"user","content":["one",{"content":"two"},{"text":"three"},null],"cwd":"/one","model":"m"}',
                '{"timestamp":"t2","payload":{"role":"assistant","message":"answer","cwd":"/two","model":"m2"}}',
                '{"ts":"t3","type":"user_message","text":"question"}',
                '{"type":"agent_message","message":"reply"}',
                '{"type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":-1}}}}',
                "[]",
                "{",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    parsed = parse_codex_session(transcript, "codex-id")
    assert [(log.role, log.content) for log in parsed.logs] == [
        ("user", "one\ntwo\nthree"),
        ("assistant", "answer"),
        ("user", "question"),
        ("assistant", "reply"),
    ]
    assert (parsed.malformed, parsed.skipped) == (2, 1)
    assert [(log.cwd, log.model) for log in parsed.logs[:2]] == [("/one", "m"), ("/two", "m2")]
    with pytest.raises(ValueError, match="input_tokens"):
        extract_codex_usage(transcript, "codex-id")


def test_usage_extractors_cover_system_cost_and_empty_signal_contracts(tmp_path) -> None:
    agy = tmp_path / "agy.jsonl"
    _jsonl(
        agy,
        [
            {"created_at": "2026-01-01T00:00:00Z", "type": "RUN_COMMAND", "content": "abcd"},
            {"created_at": "2026-01-01T00:00:01Z", "type": "SYSTEM_MESSAGE", "content": "efgh"},
            {"created_at": "2026-01-01T00:00:02Z", "type": "OTHER", "content": "ignored"},
        ],
    )
    assert extract_agy_usage(agy, "agy-id").input_tokens == 2

    claude = tmp_path / "claude.jsonl"
    _jsonl(
        claude,
        [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "cwd": "/observed",
                "type": "cost-state",
                "totalCostUSD": 0.5,
            },
            {"timestamp": "2026-01-01T00:00:01Z", "type": "assistant", "message": {"model": "m"}},
            {
                "timestamp": "2026-01-01T00:00:02Z",
                "type": "assistant",
                "message": {"usage": {"input_tokens": 1.0, "cache_creation_input_tokens": 2}},
            },
        ],
    )
    claude_usage = extract_claude_usage(claude, "claude-id")
    assert (claude_usage.cwd, claude_usage.model, claude_usage.cost_usd) == ("/observed", "m", 0.5)
    assert (claude_usage.input_tokens, claude_usage.cache_write_tokens, claude_usage.turn_count) == (1, 2, 2)

    grok_dir = tmp_path / "grok"
    grok_dir.mkdir()
    (grok_dir / "signals.json").write_text("{", encoding="utf-8")
    assert extract_grok_usage(grok_dir, "grok-id").total_tokens == 0
    (grok_dir / "signals.json").write_text("[]", encoding="utf-8")
    assert extract_grok_usage(grok_dir, "grok-id").total_tokens == 0
