from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from fmind_dot.archive import parsers as parser_module
from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    ParsedSession,
    parse_agy_session,
    parse_claude_session,
    parse_copilot_session,
)
from fmind_dot.archive.store import SessionLog, fingerprint_bytes, marshal_session_logs
from fmind_dot.archive.usage import RETIRED_AGENTS, UsageRecord

COPILOT_SCHEMA = """
CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
CREATE TABLE turns(id INTEGER, session_id TEXT, turn_index INTEGER, user_message TEXT, assistant_response TEXT, timestamp TEXT);
CREATE TABLE assistant_usage_events(session_id TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);
"""


def _usage(parsed: ParsedSession) -> UsageRecord:
    if parsed.usage is None:
        raise parsed.usage_error or AssertionError("parser returned neither usage nor its error")
    return parsed.usage


def _jsonl(path, rows) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_claude_meta_user_turns_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "claude.jsonl"
    turns = [
        {"type": "user", "message": {"content": "normal prompt"}},
        {"type": "user", "isMeta": True, "message": {"content": "injected skill body"}},
        {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": "injected hook"}]}},
        {"type": "user", "isMeta": False, "message": {"content": "explicit normal prompt"}},
        {"type": "user", "isMeta": "true", "message": {"content": "non-boolean flag"}},
        {"type": "user", "isMeta": 1, "message": {"content": "numeric flag"}},
        {"type": "assistant", "isMeta": True, "message": {"content": [{"type": "text", "text": "answer"}]}},
    ]
    _jsonl(path, turns)

    parsed = parse_claude_session(path, "claude-id")
    rows = [json.loads(line) for line in marshal_session_logs(parsed.logs).splitlines()]

    assert [row["content"] for row in rows] == [
        "normal prompt",
        "injected skill body",
        "injected hook",
        "explicit normal prompt",
        "non-boolean flag",
        "numeric flag",
        "answer",
    ]
    assert [row.get("meta") for row in rows] == [None, True, True, None, None, None, None]
    assert [SessionLog.from_dict(row) for row in rows] == parsed.logs


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
                "truncated_fields": ["tool_calls"],
            },
            {"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "old", "is_truncated": True},
            {"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "cut", "truncated_fields": ["content"]},
        ],
    )
    parsed_agy = parse_agy_session(agy, "agy-id")
    assert [line.role for line in parsed_agy.logs] == ["user", "assistant"]
    assert parsed_agy.usage is not None
    assert parsed_agy.usage.total_tokens == 6
    assert parsed_agy.usage.measurement_kind == "estimated"
    assert parsed_agy.usage.model == "unknown"
    assert parsed_agy.usage.source_bytes == agy.stat().st_size

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
    assert parsed.usage is not None
    assert parsed.usage.total_tokens == 9
    assert parsed.usage.measurement_kind == "provider-reported"


@pytest.mark.parametrize(
    ("parser", "row"),
    [
        (
            parse_agy_session,
            {"created_at": "t1", "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "first"},
        ),
        (parse_claude_session, {"type": "user", "timestamp": "t1", "message": {"content": "first"}}),
    ],
    ids=["agy", "claude"],
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

    def fingerprint_snapshot(content: bytes) -> str:
        append_once()
        return fingerprint_bytes(content)

    # Appending after the snapshot read reproduces a transcript growing mid-parse.
    monkeypatch.setattr(parser_module, "fingerprint_bytes", fingerprint_snapshot)

    parsed = parser(transcript, "session-id")

    assert appended
    assert [log.content for log in parsed.logs] == ["first"]
    assert parsed.fingerprint == fingerprint_bytes(snapshot)
    assert parsed.fingerprint != fingerprint_bytes(transcript.read_bytes())


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
        _usage(parse_claude_session(transcript, "claude-id"))


@pytest.mark.parametrize("keys", [("message",), ("message", "usage")], ids=["claude-message", "claude-usage"])
@pytest.mark.parametrize(
    "value",
    [Ellipsis, None, {}, [], "private-invalid-container", True, 1],
    ids=["absent", "null", "empty-object", "list", "string", "boolean", "number"],
)
def test_usage_containers_reject_wrong_types_without_losing_transcripts(tmp_path: Path, keys, value) -> None:
    prompt = {"type": "user", "message": {"content": "retained prompt"}}
    row = {"type": "assistant", "message": {"usage": {}}}
    target = row
    for key in keys[:-1]:
        target = target[key]
    assert isinstance(target, dict)
    if value is Ellipsis:
        del target[keys[-1]]
    else:
        target[keys[-1]] = value
    transcript = tmp_path / "claude.jsonl"
    _jsonl(transcript, [prompt, row])

    parsed = parse_claude_session(transcript, "session-id")

    assert [log.content for log in parsed.logs] == ["retained prompt"]
    invalid = value is not Ellipsis and value is not None and not isinstance(value, dict)
    if invalid:
        assert parsed.usage is None
        assert isinstance(parsed.usage_error, ValueError)
        assert "must be an object" in str(parsed.usage_error)
        assert "private-" not in str(parsed.usage_error)
    else:
        assert parsed.usage_error is None
        assert parsed.usage is None


@pytest.mark.parametrize("with_image", [False, True], ids=["text-array", "text-and-image"])
def test_claude_user_text_blocks_preserve_prompts_without_tool_results(tmp_path: Path, with_image: bool) -> None:
    transcript = tmp_path / "claude.jsonl"
    content: list[dict[str, object]] = [{"type": "text", "text": "first"}, {"type": "text", "text": "second"}]
    if with_image:
        content.insert(1, {"type": "image", "source": {"type": "base64", "data": "private-image"}})
    _jsonl(
        transcript,
        [
            {"type": "user", "timestamp": "2026-09-01T12:00:00Z", "message": {"content": content}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "private-result"}]}},
        ],
    )

    parsed = parse_claude_session(transcript, "claude-id")

    assert [(record.role, record.content) for record in parsed.logs] == [("user", "first\nsecond")]
    assert parsed.malformed == 0
    assert parsed.skipped == 1
    assert parsed.usage_error is None


def test_copilot_database_parser_and_usage(tmp_path) -> None:
    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            COPILOT_SCHEMA
            + """INSERT INTO sessions VALUES('cp-id','/repo','2026-01-01T00:00:00Z');
            INSERT INTO turns VALUES(1,'cp-id',1,'ask','reply','2026-01-01T00:00:01Z');
            INSERT INTO assistant_usage_events VALUES('cp-id','gpt',10,5,2,3,1);"""
        )
    parsed = parse_copilot_session(database, "cp-id")
    assert [line.role for line in parsed.logs] == ["user", "assistant"]
    usage = _usage(parsed)
    assert (usage.model, usage.total_tokens, usage.reasoning_tokens) == ("gpt", 20, 1)


@pytest.mark.parametrize(
    "value", [None, "private-invalid-metric", b"private-invalid-metric"], ids=["null", "text", "blob"]
)
def test_copilot_usage_rejects_non_numeric_database_values(tmp_path: Path, value: object) -> None:
    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            COPILOT_SCHEMA
            + """INSERT INTO sessions VALUES('cp-id','/repo','2026-01-01T00:00:00Z');
            INSERT INTO turns VALUES(1,'cp-id',1,'ask','reply','2026-01-01T00:00:01Z');"""
        )
        connection.execute("INSERT INTO assistant_usage_events VALUES('cp-id','gpt',?,5,2,3,1)", (value,))
        connection.commit()

    parsed = parse_copilot_session(database, "cp-id")

    assert [log.content for log in parsed.logs] == ["ask", "reply"]
    if value is None:
        assert parsed.usage_error is None
        assert _usage(parsed).total_tokens == 10
    else:
        assert parsed.usage is None
        assert isinstance(parsed.usage_error, ValueError)
        assert "input_tokens" in str(parsed.usage_error)
        assert "private-invalid-metric" not in str(parsed.usage_error)


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

    assert list(AGENT_ADAPTERS) == ["agy", "claude", "copilot", "opencode"]
    assert AGENT_ADAPTERS["agy"].enumerate(agy_root) == [("agy-id", "", preferred_agy)]
    assert {candidate[0] for candidate in AGENT_ADAPTERS["claude"].enumerate(claude_root)} == {
        "claude-direct",
        "claude-fallback",
    }


def test_retired_agents_have_no_capture_adapter() -> None:
    # Retired harnesses keep their archived bundles selectable, so their names must never shadow an adapter.
    assert RETIRED_AGENTS == ("codex", "grok")
    assert set(RETIRED_AGENTS).isdisjoint(AGENT_ADAPTERS)


def test_copilot_discovery_is_read_only_and_filters_invalid_session_ids(tmp_path) -> None:
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        AGENT_ADAPTERS["copilot"].enumerate(missing)
    assert not missing.exists()

    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
            INSERT INTO sessions VALUES('valid-id',NULL,'2026-01-01T00:00:00Z');
            INSERT INTO sessions VALUES('invalid/id','/private','2026-01-01T00:00:00Z');"""
        )

    assert AGENT_ADAPTERS["copilot"].enumerate(database) == [("valid-id", "", database)]
    with pytest.raises(ValueError, match="invalid copilot session id"):
        parse_copilot_session(database, "invalid/id")


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
    agy_usage = _usage(parsed_agy)
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


def test_usage_extractors_cover_system_and_cost_contracts(tmp_path) -> None:
    agy = tmp_path / "agy.jsonl"
    _jsonl(
        agy,
        [
            {"created_at": "2026-01-01T00:00:00Z", "type": "RUN_COMMAND", "content": "abcd"},
            {"created_at": "2026-01-01T00:00:01Z", "type": "SYSTEM_MESSAGE", "content": "efgh"},
            {"created_at": "2026-01-01T00:00:02Z", "type": "OTHER", "content": "ignored"},
        ],
    )
    assert _usage(parse_agy_session(agy, "agy-id")).input_tokens == 2

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
            {
                "timestamp": "2026-01-01T00:00:01Z",
                "type": "assistant",
                "message": {"model": "m", "usage": {"input_tokens": 0}},
            },
            {
                "timestamp": "2026-01-01T00:00:02Z",
                "type": "assistant",
                "message": {"usage": {"input_tokens": 1.0, "cache_creation_input_tokens": 2}},
            },
        ],
    )
    claude_usage = _usage(parse_claude_session(claude, "claude-id"))
    assert (claude_usage.cwd, claude_usage.model, claude_usage.cost_usd) == ("/observed", "m", 0.5)
    assert (claude_usage.input_tokens, claude_usage.cache_write_tokens, claude_usage.turn_count) == (1, 2, 2)


# 2026-09-03T04:05:06Z: a source modification time far from both the transcript and the test clock.
_SOURCE_MTIME = 1_788_408_306


def test_undated_usage_takes_the_latest_transcript_timestamp_never_the_clock(tmp_path) -> None:
    claude = tmp_path / "claude.jsonl"
    _jsonl(
        claude,
        [
            {"type": "user", "timestamp": "2026-02-01T10:00:00Z", "message": {"content": "question"}},
            # An assistant block without its own timestamp cannot be dated as a request.
            {
                "type": "assistant",
                "message": {"id": "m", "content": [{"type": "text", "text": "a"}], "usage": {"input_tokens": 4}},
            },
            {"type": "user", "timestamp": "2026-02-01T10:05:00+00:00", "message": {"content": "later"}},
        ],
    )
    os.utime(claude, (_SOURCE_MTIME, _SOURCE_MTIME))

    first = _usage(parse_claude_session(claude, "claude-id"))
    again = _usage(parse_claude_session(claude, "claude-id"))

    assert first.timestamp == again.timestamp == "2026-02-01T10:05:00+00:00"
    assert (first.samples, first.input_tokens) == ([], 4)


def test_undated_usage_without_transcript_timestamps_takes_the_source_mtime(tmp_path) -> None:
    claude = tmp_path / "claude.jsonl"
    # An undated request keeps its tokens but never claims a request timestamp.
    _jsonl(
        claude,
        [
            {
                "type": "assistant",
                "message": {"id": "m", "content": [{"type": "text", "text": "a"}], "usage": {"input_tokens": 7}},
            }
        ],
    )
    os.utime(claude, (_SOURCE_MTIME, _SOURCE_MTIME))
    turn = _usage(parse_claude_session(claude, "claude-id"))
    assert (turn.timestamp, turn.samples, turn.input_tokens) == ("2026-09-03T04:05:06Z", [], 7)

    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            COPILOT_SCHEMA
            + """INSERT INTO sessions VALUES('cp-id','/repo',NULL);
            INSERT INTO turns VALUES(1,'cp-id',1,'ask','reply','2026-03-01T00:00:01Z');
            INSERT INTO assistant_usage_events VALUES('cp-id','gpt',10,5,0,0,0);"""
        )
    assert _usage(parse_copilot_session(database, "cp-id")).timestamp == "2026-03-01T00:00:01Z"


def test_copilot_usage_is_dated_by_the_latest_turn_of_a_resumed_session(tmp_path) -> None:
    database = tmp_path / "copilot.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            COPILOT_SCHEMA
            + """INSERT INTO sessions VALUES('cp-id','/repo','2026-03-01T00:00:00Z');
            INSERT INTO turns VALUES(1,'cp-id',1,'ask','reply','2026-03-01T00:00:01Z');
            INSERT INTO turns VALUES(2,'cp-id',2,'again','reply','2026-03-09T00:00:00Z');
            INSERT INTO assistant_usage_events VALUES('cp-id','gpt',10,5,0,0,0);"""
        )
    assert _usage(parse_copilot_session(database, "cp-id")).timestamp == "2026-03-09T00:00:00Z"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DELETE FROM turns")
        connection.commit()
    # Without dated turns, the session creation time still dates the usage.
    assert _usage(parse_copilot_session(database, "cp-id")).timestamp == "2026-03-01T00:00:00Z"


def test_undated_usage_without_its_source_stays_undated(tmp_path) -> None:
    # A source removed mid-sync must not crash parsing or invent a capture-time stamp.
    assert parser_module._undated_usage_timestamp([], tmp_path / "gone.jsonl") == ""  # noqa: SLF001


def _claude_answer(usage: dict, *, request: str = "r", text: str = "a") -> dict:
    return {
        "type": "assistant",
        "timestamp": "2026-09-01T10:00:00Z",
        "requestId": request,
        "message": {"id": "m", "model": "claude-opus-5-5", "content": [{"type": "text", "text": text}], "usage": usage},
    }


def test_claude_one_hour_cache_writes_are_a_subset_of_cache_writes(tmp_path: Path) -> None:
    transcript = tmp_path / "claude.jsonl"
    usage = {
        "input_tokens": 10,
        "output_tokens": 5,
        "cache_creation_input_tokens": 1000,
        "cache_creation": {"ephemeral_5m_input_tokens": 600, "ephemeral_1h_input_tokens": 400},
    }
    # Streaming blocks repeat one request's usage; it counts once.
    _jsonl(transcript, [_claude_answer(usage), _claude_answer(usage, text="b")])

    record = _usage(parse_claude_session(transcript, "claude-id"))

    assert (record.cache_write_tokens, record.cache_write_1h_tokens, record.total_tokens) == (1000, 400, 1015)
    assert [(sample["cache_write_tokens"], sample["cache_write_1h_tokens"]) for sample in record.samples] == [
        (1000, 400)
    ]
    assert record.to_dict()["cache_write_1h_tokens"] == 400


def test_claude_one_hour_writes_beyond_cache_writes_fail_extraction(tmp_path: Path) -> None:
    transcript = tmp_path / "claude.jsonl"
    usage = {"input_tokens": 1, "cache_creation_input_tokens": 10, "cache_creation": {"ephemeral_1h_input_tokens": 11}}
    _jsonl(transcript, [_claude_answer(usage)])

    parsed = parse_claude_session(transcript, "claude-id")

    assert parsed.usage is None
    assert "cache_write_1h_tokens" in str(parsed.usage_error)


@pytest.mark.parametrize("unknown", [True, False])
def test_claude_cost_with_an_unknown_model_price_is_unknown(tmp_path: Path, unknown: bool) -> None:
    transcript = tmp_path / "claude.jsonl"
    cost = {"type": "cost-state", "totalCostUSD": 1.5, "hasUnknownModelCost": unknown}
    _jsonl(transcript, [_claude_answer({"input_tokens": 1, "output_tokens": 1}), cost])

    record = _usage(parse_claude_session(transcript, "claude-id")).to_dict()

    # A partial bill is never reported as the session cost.
    assert (record["cost_known"], record["cost_usd"]) == ((False, None) if unknown else (True, 1.5))


def test_claude_rejects_a_non_boolean_unknown_cost_flag(tmp_path: Path) -> None:
    transcript = tmp_path / "claude.jsonl"
    cost = {"type": "cost-state", "totalCostUSD": 1.5, "hasUnknownModelCost": "private-flag"}
    _jsonl(transcript, [_claude_answer({"input_tokens": 1}), cost])

    parsed = parse_claude_session(transcript, "claude-id")

    assert parsed.usage is None
    assert str(parsed.usage_error) == "usage record field 'hasUnknownModelCost' must be a boolean"


def test_claude_subagents_are_sidechains_and_workflow_journals_are_not_sessions(tmp_path: Path) -> None:
    project = tmp_path / "claude/-work-project"
    parent = project / "parent-id.jsonl"
    subagent = project / "parent-id/subagents/agent-a1.jsonl"
    workflow = project / "parent-id/subagents/workflows/wf_1"
    for path in (subagent, workflow / "agent-b2.jsonl"):
        path.parent.mkdir(parents=True, exist_ok=True)
        _jsonl(path, [{"type": "user", "isSidechain": True, "sessionId": "parent-id", "message": {"content": "task"}}])
    # Older transcripts embed sidechain records under their own session: still a top-level session.
    _jsonl(parent, [{"type": "user", "isSidechain": True, "sessionId": "parent-id", "message": {"content": "own"}}])
    _jsonl(workflow / "journal.jsonl", [{"type": "launched"}, {"type": "started", "agentId": "b2", "key": "k"}])

    sessions = sorted(candidate[0] for candidate in AGENT_ADAPTERS["claude"].enumerate(tmp_path / "claude"))
    top = parse_claude_session(parent, "parent-id")
    child = parse_claude_session(subagent, "agent-a1")

    assert sessions == ["agent-a1", "agent-b2", "parent-id"]
    assert (top.sidechain, top.parent_session_id) == (False, "")
    assert (child.sidechain, child.parent_session_id) == (True, "parent-id")


# Python 3.14 measures JSON recursion against the C stack: about a million levels exceed it.
_DEEP_ARRAY = "[" * 1_000_000 + "]" * 1_000_000


@pytest.mark.parametrize("parser", [parse_agy_session, parse_claude_session])
def test_deeply_nested_json_lines_are_malformed_records(tmp_path: Path, parser) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(_DEEP_ARRAY + "\n" + json.dumps({"type": "unrelated"}) + "\n", encoding="utf-8")

    parsed = parser(transcript, "session-id")

    assert parsed.malformed == 1


def test_unexpandable_home_paths_are_malformed_input() -> None:
    with pytest.raises(ValueError, match="cannot expand a home directory"):
        parser_module.resolve_cwd("~dot-test-no-such-user/project")


def _agy_summaries(path: Path, rows: list[tuple[object, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE conversation_summaries (conversation_id text, workspace_uris text NOT NULL)")
        connection.executemany("INSERT INTO conversation_summaries VALUES (?, ?)", rows)
        connection.commit()


def test_agy_sessions_take_their_workspace_from_the_summaries_database(tmp_path: Path) -> None:
    root = tmp_path / "antigravity-cli/brain"
    rows: list[tuple[object, object]] = [
        ("project", json.dumps(["file:///work/my%20project"])),
        ("multiple", json.dumps(["https://example.com/repo", "file://localhost/work/second", "file:///work/third"])),
        ("empty", ""),
        ("remote", json.dumps(["file://host/share", "vscode-remote://ssh/work", "file:relative"])),
        ("malformed", "["),
        ("scalar", json.dumps("file:///work/scalar")),
        ("missing-transcript", json.dumps(["file:///work/none"])),
        ("encoded-nul", json.dumps(["file:///work/a%00b"])),
    ]
    _agy_summaries(tmp_path / "antigravity-cli/conversation_summaries.db", rows)
    for session_id, _ in rows:
        if session_id != "missing-transcript":
            _jsonl(_agy_transcript(root, str(session_id)), [])
    _jsonl(_agy_transcript(root, "unlisted"), [])

    candidates = {session_id: cwd for session_id, cwd, _ in AGENT_ADAPTERS["agy"].enumerate(root)}

    assert candidates == {
        "project": "/work/my project",
        "multiple": "/work/second",
        "empty": "",
        "remote": "",
        "malformed": "",
        "scalar": "",
        "encoded-nul": "",
        "unlisted": "",
    }


def test_agy_without_summaries_database_keeps_sessions_without_workspace(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _jsonl(_agy_transcript(root, "session"), [])
    assert [(session_id, cwd) for session_id, cwd, _ in AGENT_ADAPTERS["agy"].enumerate(root)] == [("session", "")]


def test_agy_unreadable_summaries_database_fails_the_scan(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _jsonl(_agy_transcript(root, "session"), [])
    with closing(sqlite3.connect(tmp_path / "conversation_summaries.db")) as connection:
        connection.execute("CREATE TABLE other (value text)")
    with pytest.raises(sqlite3.Error):
        AGENT_ADAPTERS["agy"].enumerate(root)


def test_agy_workspace_marks_records_usage_and_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "transcript.jsonl"
    _jsonl(
        path, [{"created_at": "2026-01-01T00:00:00Z", "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hi"}]
    )
    without = parse_agy_session(path, "agy-id")
    located = parse_agy_session(path, "agy-id", "/work/project")
    assert without.fingerprint == fingerprint_bytes(path.read_bytes())
    assert located.fingerprint != without.fingerprint
    assert [record.cwd for record in located.logs] == ["/work/project"]
    assert _usage(located).cwd == "/work/project"


def _agy_transcript(root: Path, session_id: str) -> Path:
    path = root / session_id / ".system_generated/logs/transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
