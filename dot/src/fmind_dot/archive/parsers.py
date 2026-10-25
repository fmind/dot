"""Verified discovery, transcript parsing, and usage extraction for agent stores."""

from __future__ import annotations

import json
import math
import sqlite3
import stat
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from fmind_dot.archive.store import (
    SessionLog,
    fingerprint_bytes,
    fingerprint_json,
    is_valid_session_id,
    parse_utc_instant,
    propagate_models,
)
from fmind_dot.archive.usage import UsageRecord

AGY_TRANSCRIPT_NAMES = ("transcript_full.jsonl", "transcript.jsonl")
# Antigravity transcripts carry no CWD; the CLI records each conversation's workspace URIs here,
# beside the conversation directories root.
AGY_SUMMARIES_NAME = "conversation_summaries.db"
_AGY_SUMMARIES_LIMIT = 100_000


@dataclass
class ParsedSession:
    logs: list[SessionLog]
    fingerprint: str
    source_type: str
    malformed: int = 0
    skipped: int = 0
    usage: UsageRecord | None = None
    usage_error: Exception | None = None
    # A subagent transcript belongs to its parent's session; the parent can be unknown.
    sidechain: bool = False
    parent_session_id: str = ""


SessionParser = Callable[[Path, str, str], ParsedSession]
# Session id, CWD known before parsing (empty when the transcript holds it), and source path.
SessionCandidate = tuple[str, str, Path]
SessionEnumerator = Callable[[Path], list[SessionCandidate]]


@dataclass(frozen=True)
class AgentAdapter:
    """Everything dot knows about one agent's native store; adding an agent starts here."""

    name: str
    label: str
    database: bool
    parser: SessionParser
    enumerate: SessionEnumerator
    # Desktop notification title; hosts brand themselves differently from their CLI name.
    notify_label: str = ""
    # The CWD comes from metadata outside the transcript file, so it joins the source signature.
    external_cwd: bool = False


def resolve_cwd(value: str) -> str:
    if not value:
        return ""
    try:
        path = Path(value).expanduser()
    except RuntimeError:
        # `~user` names an account without a home directory: malformed input, not a crash.
        raise ValueError("cannot expand a home directory in the project path") from None
    return str(path.resolve(strict=False))


def _json_document(content: str | bytes, label: str) -> object:
    """Decode one JSON document; nesting deeper than the interpreter stack is malformed input."""
    try:
        return json.loads(content)
    except RecursionError:
        raise ValueError(f"{label} is nested too deeply") from None


def _decode_jsonl(content: bytes) -> Iterator[dict[str, Any] | None]:
    """Yield each JSON object record, or None for a malformed one."""
    # JSONL records end at LF, not at Unicode separators embedded in JSON strings.
    # Decode one LF-delimited record at a time: large transcript snapshots can be
    # nearly a gigabyte, and splitting a decoded copy multiplies peak memory.
    for raw_line in BytesIO(content):
        try:
            line = raw_line.decode()
            if not line.strip():
                continue
            value = json.loads(line)
        except UnicodeDecodeError, json.JSONDecodeError, RecursionError:
            # An undecodable record is malformed; it must not cost the rest of the session.
            value = None
        yield value if isinstance(value, dict) else None


def _jsonl_snapshot(path: Path) -> tuple[Iterator[dict[str, Any] | None], str, int]:
    content = path.read_bytes()
    return _decode_jsonl(content), fingerprint_bytes(content), len(content)


def _usage_token_count(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"usage record field {field!r} must be a non-negative integer")
    if value < 0 or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer())):
        raise ValueError(f"usage record field {field!r} must be a non-negative integer")
    return int(value)


def _apply_counters(
    record: UsageRecord,
    counters: Mapping[str, object],
    fields: tuple[tuple[str, str], ...],
    *,
    accumulate: bool = False,
) -> None:
    """Copy (or add) the present provider counters; an input, output, or total counter proves a measurement."""
    for source, target in fields:
        count = _usage_token_count(counters.get(source), target)
        if count is not None:
            setattr(record, target, getattr(record, target) + count if accumulate else count)
            if target in {"input_tokens", "output_tokens", "total_tokens"}:
                record.measurement_kind = "provider-reported"


def _usage_mapping(value: object, field: str, *, optional: bool = True) -> dict[str, Any]:
    if value is None and optional:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"usage record field {field!r} must be an object")
    return value


def _usage_cost(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("usage record field 'cost_usd' must be a non-negative finite number")
    try:
        cost = float(value)
    except OverflowError as error:
        raise ValueError("usage record field 'cost_usd' must be a non-negative finite number") from error
    if cost < 0 or not math.isfinite(cost):
        raise ValueError("usage record field 'cost_usd' must be a non-negative finite number")
    return cost


def _undated_usage_timestamp(logs: list[SessionLog], *sources: Path) -> str:
    """Date usage without its own timestamp by the latest transcript record, else the newest source mtime.

    The clock is never evidence: a capture-time stamp would move usage between periods and change on recapture.
    """
    dated = [(instant, log.ts) for log in logs if (instant := parse_utc_instant(log.ts)) is not None]
    if dated:
        return max(dated, key=lambda item: item[0])[1]
    mtimes: list[float] = []
    for source in sources:
        try:
            mtimes.append(source.stat().st_mtime)
        except FileNotFoundError:
            continue  # A source removed mid-sync leaves the others as evidence.
    if not mtimes:
        return ""
    return datetime.fromtimestamp(max(mtimes), UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finalize_parsed_usage(
    record: UsageRecord, error: Exception | None, fallback_timestamp: str
) -> tuple[UsageRecord | None, Exception | None]:
    if error is not None:
        return None, error
    try:
        return record.finalize(fallback_timestamp=fallback_timestamp), None
    except ValueError as usage_error:
        # Transcript archival stays useful when a provider emits bad metrics:
        # ingestion publishes the transcript without usage, then reports this error.
        return None, usage_error


_AGY_ROLES = {("USER_EXPLICIT", "USER_INPUT"): "user", ("MODEL", "PLANNER_RESPONSE"): "assistant"}


def parse_agy_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    usage = UsageRecord(
        harness="agy",
        agent="agy",
        session_id=session_id,
        # The transcript has no verified model identity; agy can serve several providers.
        model="unknown",
        cwd=resolve_cwd(cwd),
        measurement_kind="estimated",
    )
    input_bytes = output_bytes = 0
    records, fingerprint, source_bytes = _jsonl_snapshot(path)
    for raw in records:
        if raw is None:
            malformed += 1
            continue
        decoded += 1
        timestamp = raw.get("created_at")
        if isinstance(timestamp, str) and timestamp:
            usage.timestamp = timestamp
        source, kind, content = raw.get("source"), raw.get("type"), raw.get("content")
        text = content if isinstance(content, str) else ""
        role = _AGY_ROLES.get((source, kind), "")
        if role == "user":
            usage.turn_count += 1
            input_bytes += len(text.encode())
        elif role == "assistant":
            output_bytes += len(text.encode())
            thinking = raw.get("thinking")
            if isinstance(thinking, str):
                output_bytes += len(thinking.encode())
        elif kind in {"RUN_COMMAND", "SYSTEM_MESSAGE"}:
            input_bytes += len(text.encode())
        truncated = raw.get("truncated_fields")
        if raw.get("is_truncated") is True or (isinstance(truncated, list) and "content" in truncated):
            continue
        if role and isinstance(content, str) and content.strip():
            logs.append(SessionLog(str(raw.get("created_at", "")), "agy", session_id, role, content, usage.cwd))
    usage.input_tokens = (input_bytes + 3) // 4
    usage.output_tokens = (output_bytes + 3) // 4
    usage.source_bytes = source_bytes
    parsed_usage, usage_error = _finalize_parsed_usage(usage, None, _undated_usage_timestamp(logs, path))
    if usage.cwd:
        # The workspace comes from the summaries database, not the transcript bytes.
        fingerprint = fingerprint_json({"transcript": fingerprint, "cwd": usage.cwd})
    return ParsedSession(
        logs,
        fingerprint,
        "antigravity-jsonl",
        malformed,
        decoded - len(logs),
        parsed_usage,
        usage_error,
    )


def claude_session_id(path: Path) -> str:
    # Memory files and subagent workflow journals (`journal.jsonl`) are not conversations.
    return "" if path.name in {"memory.jsonl", "journal.jsonl"} else path.stem


def claude_parent_session_id(path: Path) -> str:
    """Return the parent session id of a `<parent>/subagents/agent-*.jsonl` sidechain path."""
    parent = path.parent.parent.name if path.parent.name == "subagents" else ""
    return parent if is_valid_session_id(parent) else ""


_CLAUDE_TOKEN_FIELDS = (
    ("input_tokens", "input_tokens"),
    ("output_tokens", "output_tokens"),
    ("cache_read_input_tokens", "cached_tokens"),
    ("cache_creation_input_tokens", "cache_write_tokens"),
)


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
        unknown = raw.get("hasUnknownModelCost", False)
        if not isinstance(unknown, bool):
            raise ValueError("usage record field 'hasUnknownModelCost' must be a boolean")
        if unknown:
            # A model without a known price makes the total a partial bill: the cost is unknown.
            record.cost_usd, record.cost_known = 0.0, False
        elif cost is not None:
            record.cost_usd = cost
            record.cost_known = True
    if kind != "assistant":
        return
    record.turn_count += 1
    message = _usage_mapping(raw.get("message"), "message")
    model = message.get("model")
    if isinstance(model, str) and model:
        record.observe_model(model)
    if model == "<synthetic>":
        # Claude's local error/interrupt responses do not make a billed request.
        record.measurement_kind = "provider-reported"
    usage = _usage_mapping(message.get("usage"), "usage")
    _apply_counters(record, usage, _CLAUDE_TOKEN_FIELDS, accumulate=True)
    # 1-hour cache writes are a subset of cache_creation_input_tokens with their own price.
    creation = _usage_mapping(usage.get("cache_creation"), "cache_creation")
    count = _usage_token_count(creation.get("ephemeral_1h_input_tokens"), "cache_write_1h_tokens")
    if count is not None:
        record.cache_write_1h_tokens += count


def parse_claude_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    usage_error: Exception | None = None
    usage = UsageRecord(
        harness="claude",
        agent="claude",
        session_id=session_id,
        cwd=resolve_cwd(cwd),
    )
    messages: dict[tuple[str, str], UsageRecord] = {}
    timed = True
    parent = ""
    records, fingerprint, source_bytes = _jsonl_snapshot(path)
    # Only validates an undated sample: untimed sessions drop their samples below.
    sample_fallback = _undated_usage_timestamp([], path)
    for raw in records:
        if raw is None:
            malformed += 1
            continue
        decoded += 1
        declared = raw.get("sessionId")
        if (
            not parent
            and raw.get("isSidechain") is True
            and isinstance(declared, str)
            and declared != session_id
            and is_valid_session_id(declared)
        ):
            # A subagent transcript is a sidechain of the session that launched it.
            parent = declared
        try:
            if raw.get("type") == "assistant":
                message = _mapping(raw.get("message"))
                sample = UsageRecord(harness="claude", session_id=session_id)
                _observe_claude_usage(sample, raw)
                timed = timed and bool(sample.timestamp)
                sample.finalize(fallback_timestamp=sample_fallback)
                # Streaming content blocks share a message ID and repeat its usage.
                identity = message.get("id")
                key = (
                    (str(raw.get("requestId", "")), identity)
                    if isinstance(identity, str) and identity
                    else ("row", str(decoded))
                )
                previous = messages.get(key)
                if previous:
                    sample.measurement_kind = sample.measurement_kind or previous.measurement_kind
                    # Partial blocks can report increasing output; preserve the high water.
                    for name in (
                        "input_tokens",
                        "output_tokens",
                        "cached_tokens",
                        "cache_write_tokens",
                        "cache_write_1h_tokens",
                    ):
                        setattr(sample, name, max(getattr(previous, name), getattr(sample, name)))
                    sample.total_tokens = (
                        sample.input_tokens + sample.output_tokens + sample.cached_tokens + sample.cache_write_tokens
                    )
                messages[key] = sample
            else:
                _observe_claude_usage(usage, raw)
        except ValueError as error:
            usage_error = error
        kind = raw.get("type")
        message = raw.get("message")
        if kind not in {"user", "assistant"} or not isinstance(message, dict):
            continue
        content = ""
        if kind == "user" and isinstance(message.get("content"), str):
            content = message["content"]
        elif isinstance(message.get("content"), list):
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
                meta=kind == "user" and raw.get("isMeta") is True,
            )
        )
    propagate_models(logs)
    measured = bool(messages) and all(sample.measurement_kind for sample in messages.values())
    if measured:
        usage.measurement_kind = "provider-reported"
        usage.set_samples(list(messages.values()), timed=timed)
        usage.timestamp = max(sample.timestamp for sample in messages.values()) if timed else ""
        if not usage.cwd:
            usage.cwd = next((sample.cwd for sample in messages.values() if sample.cwd), "")
    usage.source_bytes = source_bytes
    if not measured and not usage.cost_known:
        # An absent measurement is unknown, not a zero-token provider request.
        parsed_usage = None
    else:
        parsed_usage, usage_error = _finalize_parsed_usage(usage, usage_error, _undated_usage_timestamp(logs, path))
    return ParsedSession(
        logs,
        fingerprint,
        "claude-jsonl",
        malformed,
        decoded - len(logs),
        parsed_usage,
        usage_error,
        sidechain=bool(parent),
        parent_session_id=parent,
    )


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _copilot_turns(
    connection: sqlite3.Connection, session_id: str, fallback_cwd: str
) -> tuple[list[dict[str, Any]], list[SessionLog]]:
    """Return the session's turn rows (fingerprint evidence) and their transcript records."""
    rows: list[dict[str, Any]] = []
    logs: list[SessionLog] = []
    for row in connection.execute(
        """SELECT t.session_id, t.turn_index, t.user_message, t.assistant_response, t.timestamp, s.cwd
           FROM turns t JOIN sessions s ON t.session_id = s.id
           WHERE t.session_id = ? ORDER BY t.turn_index, t.id""",
        (session_id,),
    ):
        turn = {
            "session_id": row["session_id"],
            "user_message": row["user_message"] or "",
            "assistant_response": row["assistant_response"] or "",
            "timestamp": row["timestamp"] or "",
            "cwd": row["cwd"] or "",
            "turn_index": row["turn_index"],
        }
        rows.append(turn)
        cwd = resolve_cwd(str(turn["cwd"] or fallback_cwd))
        timestamp = str(turn["timestamp"])
        for role, text in (("user", turn["user_message"]), ("assistant", turn["assistant_response"])):
            if isinstance(text, str) and text.strip():
                logs.append(SessionLog(timestamp, "copilot", session_id, role, text, cwd))
    return rows, logs


def parse_copilot_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid copilot session id {session_id!r}")
    with closing(_connect_read_only(path)) as connection:
        connection.execute("BEGIN")
        rows, logs = _copilot_turns(connection, session_id, cwd)
        try:
            usage = _extract_copilot_usage(
                connection, session_id, cwd, _undated_usage_timestamp(logs), _undated_usage_timestamp([], path)
            )
            usage_error = None
        except (sqlite3.Error, ValueError) as error:
            usage = None
            usage_error = error
    if usage is not None:
        usage.source_bytes = path.stat().st_size
    return ParsedSession(
        logs,
        fingerprint_json(
            {
                "turns": rows,
                "usage": {key: value for key, value in usage.to_dict().items() if key != "source_bytes"}
                if usage is not None
                else None,
            }
        ),
        "copilot-db",
        usage=usage,
        usage_error=usage_error,
    )


_COPILOT_TOKEN_FIELDS = (
    ("input_tokens", "input_tokens"),
    ("output_tokens", "output_tokens"),
    ("cache_read_tokens", "cached_tokens"),
    ("cache_write_tokens", "cache_write_tokens"),
    ("reasoning_tokens", "reasoning_tokens"),
)


def _extract_copilot_usage(
    connection: sqlite3.Connection, session_id: str, cwd: str, latest_turn: str, fallback_timestamp: str
) -> UsageRecord | None:
    rows = connection.execute(
        """SELECT model, input_tokens, output_tokens, cache_read_tokens,
                  cache_write_tokens, reasoning_tokens
           FROM assistant_usage_events WHERE session_id = ?""",
        (session_id,),
    ).fetchall()
    session = connection.execute("SELECT cwd, created_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    record = UsageRecord(
        harness="copilot",
        agent="copilot",
        session_id=session_id,
        cwd=resolve_cwd(cwd),
        measurement_kind="provider-reported",
        # Usage is per session, so date it by its last activity; a resumed session belongs to the period of use.
        timestamp=latest_turn,
    )
    if session is not None:
        if not record.cwd:
            record.cwd = resolve_cwd(session["cwd"] or "")
        record.timestamp = record.timestamp or session["created_at"] or ""
    for row in rows:
        if row["model"]:
            record.observe_model(str(row["model"]))
        _apply_counters(record, dict(row), _COPILOT_TOKEN_FIELDS, accumulate=True)
        record.turn_count += 1
    if not rows or any(row["input_tokens"] is None and row["output_tokens"] is None for row in rows):
        return None
    record.total_tokens = record.input_tokens + record.output_tokens + record.cached_tokens + record.cache_write_tokens
    return record.finalize(fallback_timestamp=fallback_timestamp)


_OPENCODE_TOKEN_FIELDS = (
    ("input", "input_tokens"),
    ("output", "output_tokens"),
    ("reasoning", "reasoning_tokens"),
)


def _opencode_time(value: object) -> str:
    if type(value) is not int or not 0 <= value <= 253402300799000:
        raise ValueError("invalid OpenCode message time")
    return datetime.fromtimestamp(value / 1000, UTC).isoformat()


def _opencode_request(message: dict[str, Any], created: int, session_id: str, cwd: str) -> UsageRecord:
    """Measure one assistant message: OpenCode records each model step as its own message."""
    tokens = _usage_mapping(message.get("tokens"), "tokens", optional=False)
    sample = UsageRecord(harness="opencode", session_id=session_id, cwd=cwd, turn_count=1)
    _apply_counters(sample, tokens, _OPENCODE_TOKEN_FIELDS)
    cache = _usage_mapping(tokens.get("cache"), "cache")
    _apply_counters(sample, cache, (("read", "cached_tokens"), ("write", "cache_write_tokens")))
    # OpenCode reports reasoning beside output; the archive treats it as a subset of output.
    sample.output_tokens += sample.reasoning_tokens
    sample.total_tokens = sample.input_tokens + sample.output_tokens + sample.cached_tokens + sample.cache_write_tokens
    model = message.get("modelID")
    sample.model = model if isinstance(model, str) else ""
    completed = _mapping(message.get("time")).get("completed")
    sample.timestamp = _opencode_time(completed if completed is not None else created)
    return sample.finalize()


_OPENCODE_MAX_MESSAGES = 20_000
_OPENCODE_MAX_PARTS = 100_000
_OPENCODE_MAX_BYTES = 16 << 20


def parse_opencode_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    """Read text turns and per-step usage from OpenCode's SQLite store.

    Tools, synthetic parts and summaries are excluded from the transcript. The observed message/part
    schema stores provider JSON in `data` and millisecond times in columns; assistant messages carry
    `tokens` (input, output, reasoning, cache read/write), OpenCode's computed `cost`, and `modelID`.
    """
    if not is_valid_session_id(session_id):
        raise ValueError("invalid OpenCode session id")
    with closing(_connect_read_only(path)) as connection:
        connection.execute("BEGIN")
        session = connection.execute("SELECT directory FROM session WHERE id = ?", (session_id,)).fetchone()
        if session is None:
            raise ValueError("OpenCode session disappeared")
        cwd = resolve_cwd(session[0] or cwd)
        # Check sizes inside the same read transaction before materializing provider JSON.
        sizes = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM message WHERE session_id = ? "
            "UNION ALL SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM part WHERE session_id = ?",
            (session_id, session_id),
        ).fetchall()
        if (
            sizes[0][0] > _OPENCODE_MAX_MESSAGES
            or sizes[1][0] > _OPENCODE_MAX_PARTS
            or sum(row[1] for row in sizes) > _OPENCODE_MAX_BYTES
        ):
            raise ValueError("OpenCode session exceeds transcript bounds")
        # The same read transaction keeps these rows within the bounds checked above.
        messages = connection.execute(
            "SELECT id, time_created, data FROM message WHERE session_id = ? ORDER BY time_created, id",
            (session_id,),
        ).fetchall()
        parts = connection.execute(
            "SELECT id, message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
            (session_id,),
        ).fetchall()
    content: dict[str, list[str]] = {}
    message_ids = {row[0] for row in messages}
    for _, message_id, raw in parts:
        if message_id not in message_ids:
            raise ValueError("OpenCode part references a missing message")
        part = _json_document(raw, "OpenCode part")
        if not isinstance(part, dict):
            raise ValueError("invalid OpenCode part")
        if part.get("type") == "text" and not part.get("synthetic") and not part.get("ignored"):
            if not isinstance(part.get("text"), str):
                raise ValueError("invalid OpenCode text")
            content.setdefault(message_id, []).append(part["text"])
    logs = []
    requests: list[UsageRecord] = []
    costs: list[float | None] = []
    usage_error: Exception | None = None
    # One assistant message without counters (an older release) makes the session's usage unknown.
    measured = True
    for message_id, created, raw in messages:
        message = _json_document(raw, "OpenCode message")
        if not isinstance(message, dict):
            raise ValueError("invalid OpenCode message")
        role = message.get("role")
        if role == "assistant" and message.get("tokens") is None:
            measured = False
        elif role == "assistant" and usage_error is None:
            # Summaries are model calls too, so they count toward usage but not the transcript.
            try:
                requests.append(_opencode_request(message, created, session_id, cwd))
                costs.append(_usage_cost(message.get("cost")))
            except ValueError as error:
                usage_error = error
        if role not in {"user", "assistant"} or message.get("summary") is True:
            continue
        timestamp = _opencode_time(created)
        body = "\n".join(content.get(message_id, []))
        if body.strip():
            logs.append(SessionLog(timestamp, "opencode", session_id, role, body, cwd))
    usage = None
    if requests and measured and usage_error is None:
        usage = UsageRecord(
            harness="opencode",
            agent="opencode",
            session_id=session_id,
            cwd=cwd,
            measurement_kind="provider-reported",
            source_bytes=sum(len(row[2]) for row in messages),
        )
        usage.set_samples(requests)
        usage.timestamp = max(request.timestamp for request in requests)
        if all(cost is not None for cost in costs):
            usage.cost_usd = sum(cost for cost in costs if cost is not None)
            usage.cost_known = True
        usage, usage_error = _finalize_parsed_usage(usage, None, usage.timestamp)
    return ParsedSession(
        logs,
        fingerprint_json(
            {"cwd": cwd, "messages": [tuple(row) for row in messages], "parts": [tuple(row) for row in parts]}
        ),
        "opencode-db",
        usage=usage,
        usage_error=usage_error,
    )


def _file_uri_path(value: object) -> str:
    """Return the absolute local path of a file URI, or an empty string for anything else."""
    if not isinstance(value, str):
        return ""
    parts = urlsplit(value)
    # Check NUL after decoding: unquote turns %00 into the byte that path resolution rejects.
    path = unquote(parts.path)
    if parts.scheme != "file" or parts.netloc not in {"", "localhost"} or not path.startswith("/") or "\x00" in path:
        return ""
    return path


def agy_workspaces(root: Path) -> dict[str, str]:
    """Map each Antigravity conversation id to its first local workspace path."""
    path = root.parent / AGY_SUMMARIES_NAME
    if not path.exists():
        # Older CLI releases kept no summaries database: sessions stay without a CWD.
        return {}
    with closing(_connect_read_only(path)) as connection:
        rows = connection.execute(
            "SELECT conversation_id, workspace_uris FROM conversation_summaries LIMIT ?",
            (_AGY_SUMMARIES_LIMIT + 1,),
        ).fetchall()
    if len(rows) > _AGY_SUMMARIES_LIMIT:
        raise ValueError(f"Antigravity summaries exceed {_AGY_SUMMARIES_LIMIT} conversations")
    workspaces: dict[str, str] = {}
    for identifier, uris in rows:
        if not isinstance(identifier, str) or not isinstance(uris, str) or not uris:
            continue
        try:
            values = json.loads(uris)
        except ValueError, RecursionError:
            # One unreadable row costs only that conversation's CWD.
            continue
        if isinstance(values, list):
            workspace = next((path for path in map(_file_uri_path, values) if path), "")
            if workspace:
                workspaces[identifier] = workspace
    return workspaces


def _raise_walk_error(error: OSError) -> None:
    raise error


def _session_files(root: Path, names: tuple[str, ...]) -> list[Path]:
    """Enumerate without hiding inaccessible directories or following directory links."""
    return sorted(
        directory / name
        for directory, _, files in root.walk(on_error=_raise_walk_error)
        for name in files
        # A dangling symlink is no session; parsing it would fail every sync with a bare ENOENT.
        if any(fnmatchcase(name, pattern) for pattern in names) and (directory / name).exists()
    )


def _enumerate_agy(root: Path) -> list[SessionCandidate]:
    candidates: list[SessionCandidate] = []
    workspaces = agy_workspaces(root)
    for directory in sorted(root.iterdir()):
        if not stat.S_ISDIR(directory.lstat().st_mode):
            continue
        for name in AGY_TRANSCRIPT_NAMES:
            path = directory / ".system_generated" / "logs" / name
            try:
                mode = path.stat().st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISREG(mode):
                candidates.append((directory.name, workspaces.get(directory.name, ""), path))
                break
    return candidates


def _enumerate_claude(root: Path) -> list[SessionCandidate]:
    return [
        (session_id, "", path)
        for path in _session_files(root, ("*.jsonl",))
        if is_valid_session_id(session_id := claude_session_id(path))
    ]


def _enumerate_copilot(root: Path) -> list[SessionCandidate]:
    with closing(_connect_read_only(root)) as connection:
        return [
            (row[0], row[1] or "", root)
            for row in connection.execute("SELECT id, cwd FROM sessions")  # nosemgrep: formatted-sql-query
            if is_valid_session_id(row[0])
        ]


def _enumerate_opencode(root: Path) -> list[SessionCandidate]:
    with closing(_connect_read_only(root)) as connection:
        rows = connection.execute("SELECT id, directory FROM session ORDER BY id LIMIT 20001").fetchall()
    if len(rows) > 20000:
        raise ValueError("OpenCode exceeds 20000 sessions")
    candidates: list[SessionCandidate] = []
    for identifier, directory in rows:
        if not isinstance(identifier, str) or not is_valid_session_id(identifier):
            raise ValueError("invalid OpenCode session identity")
        candidates.append((identifier, directory or "", root))
    return candidates


# Harnesses dot no longer captures (removed 2026-10-25); their archived bundles stay queryable.
RETIRED_AGENTS = ("codex", "grok")

AGENT_ADAPTERS: dict[str, AgentAdapter] = {
    "agy": AgentAdapter("agy", "agy", False, parse_agy_session, _enumerate_agy, "Antigravity", external_cwd=True),
    "claude": AgentAdapter("claude", "Claude", False, parse_claude_session, _enumerate_claude, "Claude Code"),
    "copilot": AgentAdapter("copilot", "Copilot", True, parse_copilot_session, _enumerate_copilot, "Copilot"),
    "opencode": AgentAdapter("opencode", "OpenCode", True, parse_opencode_session, _enumerate_opencode, "OpenCode"),
}
