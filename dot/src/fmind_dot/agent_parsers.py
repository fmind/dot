"""Verified discovery, transcript parsing, and usage extraction for agent stores."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fmind_dot.session_store import SessionLog, fingerprint_bytes, fingerprint_json, is_valid_session_id
from fmind_dot.usage import UsageRecord

AGY_TRANSCRIPT_NAMES = ("transcript_full.jsonl", "transcript.jsonl")
GROK_TRANSCRIPT_NAME = "updates.jsonl"


@dataclass
class ParsedSession:
    logs: list[SessionLog]
    fingerprint: str
    source_type: str
    malformed: int = 0
    skipped: int = 0


SessionParser = Callable[[Path, str, str], ParsedSession]
UsageParser = Callable[[Path, str, str], UsageRecord]


@dataclass(frozen=True)
class AgentAdapter:
    name: str
    label: str
    alias: str
    source_type: str
    database: bool
    parser: SessionParser | None
    usage_parser: UsageParser | None
    verified: bool = True


def resolve_cwd(value: str) -> str:
    if not value:
        return ""
    return str(Path(value).expanduser().resolve(strict=False))


def _decode_jsonl(content: bytes) -> Iterator[tuple[dict[str, Any] | None, bool]]:
    for line in content.decode().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            yield None, True
            continue
        if not isinstance(value, dict):
            yield None, True
            continue
        yield value, False


def _jsonl_snapshot(path: Path) -> tuple[Iterator[tuple[dict[str, Any] | None, bool]], str]:
    content = path.read_bytes()
    return _decode_jsonl(content), fingerprint_bytes(content)


def _iter_jsonl(path: Path) -> Iterator[tuple[dict[str, Any] | None, bool]]:
    records, _fingerprint = _jsonl_snapshot(path)
    yield from records


def _finalize_models(logs: list[SessionLog]) -> None:
    active = ""
    for log in logs:
        if log.model:
            active = log.model
        elif active:
            log.model = active
    active = ""
    for log in reversed(logs):
        if log.model:
            active = log.model
        elif active:
            log.model = active


def _usage_token_count(value: object, field: str) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if value < 0 or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer())):
        raise ValueError(f"usage record field {field!r} must be a non-negative integer")
    return int(value)


def _usage_cost(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        cost = float(value)
    except OverflowError as error:
        raise ValueError("usage record field 'cost_usd' must be a non-negative finite number") from error
    if cost < 0 or not math.isfinite(cost):
        raise ValueError("usage record field 'cost_usd' must be a non-negative finite number")
    return cost


def parse_agy_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    records, fingerprint = _jsonl_snapshot(path)
    for raw, bad in records:
        if bad:
            malformed += 1
            continue
        if raw is None:
            continue
        decoded += 1
        if raw.get("is_truncated") is True:
            continue
        source, kind, content = raw.get("source"), raw.get("type"), raw.get("content")
        role = ""
        if source == "USER_EXPLICIT" and kind == "USER_INPUT":
            role = "user"
        elif source == "MODEL" and kind == "PLANNER_RESPONSE":
            role = "assistant"
        if role and isinstance(content, str) and content.strip():
            logs.append(SessionLog(str(raw.get("created_at", "")), "agy", session_id, role, content, resolve_cwd(cwd)))
    return ParsedSession(logs, fingerprint, "antigravity-jsonl", malformed, decoded - len(logs))


def extract_agy_usage(path: Path, session_id: str, cwd: str = "") -> UsageRecord:
    record = UsageRecord(harness="agy", agent="agy", session_id=session_id, model="gemini", cwd=resolve_cwd(cwd))
    input_bytes = output_bytes = 0
    for raw, bad in _iter_jsonl(path):
        if bad:
            continue
        if raw is None:
            continue
        timestamp = raw.get("created_at")
        if isinstance(timestamp, str) and timestamp:
            record.timestamp = timestamp
        source, kind, content = raw.get("source"), raw.get("type"), raw.get("content")
        text = content if isinstance(content, str) else ""
        if source == "USER_EXPLICIT" and kind == "USER_INPUT":
            record.turn_count += 1
            input_bytes += len(text.encode())
        elif source == "MODEL" and kind == "PLANNER_RESPONSE":
            output_bytes += len(text.encode())
            thinking = raw.get("thinking")
            if isinstance(thinking, str):
                output_bytes += len(thinking.encode())
        elif kind in {"RUN_COMMAND", "SYSTEM_MESSAGE"}:
            input_bytes += len(text.encode())
    record.input_tokens = (input_bytes + 3) // 4
    record.output_tokens = (output_bytes + 3) // 4
    return record.finalize()


def claude_project_directory(cwd: str) -> str:
    return "-" + cwd.replace("/", "-").replace(".", "-").lstrip("-")


def claude_session_id(path: Path) -> str:
    return "" if path.name == "memory.jsonl" else path.stem


def _observe_claude_usage(record: UsageRecord, raw: dict[str, Any]) -> None:
    timestamp = raw.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        record.timestamp = timestamp
    line_cwd = raw.get("cwd")
    if isinstance(line_cwd, str) and line_cwd and not record.cwd:
        record.cwd = resolve_cwd(line_cwd)
    kind = raw.get("type")
    if kind == "cost-state":
        cost = _usage_cost(raw.get("totalCostUSD"))
        if cost is not None:
            record.cost_usd = cost
    if kind != "assistant":
        return
    record.turn_count += 1
    message = raw.get("message")
    if not isinstance(message, dict):
        return
    model = message.get("model")
    if isinstance(model, str) and model:
        record.model = model
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return
    for source, target in (
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("cache_read_input_tokens", "cached_tokens"),
        ("cache_creation_input_tokens", "cache_write_tokens"),
    ):
        count = _usage_token_count(usage.get(source), target)
        if count is not None:
            setattr(record, target, getattr(record, target) + count)


def parse_claude_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    records, fingerprint = _jsonl_snapshot(path)
    for raw, bad in records:
        if bad:
            malformed += 1
            continue
        if raw is None:
            continue
        decoded += 1
        kind = raw.get("type")
        message = raw.get("message")
        if kind not in {"user", "assistant"} or not isinstance(message, dict):
            continue
        content = ""
        if kind == "user" and isinstance(message.get("content"), str):
            content = message["content"]
        elif kind == "assistant" and isinstance(message.get("content"), list):
            texts = [
                part["text"]
                for part in message["content"]
                if isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
                and part["text"]
            ]
            content = "\n".join(texts)
        if not content.strip():
            continue
        line_cwd = raw.get("cwd") if isinstance(raw.get("cwd"), str) else cwd
        model = message.get("model") if isinstance(message.get("model"), str) else ""
        logs.append(
            SessionLog(
                str(raw.get("timestamp", "")),
                "claude",
                session_id,
                kind,
                content,
                resolve_cwd(line_cwd or cwd),
                model,
            )
        )
    _finalize_models(logs)
    return ParsedSession(logs, fingerprint, "claude-jsonl", malformed, decoded - len(logs))


def extract_claude_usage(path: Path, session_id: str, cwd: str = "") -> UsageRecord:
    record = UsageRecord(harness="claude", agent="claude", session_id=session_id, cwd=resolve_cwd(cwd))
    for raw, bad in _iter_jsonl(path):
        if not bad and raw is not None:
            _observe_claude_usage(record, raw)
    # Claude's cumulative cost contract always recomputes the token total.
    record.total_tokens = record.input_tokens + record.output_tokens + record.cached_tokens + record.cache_write_tokens
    return record.finalize()


def codex_session_id(path: Path) -> str:
    name = path.stem
    if not name.startswith("rollout-"):
        return ""
    parts = name.split("-")
    return "-".join(parts[6:]) if len(parts) >= 7 else ""


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _codex_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    texts: list[str] = []
    for part in value:
        if isinstance(part, str):
            texts.append(part)
        elif isinstance(part, dict):
            text = part.get("text") or part.get("content")
            if isinstance(text, str) and text:
                texts.append(text)
    return "\n".join(texts)


def _codex_role(raw: dict[str, Any]) -> str:
    if isinstance(raw.get("role"), str) and raw["role"]:
        return raw["role"]
    payload = _mapping(raw.get("payload"))
    if isinstance(payload.get("role"), str) and payload["role"]:
        return payload["role"]
    kind = raw.get("type")
    if kind in {"user", "user_message"}:
        return "user"
    return "assistant" if kind in {"assistant", "assistant_message", "agent_message"} else ""


def _codex_content(raw: dict[str, Any]) -> str:
    content = _codex_text(raw.get("content"))
    if content:
        return content
    payload = _mapping(raw.get("payload"))
    content = _codex_text(payload.get("content"))
    if content:
        return content
    for value in (payload.get("message"), payload.get("text"), raw.get("message"), raw.get("text")):
        if isinstance(value, str) and value:
            return value
    return ""


def _codex_field(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and value:
        return value
    value = _mapping(raw.get("payload")).get(key)
    return value if isinstance(value, str) else ""


def _observe_codex_usage(record: UsageRecord, raw: dict[str, Any]) -> None:
    timestamp = raw.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        record.timestamp = timestamp
    payload = _mapping(raw.get("payload"))
    kind = raw.get("type")
    if kind in {"turn_context", "session_meta"}:
        model = payload.get("model")
        if kind == "turn_context" and isinstance(model, str) and model:
            record.model = model
        cwd = payload.get("cwd")
        if isinstance(cwd, str) and cwd and not record.cwd:
            record.cwd = resolve_cwd(cwd)
    elif kind == "response_item" and payload.get("role") == "assistant":
        record.turn_count += 1
    elif kind == "event_msg" and payload.get("type") == "token_count":
        total = _mapping(_mapping(payload.get("info")).get("total_token_usage"))
        for source, target in (
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("cached_input_tokens", "cached_tokens"),
            ("cache_write_input_tokens", "cache_write_tokens"),
            ("reasoning_output_tokens", "reasoning_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            count = _usage_token_count(total.get(source), target)
            if count is not None:
                setattr(record, target, count)


def parse_codex_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    active_model = ""
    active_cwd = resolve_cwd(cwd)
    records, fingerprint = _jsonl_snapshot(path)
    for raw, bad in records:
        if bad:
            malformed += 1
            continue
        if raw is None:
            continue
        decoded += 1
        if model := _codex_field(raw, "model"):
            active_model = model
        if line_cwd := _codex_field(raw, "cwd"):
            active_cwd = resolve_cwd(line_cwd)
        role = _codex_role(raw)
        content = _codex_content(raw)
        if role not in {"user", "assistant"} or not content.strip():
            continue
        timestamp = next(
            (raw[key] for key in ("timestamp", "created_at", "ts") if isinstance(raw.get(key), str) and raw[key]),
            "",
        )
        logs.append(
            SessionLog(
                timestamp,
                "codex",
                session_id,
                role,
                content,
                resolve_cwd(_codex_field(raw, "cwd")) or active_cwd,
                _codex_field(raw, "model") or active_model,
            )
        )
    _finalize_models(logs)
    return ParsedSession(logs, fingerprint, "codex-jsonl", malformed, decoded - len(logs))


def extract_codex_usage(path: Path, session_id: str, cwd: str = "") -> UsageRecord:
    record = UsageRecord(harness="codex", agent="codex", session_id=session_id, cwd=resolve_cwd(cwd))
    for raw, bad in _iter_jsonl(path):
        if not bad and raw is not None:
            _observe_codex_usage(record, raw)
    return record.finalize()


def grok_session_directory(cwd: str) -> str:
    return quote(cwd, safe="")


def grok_cwd_from_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return ""
    return unquote(relative.parts[0]) if len(relative.parts) >= 2 else ""


def _grok_timestamp(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return ""
    try:
        timestamp = datetime.fromtimestamp(int(value), UTC)
    except OverflowError, OSError, ValueError:
        return ""
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_grok_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    active_model = ""
    current_role = current_prompt = current_ts = current_model = ""
    parts: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_prompt, current_ts, current_model, parts
        content = "".join(parts)
        if current_role and content.strip():
            logs.append(
                SessionLog(
                    current_ts,
                    "grok",
                    session_id,
                    current_role,
                    content,
                    resolve_cwd(cwd),
                    current_model,
                )
            )
        current_role = current_prompt = current_ts = current_model = ""
        parts = []

    roles = {"user_message_chunk": "user", "agent_message_chunk": "assistant"}
    records, fingerprint = _jsonl_snapshot(path)
    for raw, bad in records:
        if bad:
            malformed += 1
            continue
        if raw is None:
            continue
        decoded += 1
        params = _mapping(raw.get("params"))
        update = _mapping(params.get("update"))
        model = _mapping(update.get("_meta")).get("modelId")
        if isinstance(model, str) and model:
            active_model = model
        role = roles.get(update.get("sessionUpdate"))
        text = _mapping(update.get("content")).get("text")
        if role is None or not isinstance(text, str) or not text:
            continue
        prompt = _mapping(params.get("_meta")).get("promptId")
        prompt_id = prompt if isinstance(prompt, str) else ""
        if current_role != role or current_prompt != prompt_id:
            flush()
            current_role = role
            current_prompt = prompt_id
            current_ts = _grok_timestamp(raw.get("timestamp"))
            current_model = active_model
        parts.append(text)
    flush()
    _finalize_models(logs)
    return ParsedSession(logs, fingerprint, "grok-jsonl", malformed, decoded - len(logs))


def extract_grok_usage(session_dir: Path, session_id: str, cwd: str = "") -> UsageRecord:
    record = UsageRecord(harness="grok", agent="grok", session_id=session_id, cwd=resolve_cwd(cwd))
    signals = session_dir / "signals.json"
    if signals.exists():
        try:
            value = json.loads(signals.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            value = {}
        if isinstance(value, dict):
            model = value.get("primaryModelId")
            if isinstance(model, str):
                record.model = model
            tokens = _usage_token_count(value.get("contextTokensUsed"), "input_tokens")
            if tokens is not None:
                record.input_tokens = tokens
            turns = _usage_token_count(value.get("turnCount"), "turn_count")
            if turns is not None:
                record.turn_count = turns
    return record.finalize()


def _extract_grok_usage_from_transcript(path: Path, session_id: str, cwd: str = "") -> UsageRecord:
    return extract_grok_usage(path.parent, session_id, cwd)


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _copilot_rows(connection: sqlite3.Connection, session_id: str | None = None) -> list[dict[str, Any]]:
    columns = """SELECT t.session_id, t.turn_index, t.user_message, t.assistant_response,
                         t.timestamp, s.cwd
                  FROM turns t JOIN sessions s ON t.session_id = s.id"""
    if session_id is None:
        cursor = connection.execute(columns + " ORDER BY t.session_id, t.turn_index, t.id")
    else:
        cursor = connection.execute(
            columns + " WHERE t.session_id = ? ORDER BY t.session_id, t.turn_index, t.id",
            (session_id,),
        )
    return [
        {
            "session_id": row["session_id"],
            "user_message": row["user_message"] or "",
            "assistant_response": row["assistant_response"] or "",
            "timestamp": row["timestamp"] or "",
            "cwd": row["cwd"] or "",
            "turn_index": row["turn_index"],
        }
        for row in cursor
    ]


def parse_copilot_rows(session_id: str, rows: list[dict[str, Any]], fallback_cwd: str = "") -> list[SessionLog]:
    logs: list[SessionLog] = []
    for row in rows:
        cwd = resolve_cwd(str(row.get("cwd") or fallback_cwd))
        timestamp = str(row.get("timestamp") or "")
        user = row.get("user_message")
        if isinstance(user, str) and user.strip():
            logs.append(SessionLog(timestamp, "copilot", session_id, "user", user, cwd))
        assistant = row.get("assistant_response")
        if isinstance(assistant, str) and assistant.strip():
            logs.append(SessionLog(timestamp, "copilot", session_id, "assistant", assistant, cwd))
    return logs


def parse_copilot_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid copilot session id {session_id!r}")
    with closing(_connect_read_only(path)) as connection:
        rows = _copilot_rows(connection, session_id)
    return ParsedSession(parse_copilot_rows(session_id, rows, cwd), fingerprint_json(rows), "copilot-db")


def extract_copilot_usage(path: Path, session_id: str, cwd: str = "") -> UsageRecord:
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid copilot session id {session_id!r}")
    with closing(_connect_read_only(path)) as connection:
        rows = connection.execute(
            """SELECT model, input_tokens, output_tokens, cache_read_tokens,
                      cache_write_tokens, reasoning_tokens
               FROM assistant_usage_events WHERE session_id = ?""",
            (session_id,),
        ).fetchall()
        session = connection.execute("SELECT cwd, created_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    record = UsageRecord(harness="copilot", agent="copilot", session_id=session_id, cwd=resolve_cwd(cwd))
    if session is not None:
        if not record.cwd:
            record.cwd = resolve_cwd(session["cwd"] or "")
        record.timestamp = session["created_at"] or ""
    for row in rows:
        if not record.model and row[0]:
            record.model = str(row[0])
        record.input_tokens += _usage_token_count(row[1], "input_tokens") or 0
        record.output_tokens += _usage_token_count(row[2], "output_tokens") or 0
        record.cached_tokens += _usage_token_count(row[3], "cached_tokens") or 0
        record.cache_write_tokens += _usage_token_count(row[4], "cache_write_tokens") or 0
        record.reasoning_tokens += _usage_token_count(row[5], "reasoning_tokens") or 0
        record.turn_count += 1
    record.total_tokens = record.input_tokens + record.output_tokens + record.cached_tokens + record.cache_write_tokens
    return record.finalize()


AGENT_ADAPTERS: dict[str, AgentAdapter] = {
    "agy": AgentAdapter("agy", "agy", "a", "antigravity-jsonl", False, parse_agy_session, extract_agy_usage),
    "claude": AgentAdapter("claude", "Claude", "c", "claude-jsonl", False, parse_claude_session, extract_claude_usage),
    "codex": AgentAdapter("codex", "Codex", "x", "codex-jsonl", False, parse_codex_session, extract_codex_usage),
    "grok": AgentAdapter(
        "grok", "Grok", "g", "grok-jsonl", False, parse_grok_session, _extract_grok_usage_from_transcript
    ),
    "copilot": AgentAdapter(
        "copilot", "Copilot", "p", "copilot-db", True, parse_copilot_session, extract_copilot_usage
    ),
}


def agent_adapters(*, verified_only: bool = False) -> list[AgentAdapter]:
    return [adapter for adapter in AGENT_ADAPTERS.values() if adapter.verified or not verified_only]


def find_transcript(root: Path, agent: str, session_id: str, cwd: str = "") -> Path:
    if agent == "agy":
        for name in AGY_TRANSCRIPT_NAMES:
            candidate = root / session_id / ".system_generated" / "logs" / name
            if candidate.is_file():
                return candidate
    elif agent == "claude":
        candidate = root / claude_project_directory(cwd) / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
        for path in root.rglob(f"{session_id}.jsonl"):
            if path.name != "memory.jsonl":
                return path
    elif agent == "codex":
        for path in root.rglob("*.jsonl"):
            if codex_session_id(path) == session_id:
                return path
    elif agent == "grok":
        if cwd:
            candidate = root / grok_session_directory(cwd) / session_id / GROK_TRANSCRIPT_NAME
            if candidate.is_file():
                return candidate
        for path in root.rglob(GROK_TRANSCRIPT_NAME):
            if path.parent.name == session_id:
                return path
    raise FileNotFoundError(f"session file not found for {agent} session {session_id}")


def enumerate_sessions(root: Path, agent: str) -> list[tuple[str, str, Path]]:
    """Return session id, CWD, and source path for one verified adapter."""
    candidates: list[tuple[str, str, Path]] = []
    if agent == "agy":
        for directory in sorted(root.iterdir()):
            if not directory.is_dir():
                continue
            for name in AGY_TRANSCRIPT_NAMES:
                path = directory / ".system_generated" / "logs" / name
                if path.is_file():
                    candidates.append((directory.name, "", path))
                    break
    elif agent == "claude":
        for path in sorted(root.rglob("*.jsonl")):
            session_id = claude_session_id(path)
            if is_valid_session_id(session_id):
                candidates.append((session_id, "", path))
    elif agent == "codex":
        for path in sorted(root.rglob("*.jsonl")):
            session_id = codex_session_id(path)
            if is_valid_session_id(session_id):
                candidates.append((session_id, "", path))
    elif agent == "grok":
        for path in sorted(root.rglob(GROK_TRANSCRIPT_NAME)):
            session_id = path.parent.name
            if is_valid_session_id(session_id):
                candidates.append((session_id, grok_cwd_from_path(root, path), path))
    elif agent == "copilot":
        with closing(_connect_read_only(root)) as connection:
            candidates.extend(
                (row[0], row[1] or "", root)
                for row in connection.execute("SELECT id, cwd FROM sessions")  # nosemgrep: formatted-sql-query
                if is_valid_session_id(row[0])
            )
    else:
        raise ValueError(f"agent {agent!r} has no verified session parser")
    return candidates


def enumerate_usage_sessions(root: Path, agent: str) -> list[tuple[str, str, Path]]:
    """Return candidates using each source's usage-specific discovery rules."""
    if agent != "grok":
        return enumerate_sessions(root, agent)
    candidates: list[tuple[str, str, Path]] = []
    for cwd_directory in sorted(root.iterdir()):
        if not cwd_directory.is_dir():
            continue
        candidates.extend(
            (session_directory.name, "", session_directory / GROK_TRANSCRIPT_NAME)
            for session_directory in sorted(cwd_directory.iterdir())
            if session_directory.is_dir() and is_valid_session_id(session_directory.name)
        )
    return candidates


__all__ = [
    "AGENT_ADAPTERS",
    "AGY_TRANSCRIPT_NAMES",
    "GROK_TRANSCRIPT_NAME",
    "AgentAdapter",
    "ParsedSession",
    "agent_adapters",
    "claude_project_directory",
    "claude_session_id",
    "codex_session_id",
    "enumerate_sessions",
    "enumerate_usage_sessions",
    "extract_agy_usage",
    "extract_claude_usage",
    "extract_codex_usage",
    "extract_copilot_usage",
    "extract_grok_usage",
    "find_transcript",
    "grok_cwd_from_path",
    "grok_session_directory",
    "parse_agy_session",
    "parse_claude_session",
    "parse_codex_session",
    "parse_copilot_rows",
    "parse_copilot_session",
    "parse_grok_session",
    "resolve_cwd",
]
