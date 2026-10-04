"""Verified discovery, transcript parsing, and usage extraction for agent stores."""

from __future__ import annotations

import json
import math
import sqlite3
import stat
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fmind_dot.archive.store import (
    SessionLog,
    fingerprint_bytes,
    fingerprint_json,
    is_valid_session_id,
    propagate_models,
)
from fmind_dot.archive.usage import UsageRecord

AGY_TRANSCRIPT_NAMES = ("transcript_full.jsonl", "transcript.jsonl")
GROK_TRANSCRIPT_NAME = "updates.jsonl"
# xAI reports exact integer cost ticks; its headless-mode guide defines 1 USD = 10^10 ticks.
_GROK_TICKS_PER_USD = 10**10
_GROK_TOKEN_FIELDS = (
    ("inputTokens", "input_tokens"),
    ("outputTokens", "output_tokens"),
    ("cachedReadTokens", "cached_tokens"),
    ("cacheCreationTokens", "cache_write_tokens"),
    ("reasoningTokens", "reasoning_tokens"),
    ("totalTokens", "total_tokens"),
)


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


@dataclass(frozen=True)
class AgentAdapter:
    name: str
    label: str
    database: bool
    parser: SessionParser


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
    # Decode one LF-delimited record at a time: large Codex snapshots can be
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
    latest: tuple[datetime, str] | None = None
    for log in logs:
        try:
            parsed = datetime.fromisoformat(log.ts)
        except ValueError:
            continue
        parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        if latest is None or parsed > latest[0]:
            latest = (parsed, log.ts)
    if latest is not None:
        return latest[1]
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


def parse_agy_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    usage = UsageRecord(
        harness="agy",
        agent="agy",
        session_id=session_id,
        model="gemini",
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
        if source == "USER_EXPLICIT" and kind == "USER_INPUT":
            usage.turn_count += 1
            input_bytes += len(text.encode())
        elif source == "MODEL" and kind == "PLANNER_RESPONSE":
            output_bytes += len(text.encode())
            thinking = raw.get("thinking")
            if isinstance(thinking, str):
                output_bytes += len(thinking.encode())
        elif kind in {"RUN_COMMAND", "SYSTEM_MESSAGE"}:
            input_bytes += len(text.encode())
        if raw.get("is_truncated") is True:
            continue
        role = ""
        if source == "USER_EXPLICIT" and kind == "USER_INPUT":
            role = "user"
        elif source == "MODEL" and kind == "PLANNER_RESPONSE":
            role = "assistant"
        if role and isinstance(content, str) and content.strip():
            logs.append(SessionLog(str(raw.get("created_at", "")), "agy", session_id, role, content, resolve_cwd(cwd)))
    usage.input_tokens = (input_bytes + 3) // 4
    usage.output_tokens = (output_bytes + 3) // 4
    usage.source_bytes = source_bytes
    parsed_usage, usage_error = _finalize_parsed_usage(usage, None, _undated_usage_timestamp(logs, path))
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


_CODEX_TOKEN_FIELDS = (
    ("input_tokens", "input_tokens"),
    ("output_tokens", "output_tokens"),
    ("cached_input_tokens", "cached_tokens"),
    ("cache_write_input_tokens", "cache_write_tokens"),
    ("reasoning_output_tokens", "reasoning_tokens"),
    ("total_tokens", "total_tokens"),
)


def _codex_counts(value: object, field: str) -> dict[str, int]:
    """Read one complete Codex token usage object; absent counters inside it are zero."""
    usage = _usage_mapping(value, field, optional=False)
    counts = {target: _usage_token_count(usage.get(source), target) for source, target in _CODEX_TOKEN_FIELDS}
    if all(counts[name] is None for name in ("input_tokens", "output_tokens", "total_tokens")):
        raise ValueError(f"usage record field {field!r} has no token counters")
    result = {name: count or 0 for name, count in counts.items()}
    if not result["total_tokens"]:
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def _observe_codex_usage(record: UsageRecord, raw: dict[str, Any]) -> None:
    timestamp = raw.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        record.timestamp = timestamp
    payload = _mapping(raw.get("payload"))
    kind = raw.get("type")
    if kind in {"turn_context", "session_meta"}:
        model = payload.get("model")
        if kind == "turn_context" and isinstance(model, str) and model:
            record.observe_model(model)
        cwd = payload.get("cwd")
        if isinstance(cwd, str) and cwd and not record.cwd:
            record.cwd = resolve_cwd(cwd)
    elif kind == "response_item" and payload.get("role") == "assistant":
        record.turn_count += 1
    elif kind == "event_msg" and payload.get("type") == "token_count":
        info = _usage_mapping(payload.get("info"), "info")
        total = _usage_mapping(info.get("total_token_usage"), "total_token_usage")
        _apply_counters(record, total, _CODEX_TOKEN_FIELDS)


def parse_codex_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    logs: list[SessionLog] = []
    malformed = decoded = 0
    usage_error: Exception | None = None
    active_model = ""
    active_cwd = resolve_cwd(cwd)
    usage = UsageRecord(
        harness="codex",
        agent="codex",
        session_id=session_id,
        cwd=active_cwd,
    )
    samples: list[UsageRecord] = []
    previous_counts = dict.fromkeys((target for _, target in _CODEX_TOKEN_FIELDS), 0)
    timed = True
    # Codex 0.153+ records every response, including compactions that cumulative snapshots omit.
    responses: dict[str, UsageRecord] = {}
    thread_total: dict[str, int] = {}
    recorded = True
    meta: dict[str, Any] | None = None
    records, fingerprint, source_bytes = _jsonl_snapshot(path)
    for raw in records:
        if raw is None:
            malformed += 1
            continue
        decoded += 1
        if meta is None and raw.get("type") == "session_meta":
            # The first metadata line is this thread's; a subagent's forked history repeats its parent's.
            meta = _mapping(raw.get("payload"))
        try:
            _observe_codex_usage(usage, raw)
            payload = _mapping(raw.get("payload"))
            if raw.get("type") == "token_usage_record":
                response = payload.get("response_id")
                if not isinstance(response, str) or not response:
                    raise ValueError("usage record field 'response_id' must be a non-empty string")
                counts = _codex_counts(payload.get("usage"), "usage")
                thread_total = _codex_counts(payload.get("thread_token_usage"), "thread_token_usage")
                if response not in responses:
                    recorded = recorded and bool(raw.get("timestamp"))
                    responses[response] = replace(
                        usage,
                        model=active_model,
                        samples=[],
                        cost_usd=0,
                        cost_known=False,
                        turn_count=1,
                        measurement_kind="provider-reported",
                        **counts,
                    )
            elif (
                raw.get("type") == "event_msg"
                and payload.get("type") == "token_count"
                and _mapping(payload.get("info")).get("total_token_usage")
            ):
                counts = {name: getattr(usage, name) for name in previous_counts}
                if not counts["total_tokens"]:
                    counts["total_tokens"] = counts["input_tokens"] + counts["output_tokens"]
                delta = {name: counts[name] - previous_counts[name] for name in counts}
                timed = timed and bool(raw.get("timestamp")) and all(value >= 0 for value in delta.values())
                if timed and any(delta.values()):
                    samples.append(
                        replace(
                            usage, model=active_model, samples=[], cost_usd=0, cost_known=False, turn_count=1, **delta
                        )
                    )
                previous_counts = counts
        except ValueError as error:
            usage_error = error
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
    propagate_models(logs)
    if responses:
        requests = list(responses.values())
        usage.measurement_kind = "provider-reported"
        if all(sum(getattr(request, name) for request in requests) == count for name, count in thread_total.items()):
            usage.set_samples(requests, timed=recorded)
        else:
            # The provider's thread counter disagrees with its response records, for example when
            # usage predates them: keep the provider's total, without inventing request allocation.
            for name, count in thread_total.items():
                setattr(usage, name, count)
            usage.samples = []
    elif samples and timed:
        usage.set_samples(samples)
    usage.source_bytes = source_bytes
    parsed_usage = None
    if usage.measurement_kind:
        parsed_usage, usage_error = _finalize_parsed_usage(usage, usage_error, _undated_usage_timestamp(logs, path))
    meta = meta or {}
    spawn = _mapping(_mapping(_mapping(meta.get("source")).get("subagent")).get("thread_spawn"))
    parent = spawn.get("parent_thread_id")
    return ParsedSession(
        logs,
        fingerprint,
        "codex-jsonl",
        malformed,
        decoded - len(logs),
        parsed_usage,
        usage_error,
        sidechain=meta.get("thread_source") == "subagent",
        parent_session_id=parent if isinstance(parent, str) and is_valid_session_id(parent) else "",
    )


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
    samples: list[UsageRecord] = []
    cost_ticks = 0
    cost_complete = True
    usage: UsageRecord | None = None
    usage_error: Exception | None = None
    usage_complete = True
    timed = True
    # Both provider files participate in the generation identity. Read each once
    # so an updated measurement cannot be hidden by an unchanged transcript.
    transcript = b"" if path.name == "signals.json" else path.read_bytes()
    signals_path = path.parent / "signals.json"
    try:
        signals = signals_path.read_bytes()
    except FileNotFoundError:
        signals = None
    records = _decode_jsonl(transcript)
    sample_fallback = _undated_usage_timestamp([], path, signals_path)
    fingerprint = fingerprint_json(
        {
            "transcript": fingerprint_bytes(transcript),
            "signals": fingerprint_bytes(signals) if signals is not None else None,
        }
    )
    for raw in records:
        if raw is None:
            malformed += 1
            continue
        decoded += 1
        params = _mapping(raw.get("params"))
        update = _mapping(params.get("update"))
        model = _mapping(update.get("_meta")).get("modelId")
        if isinstance(model, str) and model:
            active_model = model
        if update.get("sessionUpdate") == "turn_completed":
            turn_timestamp = _grok_timestamp(raw.get("timestamp"))
            try:
                turn, ticks, complete = _grok_turn_usage(update, turn_timestamp, session_id, cwd, sample_fallback)
            except ValueError as error:
                usage_error = error
            else:
                timed = timed and (bool(turn_timestamp) or not turn)
                # A failed or cancelled turn without usage (e.g. an HTTP 402) billed nothing
                # measurable; only a turn that should have reported usage leaves a gap.
                unbilled = not update.get("usage") and update.get("stop_reason") in {"error", "cancelled"}
                measured = bool(turn) and all(sample.measurement_kind for sample in turn)
                usage_complete = usage_complete and (unbilled or measured)
                samples.extend(turn)
                cost_ticks += ticks
                cost_complete = cost_complete and (unbilled or complete)
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
    propagate_models(logs)
    if usage_error is None:
        try:
            usage = _parse_grok_usage(
                signals,
                session_id,
                cwd,
                samples,
                cost_ticks,
                cost_complete,
                timed=timed,
                fallback_timestamp=_undated_usage_timestamp(logs, path, signals_path),
            )
            # Both provider files are inspected to produce one measurement.
            if not usage_complete:
                if usage is not None and usage.cost_known:
                    # A complete bill is independent from absent token counters.
                    usage.set_samples([])
                    usage.measurement_kind = ""
                else:
                    usage = None
            if usage is not None:
                usage.source_bytes = len(transcript) + len(signals or b"")
        except (OSError, ValueError) as error:
            usage_error = error
    return ParsedSession(logs, fingerprint, "grok-jsonl", malformed, decoded - len(logs), usage, usage_error)


def _grok_turn_usage(
    update: dict[str, Any], timestamp: str, session_id: str, cwd: str, fallback_timestamp: str
) -> tuple[list[UsageRecord], int, bool]:
    """Return request measurements, reported cost ticks, and completeness for one turn."""
    usage = _usage_mapping(update.get("usage"), "usage")
    incomplete = usage.get("usageIsIncomplete", False)
    if not isinstance(incomplete, bool):
        raise ValueError("usage record field 'usageIsIncomplete' must be a boolean")
    if incomplete:
        # The provider explicitly has no complete measurement. Keep the transcript,
        # but never present partial counters or cost as the session's total.
        return [], 0, False
    if not usage:
        return [], 0, False
    # Per-model counters partition the turn exactly, including finished subagents.
    models = _usage_mapping(usage.get("modelUsage"), "modelUsage") or {"": usage}
    samples: list[UsageRecord] = []
    # The turn total remains authoritative when a per-model cost breakdown is absent.
    ticks = _usage_token_count(usage.get("costUsdTicks"), "cost_usd")
    for index, model in enumerate(sorted(models)):
        counters = _usage_mapping(models[model], "modelUsage entry", optional=False)
        sample = UsageRecord(
            harness="grok",
            session_id=session_id,
            cwd=resolve_cwd(cwd),
            model=model if isinstance(model, str) else "",
            timestamp=timestamp,
            # One completed turn is one prompt however many models billed it.
            turn_count=1 if index == 0 else 0,
        )
        _apply_counters(sample, counters, _GROK_TOKEN_FIELDS)
        samples.append(sample.finalize(fallback_timestamp=fallback_timestamp))
    # An unstamped turn cannot establish a complete bill, including known zero.
    return samples, ticks or 0, ticks is not None


def _parse_grok_usage(
    content: bytes | None,
    session_id: str,
    cwd: str,
    samples: list[UsageRecord],
    cost_ticks: int,
    cost_complete: bool,
    *,
    timed: bool,
    fallback_timestamp: str,
) -> UsageRecord | None:
    record = UsageRecord(
        harness="grok", agent="grok", session_id=session_id, cwd=resolve_cwd(cwd), measurement_kind="context-only"
    )
    context_known = False
    if content is not None:
        record.source_bytes = len(content)
        value = _json_document(content, "Grok signals")
        if not isinstance(value, dict):
            raise ValueError("Grok signals must contain a JSON object")
        model = value.get("primaryModelId")
        if isinstance(model, str):
            record.model = model
        tokens = _usage_token_count(value.get("contextTokensUsed"), "input_tokens")
        if tokens is not None:
            record.input_tokens = tokens
            context_known = True
        turns = _usage_token_count(value.get("turnCount"), "turn_count")
        if turns is not None:
            record.turn_count = turns
    if not samples:
        # Signals hold one final context reading, not what the session consumed.
        return record.finalize(fallback_timestamp=fallback_timestamp) if context_known else None
    record.measurement_kind = "provider-reported"
    record.set_samples(samples, timed=timed)
    record.timestamp = max(sample.timestamp for sample in samples) if timed else ""
    if cost_complete:
        record.cost_usd = cost_ticks / _GROK_TICKS_PER_USD
        record.cost_known = True
    return record.finalize(fallback_timestamp=fallback_timestamp)


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
            usage = _extract_copilot_usage(connection, session_id, cwd, _undated_usage_timestamp(logs, path))
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
    connection: sqlite3.Connection, session_id: str, cwd: str, fallback_timestamp: str
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
    )
    if session is not None:
        if not record.cwd:
            record.cwd = resolve_cwd(session["cwd"] or "")
        record.timestamp = session["created_at"] or ""
    for row in rows:
        if row["model"]:
            record.observe_model(str(row["model"]))
        _apply_counters(record, dict(row), _COPILOT_TOKEN_FIELDS, accumulate=True)
        record.turn_count += 1
    if not rows or any(row["input_tokens"] is None and row["output_tokens"] is None for row in rows):
        return None
    record.total_tokens = record.input_tokens + record.output_tokens + record.cached_tokens + record.cache_write_tokens
    return record.finalize(fallback_timestamp=fallback_timestamp)


def parse_opencode_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    """Read text turns from OpenCode's SQLite store; tools, synthetic parts and summaries are excluded.

    This adapter projects transcripts only. Usage remains unavailable rather than inventing zeros.
    The observed message/part schema stores provider JSON in `data` and millisecond times in columns.
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
        if sizes[0][0] > 20000 or sizes[1][0] > 100000 or sum(row[1] for row in sizes) > 16 << 20:
            raise ValueError("OpenCode session exceeds transcript bounds")
        messages = connection.execute(
            "SELECT id, time_created, data FROM message WHERE session_id = ? ORDER BY time_created, id LIMIT 20001",
            (session_id,),
        ).fetchall()
        parts = connection.execute(
            "SELECT id, message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id LIMIT 100001",
            (session_id,),
        ).fetchall()
    if len(messages) > 20000 or len(parts) > 100000 or sum(len(row[2]) for row in [*messages, *parts]) > 16 << 20:
        raise ValueError("OpenCode session exceeds transcript bounds")
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
    for message_id, created, raw in messages:
        message = _json_document(raw, "OpenCode message")
        if not isinstance(message, dict):
            raise ValueError("invalid OpenCode message")
        role = message.get("role")
        if role not in {"user", "assistant"} or message.get("summary") is True:
            continue
        if type(created) is not int or not 0 <= created <= 253402300799000:
            raise ValueError("invalid OpenCode message time")
        timestamp = datetime.fromtimestamp(created / 1000, UTC).isoformat()
        body = "\n".join(content.get(message_id, []))
        if body.strip():
            logs.append(SessionLog(timestamp, "opencode", session_id, role, body, cwd))
    return ParsedSession(
        logs,
        fingerprint_json(
            {"cwd": cwd, "messages": [tuple(row) for row in messages], "parts": [tuple(row) for row in parts]}
        ),
        "opencode-db",
    )


AGENT_ADAPTERS: dict[str, AgentAdapter] = {
    "agy": AgentAdapter("agy", "agy", False, parse_agy_session),
    "claude": AgentAdapter("claude", "Claude", False, parse_claude_session),
    "codex": AgentAdapter("codex", "Codex", False, parse_codex_session),
    "grok": AgentAdapter("grok", "Grok", False, parse_grok_session),
    "copilot": AgentAdapter("copilot", "Copilot", True, parse_copilot_session),
    "opencode": AgentAdapter("opencode", "OpenCode", True, parse_opencode_session),
}


def _raise_walk_error(error: OSError) -> None:
    raise error


def _session_files(root: Path, names: tuple[str, ...]) -> list[Path]:
    """Enumerate without hiding inaccessible directories or following directory links."""
    return sorted(
        directory / name
        for directory, _, files in root.walk(on_error=_raise_walk_error)
        for name in files
        if any(fnmatchcase(name, pattern) for pattern in names)
    )


def enumerate_sessions(root: Path, agent: str) -> list[tuple[str, str, Path]]:
    """Return session id, CWD, and source path for one verified adapter."""
    candidates: list[tuple[str, str, Path]] = []
    if agent == "agy":
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
                    candidates.append((directory.name, "", path))
                    break
    elif agent == "claude":
        for path in _session_files(root, ("*.jsonl",)):
            session_id = claude_session_id(path)
            if is_valid_session_id(session_id):
                candidates.append((session_id, "", path))
    elif agent == "codex":
        for path in _session_files(root, ("*.jsonl",)):
            session_id = codex_session_id(path)
            if is_valid_session_id(session_id):
                candidates.append((session_id, "", path))
    elif agent == "grok":
        directories = {path.parent for path in _session_files(root, (GROK_TRANSCRIPT_NAME, "signals.json"))}
        for directory in sorted(directories):
            path = directory / GROK_TRANSCRIPT_NAME
            if not path.is_file():
                path = directory / "signals.json"
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
    elif agent == "opencode":
        with closing(_connect_read_only(root)) as connection:
            rows = connection.execute("SELECT id, directory FROM session ORDER BY id LIMIT 20001").fetchall()
            if len(rows) > 20000:
                raise ValueError("OpenCode exceeds 20000 sessions")
            for identifier, directory in rows:
                if not isinstance(identifier, str) or not is_valid_session_id(identifier):
                    raise ValueError("invalid OpenCode session identity")
                candidates.append((identifier, directory or "", root))
    else:
        raise ValueError(f"agent {agent!r} has no verified session parser")
    return candidates


__all__ = [
    "AGENT_ADAPTERS",
    "AGY_TRANSCRIPT_NAMES",
    "GROK_TRANSCRIPT_NAME",
    "AgentAdapter",
    "ParsedSession",
    "claude_session_id",
    "codex_session_id",
    "enumerate_sessions",
    "grok_cwd_from_path",
    "parse_agy_session",
    "parse_claude_session",
    "parse_codex_session",
    "parse_copilot_session",
    "parse_grok_session",
    "resolve_cwd",
]
