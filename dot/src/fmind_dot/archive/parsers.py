"""Verified discovery, transcript parsing, and usage extraction for live agent stores."""

from __future__ import annotations

import json
import math
import re
import sqlite3
import stat
from collections.abc import Callable, Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from fmind_dot.archive.store import (
    SessionLog,
    fingerprint_bytes,
    fingerprint_json,
    format_utc_z,
    is_valid_session_id,
    parse_utc_instant,
    propagate_models,
)
from fmind_dot.archive.usage import UsageRecord, check_cost

AGY_TRANSCRIPT_NAMES = ("transcript_full.jsonl", "transcript.jsonl")
AGY_SUMMARIES_NAME = "conversation_summaries.db"
_AGY_SUMMARIES_LIMIT = 100_000
_SURROGATE_ESCAPE = re.compile(rb"\\u[dD][89a-fA-F]")
_AGY_ROLES = {("USER_EXPLICIT", "USER_INPUT"): "user", ("MODEL", "PLANNER_RESPONSE"): "assistant"}
_AGY_FIELDS = {
    "input_tokens": "input_tokens",
    "output_tokens": "output_tokens",
    "cache_read_tokens": "cached_tokens",
    "cache_write_tokens": "cache_write_tokens",
}
_CLAUDE_FIELDS = {
    "input_tokens": "input_tokens",
    "output_tokens": "output_tokens",
    "cache_read_input_tokens": "cached_tokens",
    "cache_creation_input_tokens": "cache_write_tokens",
}
_PI_FIELDS = {
    "input": "input_tokens",
    "output": "output_tokens",
    "cacheRead": "cached_tokens",
    "cacheWrite": "cache_write_tokens",
    "cacheWrite1h": "cache_write_1h_tokens",
    "reasoning": "reasoning_tokens",
    "totalTokens": "total_tokens",
}
_MAX_COUNTERS = ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens", "cache_write_1h_tokens")


@dataclass
class ParsedSession:
    logs: list[SessionLog]
    fingerprint: str
    source_type: str
    malformed: int = 0
    skipped: int = 0
    usage: UsageRecord | None = None
    usage_error: Exception | None = None
    sidechain: bool = False
    parent_session_id: str = ""


SessionParser = Callable[[Path, str, str], ParsedSession]
SessionCandidate = tuple[str, str, Path]


@dataclass(frozen=True)
class AgentAdapter:
    name: str
    label: str
    parser: SessionParser
    enumerate: Callable[[Path], list[SessionCandidate]]
    external_cwd: bool = False


def resolve_cwd(value: str) -> str:
    if not value:
        return ""
    try:
        return str(Path(value).expanduser().resolve(strict=False))
    except RuntimeError:
        raise ValueError("cannot expand a home directory in the project path") from None


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str, int, int, str]:
    content = path.read_bytes()
    rows: list[dict[str, Any]] = []
    malformed = 0
    for raw_line in BytesIO(content):
        try:
            if not (line := raw_line.decode()).strip():
                continue
            value = json.loads(line)
            if _SURROGATE_ESCAPE.search(raw_line):
                json.dumps(value, ensure_ascii=False).encode()
        except UnicodeDecodeError, UnicodeEncodeError, json.JSONDecodeError, RecursionError:
            malformed += 1
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            malformed += 1
    try:
        mtime = format_utc_z(datetime.fromtimestamp(path.stat().st_mtime, UTC), seconds=True)
    except FileNotFoundError:
        mtime = ""
    return rows, fingerprint_bytes(content), len(content), malformed, mtime


def _token_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or value < 0
        or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()))
    ):
        raise ValueError(f"usage record field {field!r} must be a non-negative integer")
    return int(value)


def _mapping(value: object, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"usage record field {field!r} must be an object")
    return value


def _apply_counters(
    record: UsageRecord, counters: Mapping[str, object], fields: Mapping[str, str], *, accumulate: bool = False
) -> None:
    for source, target in fields.items():
        if (count := _token_int(counters.get(source), target)) is not None:
            setattr(record, target, getattr(record, target) + count if accumulate else count)
            if target in {"input_tokens", "output_tokens", "total_tokens"} or (
                count > 0 and target in {"cached_tokens", "cache_write_tokens"}
            ):
                record.measurement_kind = "provider-reported"


def _build_sample(
    harness: str, session_id: str, counters: Mapping[str, object], fields: Mapping[str, str], mtime: str, **init: Any
) -> tuple[UsageRecord, bool]:
    sample = UsageRecord(harness=harness, session_id=session_id, **init)
    _apply_counters(sample, counters, fields)
    has_ts = bool(sample.timestamp)
    sample.finalize(fallback_timestamp=mtime)
    return sample, has_ts


def _latest_ts(values: Iterable[str]) -> str:
    dated = [(instant, v) for v in values if (instant := parse_utc_instant(v)) is not None]
    return max(dated, key=lambda item: item[0])[1] if dated else ""


def _finalize_usage(
    record: UsageRecord, error: Exception | None, logs: list[SessionLog], mtime: str
) -> tuple[UsageRecord | None, Exception | None]:
    if error is not None:
        return None, error
    try:
        return record.finalize(fallback_timestamp=_latest_ts(log.ts for log in logs) or mtime), None
    except ValueError as usage_error:
        return None, usage_error


def _apply_samples(usage: UsageRecord, samples: list[UsageRecord], *, timed: bool) -> None:
    usage.measurement_kind = "provider-reported"
    usage.set_samples(samples, timed=timed)
    usage.timestamp = _latest_ts(s.timestamp for s in samples) if timed else ""


def _text_blocks(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        p["text"]
        for p in content
        if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str) and p["text"]
    )


def parse_agy_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    rows, fingerprint, source_bytes, malformed, mtime = _load_jsonl(path)
    logs: list[SessionLog] = []
    kw: dict[str, Any] = {"agent": "agy", "model": "unknown", "cwd": resolve_cwd(cwd)}
    usage = UsageRecord(
        harness="agy", session_id=session_id, measurement_kind="estimated", source_bytes=source_bytes, **kw
    )
    timestamps: list[str] = []
    samples: list[UsageRecord] = []
    usage_error: Exception | None = None
    in_b = out_b = prompts = unmeasured = 0
    timed = True
    for raw in rows:
        ts = raw_ts if isinstance(raw_ts := raw.get("created_at"), str) else ""
        if ts:
            timestamps.append(ts)
        has_counters = any(f in raw for f in _AGY_FIELDS)
        if usage_error is None and has_counters:
            try:
                sample, has_ts = _build_sample("agy", session_id, raw, _AGY_FIELDS, mtime, timestamp=ts, **kw)
                timed = timed and has_ts
                sample.turn_count, prompts = prompts, 0
                samples.append(sample)
            except ValueError as error:
                usage_error = error
        kind, content = raw.get("type"), raw.get("content")
        text = content if isinstance(content, str) else ""
        role = _AGY_ROLES.get((raw.get("source"), kind), "")
        if role == "user":
            usage.turn_count += 1
            prompts += 1
            in_b += len(text.encode())
        elif role == "assistant":
            unmeasured += not has_counters
            out_b += len(text.encode()) + (len(t.encode()) if isinstance(t := raw.get("thinking"), str) else 0)
        elif kind in {"RUN_COMMAND", "SYSTEM_MESSAGE"}:
            in_b += len(text.encode())
        truncated = raw.get("truncated_fields")
        if raw.get("is_truncated") is True or (isinstance(truncated, list) and "content" in truncated):
            continue
        if role and isinstance(content, str) and content.strip():
            logs.append(SessionLog(ts, "agy", session_id, role, content, usage.cwd))
    if samples and not unmeasured and all(s.measurement_kind for s in samples):
        samples[-1].turn_count += prompts
        _apply_samples(usage, samples, timed=timed)
    else:
        usage.input_tokens, usage.output_tokens = (in_b + 3) // 4, (out_b + 3) // 4
        usage.timestamp = _latest_ts(timestamps)
    parsed_usage, usage_error = _finalize_usage(usage, usage_error, logs, mtime)
    if usage.cwd:
        fingerprint = fingerprint_json({"transcript": fingerprint, "cwd": usage.cwd})
    skipped = len(rows) - len(logs)
    return ParsedSession(logs, fingerprint, "antigravity-jsonl", malformed, skipped, parsed_usage, usage_error)


def claude_session_id(path: Path) -> str:
    return "" if path.name in {"memory.jsonl", "journal.jsonl"} else path.stem


def claude_parent_session_id(path: Path) -> str:
    return next(
        (a.parent.name if is_valid_session_id(a.parent.name) else "" for a in path.parents if a.name == "subagents"), ""
    )


def parse_claude_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    rows, fingerprint, source_bytes, malformed, mtime = _load_jsonl(path)
    logs: list[SessionLog] = []
    usage_error: Exception | None = None
    usage = UsageRecord(
        harness="claude", agent="claude", session_id=session_id, cwd=resolve_cwd(cwd), source_bytes=source_bytes
    )
    messages: dict[tuple[str, str], UsageRecord] = {}
    timed, parent = True, claude_parent_session_id(path)
    for idx, raw in enumerate(rows, start=1):
        declared, kind, message = raw.get("sessionId"), raw.get("type"), raw.get("message")
        if (
            not parent
            and raw.get("isSidechain") is True
            and isinstance(declared, str)
            and declared != session_id
            and is_valid_session_id(declared)
        ):
            parent = declared
        ts = raw_ts if isinstance(raw_ts := raw.get("timestamp"), str) else ""
        line_cwd = raw_cwd if isinstance(raw_cwd := raw.get("cwd"), str) else ""
        try:
            target = UsageRecord(harness="claude", session_id=session_id) if kind == "assistant" else usage
            if ts and (kind == "assistant" or parse_utc_instant(ts) is not None):
                target.timestamp = ts
            if line_cwd and not target.cwd:
                target.cwd = resolve_cwd(line_cwd)
            if kind == "cost-state":
                cost = check_cost(raw.get("totalCostUSD"))
                if not isinstance(unknown := raw.get("hasUnknownModelCost", False), bool):
                    raise ValueError("usage record field 'hasUnknownModelCost' must be a boolean")
                if unknown:
                    usage.cost_usd, usage.cost_known = 0.0, False
                elif cost is not None:
                    usage.cost_usd, usage.cost_known = cost, True
            elif kind == "assistant":
                msg = _mapping(message, "message")
                target.turn_count = 1
                if isinstance(model := msg.get("model"), str) and model:
                    target.observe_model(model)
                if model == "<synthetic>":
                    target.measurement_kind = "provider-reported"
                raw_u = _mapping(msg.get("usage"), "usage")
                _apply_counters(target, raw_u, _CLAUDE_FIELDS, accumulate=True)
                raw_cw = _mapping(raw_u.get("cache_creation"), "cache_creation")
                if c1h := _token_int(raw_cw.get("ephemeral_1h_input_tokens"), "cache_write_1h_tokens"):
                    target.cache_write_1h_tokens += c1h
                ident = msg.get("id")
                key = (str(raw.get("requestId", "")), ident) if isinstance(ident, str) and ident else ("row", str(idx))
                if prev := messages.get(key):
                    for attr in ("measurement_kind", "model", "cwd", "timestamp"):
                        setattr(target, attr, getattr(target, attr) or getattr(prev, attr))
                    for name in _MAX_COUNTERS:
                        setattr(target, name, max(getattr(prev, name), getattr(target, name)))
                    target.total_tokens = (
                        target.input_tokens + target.output_tokens + target.cached_tokens + target.cache_write_tokens
                    )
                messages[key] = target
        except ValueError as error:
            usage_error = error
        if kind not in {"user", "assistant"} or not isinstance(message, dict):
            continue
        raw_content = message.get("content")
        content = _text_blocks(raw_content) if kind == "user" or isinstance(raw_content, list) else ""
        if content.strip():
            model = message.get("model") if isinstance(message.get("model"), str) else ""
            try:
                resolved = resolve_cwd(line_cwd or cwd)
            except ValueError as error:
                usage_error, resolved = usage_error or error, ""
            meta = kind == "user" and raw.get("isMeta") is True
            logs.append(SessionLog(ts, "claude", session_id, str(kind), content, resolved, model, meta))
    propagate_models(logs)
    if usage_error is None:
        try:
            for sample in messages.values():
                timed = timed and bool(sample.timestamp)
                sample.finalize(fallback_timestamp=mtime)
        except ValueError as error:
            usage_error = error
    measured = bool(messages) and all(sample.measurement_kind for sample in messages.values())
    if measured:
        _apply_samples(usage, list(messages.values()), timed=timed)
        usage.cwd = usage.cwd or next((sample.cwd for sample in messages.values() if sample.cwd), "")
    parsed_usage, usage_error = (
        (None, usage_error)
        if not measured and not usage.cost_known
        else _finalize_usage(usage, usage_error, logs, mtime)
    )
    return ParsedSession(
        logs,
        fingerprint,
        "claude-jsonl",
        malformed,
        len(rows) - len(logs),
        parsed_usage,
        usage_error,
        bool(parent),
        parent,
    )


def pi_session_id(path: Path) -> str:
    return path.stem.partition("_")[2]


def parse_pi_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    rows, fingerprint, source_bytes, malformed, mtime = _load_jsonl(path)
    logs: list[SessionLog] = []
    samples: list[UsageRecord] = []
    cost, all_costs, timed = 0.0, True, True
    usage_error: Exception | None = None
    forked, forked_at, session_cwd = False, None, resolve_cwd(cwd)
    for raw in rows:
        kind = raw.get("type")
        ts = stamp if isinstance(stamp := raw.get("timestamp"), str) else ""
        if kind == "session":
            if isinstance(header_cwd := raw.get("cwd"), str) and header_cwd:
                session_cwd = resolve_cwd(header_cwd)
            if raw.get("parentSession"):
                forked, forked_at = True, parse_utc_instant(ts)
            continue
        instant = parse_utc_instant(ts)
        if forked_at is not None and instant is not None and instant < forked_at:
            continue
        message = raw.get("message") if kind == "message" else None
        role = message.get("role") if isinstance(message, dict) else None
        measured = (message if role in {"assistant", "toolResult"} else None) if kind == "message" else raw
        if isinstance(measured, dict) and measured.get("usage") is not None:
            try:
                if forked and (forked_at is None or instant is None):
                    raise ValueError("forked Pi session usage requires valid header and entry timestamps")
                raw_u = _mapping(measured.get("usage"), "usage")
                model = m if isinstance(m := measured.get("model"), str) else ""
                kw = {"model": model, "timestamp": ts, "turn_count": int(role == "assistant")}
                sample, has_ts = _build_sample("pi", session_id, raw_u, _PI_FIELDS, mtime, **kw)
                sample_cost = check_cost(_mapping(raw_u.get("cost"), "cost").get("total"))
                timed = timed and has_ts
            except ValueError as error:
                usage_error = error
            else:
                samples.append(sample)
                if sample_cost is None:
                    all_costs = False
                else:
                    cost += sample_cost
        if (
            isinstance(message, dict)
            and role in {"user", "assistant"}
            and (content := _text_blocks(message.get("content"))).strip()
        ):
            model = message.get("model") if isinstance(message.get("model"), str) else ""
            logs.append(SessionLog(ts, "pi", session_id, str(role), content, session_cwd, model))
    propagate_models(logs)
    usage = UsageRecord(harness="pi", agent="pi", session_id=session_id, cwd=session_cwd, source_bytes=source_bytes)
    if samples and all(s.measurement_kind for s in samples):
        _apply_samples(usage, samples, timed=timed)
        if all_costs:
            usage.cost_usd, usage.cost_known = cost, True
        parsed_usage, usage_error = _finalize_usage(usage, usage_error, logs, mtime)
    else:
        parsed_usage = None
    return ParsedSession(logs, fingerprint, "pi-jsonl", malformed, len(rows) - len(logs), parsed_usage, usage_error)


def agy_workspaces(root: Path) -> dict[str, str]:
    path = root.parent / AGY_SUMMARIES_NAME
    if not path.exists():
        return {}
    conn = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    with closing(conn):
        rows = conn.execute(
            "SELECT conversation_id, workspace_uris FROM conversation_summaries LIMIT ?", (_AGY_SUMMARIES_LIMIT + 1,)
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
            continue
        if isinstance(values, list):
            for uri in values:
                if (
                    isinstance(uri, str)
                    and (parts := urlsplit(uri)).scheme == "file"
                    and parts.netloc in {"", "localhost"}
                    and (p := unquote(parts.path)).startswith("/")
                    and "\x00" not in p
                ):
                    workspaces[identifier] = p
                    break
    return workspaces


def _raise_walk(error: OSError) -> None:
    raise error


def _enumerate_jsonl(root: Path, get_id: Callable[[Path], str]) -> list[SessionCandidate]:
    files = sorted(
        d / n
        for d, _, names in root.walk(on_error=_raise_walk)
        for n in names
        if n.endswith(".jsonl") and (d / n).exists()
    )
    return [(sid, "", p) for p in files if is_valid_session_id(sid := get_id(p))]


def _enumerate_agy(root: Path) -> list[SessionCandidate]:
    candidates: list[SessionCandidate] = []
    workspaces = agy_workspaces(root)
    for directory in sorted(root.iterdir()):
        if not stat.S_ISDIR(directory.lstat().st_mode) or not is_valid_session_id(directory.name):
            continue
        for name in AGY_TRANSCRIPT_NAMES:
            path = directory / ".system_generated/logs" / name
            try:
                if stat.S_ISREG(path.stat().st_mode):
                    candidates.append((directory.name, workspaces.get(directory.name, ""), path))
                    break
            except FileNotFoundError:
                continue
    return candidates


AGENT_ADAPTERS: dict[str, AgentAdapter] = {
    "agy": AgentAdapter("agy", "agy", parse_agy_session, _enumerate_agy, external_cwd=True),
    "claude": AgentAdapter("claude", "Claude", parse_claude_session, lambda r: _enumerate_jsonl(r, claude_session_id)),
    "pi": AgentAdapter("pi", "Pi", parse_pi_session, lambda r: _enumerate_jsonl(r, pi_session_id)),
}
