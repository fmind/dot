"""SQLite session discovery, transcript parsing, and usage extraction for Copilot and OpenCode."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fmind_dot.archive.common import (
    ParsedSession,
    SessionCandidate,
    apply_counters,
    apply_samples,
    connect_read_only,
    db_mtime,
    finalize_usage,
    latest_ts,
    mapping,
    resolve_cwd,
    sqlite_columns,
    sqlite_tables,
    sqlite_text,
    text_blocks,
    token_int,
)
from fmind_dot.archive.store import (
    SessionLog,
    fingerprint_json,
    format_utc_z,
    is_valid_session_id,
    parse_utc_instant,
    propagate_models,
)
from fmind_dot.archive.usage import UsageRecord, check_cost

_SESSIONS_LIMIT = 20_000
_MAX_MESSAGES = 20_000
_MAX_PARTS = 100_000
_MAX_BYTES = 16 << 20
_MAX_EPOCH_MS = 253_402_300_799_000
_OPENAI_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4", "openai/")


def enumerate_copilot(root: Path) -> list[SessionCandidate]:
    with connect_read_only(root) as conn:
        if "sessions" not in sqlite_tables(conn):
            return []
        rows = conn.execute("SELECT id, cwd FROM sessions ORDER BY id LIMIT ?", (_SESSIONS_LIMIT + 1,)).fetchall()
    if len(rows) > _SESSIONS_LIMIT:
        raise ValueError(f"Copilot sessions exceed {_SESSIONS_LIMIT}")
    return [
        (sid, row[1] if isinstance(row[1], str) else "", root)
        for row in rows
        if isinstance(sid := row[0], str) and is_valid_session_id(sid)
    ]


def _copilot_uncached_input(
    raw_input: int | None, cache_read: int, cache_write: int, details_json: object, model: str
) -> int | None:
    """Resolve uncached prompt tokens from Copilot's tokenDetails breakdown or model family."""
    if details_json is not None:
        if not isinstance(details_json, str):
            raise ValueError("invalid Copilot token_details_json")
        if details_json.strip():
            try:
                parsed = json.loads(details_json)
            except (ValueError, RecursionError) as error:
                raise ValueError("invalid Copilot token_details_json") from error
            if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
                raise ValueError("invalid Copilot token_details_json")
            for item in parsed:
                if item.get("tokenType") == "input":
                    if item.get("tokenCount") is None:
                        raise ValueError("invalid Copilot token_details_json")
                    return token_int(item.get("tokenCount"), "input_tokens")
            if parsed:
                if raw_input is not None and raw_input == cache_read + cache_write:
                    return 0
                raise ValueError("Copilot token_details_json missing input tokenCount")
    if raw_input is None:
        return None
    if model.startswith(_OPENAI_MODEL_PREFIXES):
        uncached = raw_input - cache_read - cache_write
        if uncached < 0:
            raise ValueError("Copilot OpenAI input_tokens smaller than cached prompt tokens")
        return uncached
    return raw_input


def _fetch_copilot_usage_rows(conn: sqlite3.Connection, session_id: str) -> tuple[list[sqlite3.Row], set[str], int]:
    if "assistant_usage_events" not in sqlite_tables(conn):
        return [], set(), 0
    cols = sqlite_columns(conn, "assistant_usage_events")
    detail_len = "COALESCE(LENGTH(CAST(token_details_json AS BLOB)), 0)" if "token_details_json" in cols else "0"
    ubounds = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(COALESCE(LENGTH(CAST(model AS BLOB)), 0) + {detail_len}), 0) "  # noqa: S608
        "FROM assistant_usage_events WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if ubounds is not None and (ubounds[0] > _MAX_PARTS or ubounds[1] > _MAX_BYTES):
        raise ValueError("Copilot usage events exceed bounds")
    opt_cols = [c for c in ("turn_index", "token_details_json", "created_at") if c in cols]
    base_cols = "model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens"
    select_cols = ", ".join((base_cols, *opt_cols))
    order = " ORDER BY id" if "id" in cols else ""
    rows = conn.execute(
        f"SELECT {select_cols} FROM assistant_usage_events WHERE session_id = ?{order}",  # noqa: S608
        (session_id,),
    ).fetchall()
    return rows, cols, int(ubounds[1]) if ubounds is not None else 0


def _copilot_usage_evidence(rows: Sequence[sqlite3.Row], cols: set[str]) -> list[dict[str, object]]:
    return [
        {
            "turn_index": row["turn_index"] if "turn_index" in cols and isinstance(row["turn_index"], int) else None,
            "model": sqlite_text(row["model"]),
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "cache_read_tokens": row["cache_read_tokens"],
            "cache_write_tokens": row["cache_write_tokens"],
            "reasoning_tokens": row["reasoning_tokens"],
            "token_details_json": sqlite_text(row["token_details_json"]) if "token_details_json" in cols else "",
            "created_at": sqlite_text(row["created_at"]) if "created_at" in cols else "",
        }
        for row in rows
    ]


def _extract_copilot_usage(
    rows: Sequence[sqlite3.Row],
    cols: set[str],
    usage_bytes: int,
    session_id: str,
    session_cwd: str,
    turn_timestamps: Iterable[str],
    mtime: str,
    created_at: str,
) -> tuple[UsageRecord | None, dict[int, str], int]:
    turn_models = {
        row["turn_index"]: row["model"]
        for row in rows
        if "turn_index" in cols
        and isinstance(row["turn_index"], int)
        and isinstance(row["model"], str)
        and row["model"]
    }
    if not rows or any(row["input_tokens"] is None and row["output_tokens"] is None for row in rows):
        return None, turn_models, usage_bytes
    fallback_ts = latest_ts(turn_timestamps) or created_at or mtime
    samples: list[UsageRecord] = []
    timed = "created_at" in cols
    for row in rows:
        model = str(row["model"]) if row["model"] else ""
        cache_read = token_int(row["cache_read_tokens"], "cached_tokens") or 0
        cache_write = token_int(row["cache_write_tokens"], "cache_write_tokens") or 0
        inp = _copilot_uncached_input(
            token_int(row["input_tokens"], "input_tokens"),
            cache_read,
            cache_write,
            row["token_details_json"] if "token_details_json" in cols else None,
            model,
        )
        raw_ts = row["created_at"] if "created_at" in cols else ""
        instant = parse_utc_instant(raw_ts) if isinstance(raw_ts, str) else None
        sample_ts = format_utc_z(instant) if instant is not None else ""
        timed = timed and bool(sample_ts)
        sample = UsageRecord(
            harness="copilot",
            session_id=session_id,
            timestamp=sample_ts,
            model=model,
            input_tokens=inp or 0,
            output_tokens=token_int(row["output_tokens"], "output_tokens") or 0,
            cached_tokens=cache_read,
            cache_write_tokens=cache_write,
            reasoning_tokens=token_int(row["reasoning_tokens"], "reasoning_tokens") or 0,
            turn_count=1,
            measurement_kind="provider-reported",
        )
        sample.finalize(fallback_timestamp=fallback_ts)
        samples.append(sample)
    record = UsageRecord(harness="copilot", agent="copilot", session_id=session_id, cwd=session_cwd)
    apply_samples(record, samples, timed=timed)
    if not timed:
        record.timestamp = fallback_ts
    return record.finalize(fallback_timestamp=fallback_ts), turn_models, usage_bytes


def parse_copilot_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid copilot session id {session_id!r}")
    mtime = db_mtime(path)
    usage_evidence: list[dict[str, object]] = []
    with connect_read_only(path) as conn:
        conn.execute("BEGIN")
        srow = conn.execute("SELECT cwd, created_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if srow is None:
            raise ValueError("Copilot session disappeared")
        raw_cwd, raw_created = srow["cwd"], srow["created_at"]
        if raw_cwd is not None and not isinstance(raw_cwd, str):
            raise ValueError("Copilot session cwd must be a string")
        if raw_created is not None and not isinstance(raw_created, str):
            raise ValueError("Copilot session created_at must be a string")
        session_cwd, cwd_text = resolve_cwd(raw_cwd or cwd), sqlite_text(raw_cwd)
        bounds = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM("
            "COALESCE(LENGTH(CAST(user_message AS BLOB)), 0) + "
            "COALESCE(LENGTH(CAST(assistant_response AS BLOB)), 0)), 0) "
            "FROM turns WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        turn_bytes = int(bounds[1]) if bounds is not None else 0
        if bounds is not None and (bounds[0] > _MAX_MESSAGES or turn_bytes > _MAX_BYTES):
            raise ValueError("Copilot session exceeds transcript bounds")
        turn_rows = conn.execute(
            "SELECT session_id, turn_index, user_message, assistant_response, timestamp "
            "FROM turns WHERE session_id = ? ORDER BY turn_index, id",
            (session_id,),
        ).fetchall()
        turn_stamps = [r["timestamp"] for r in turn_rows if isinstance(r["timestamp"], str)]
        try:
            u_rows, u_cols, u_bytes = _fetch_copilot_usage_rows(conn, session_id)
            usage_evidence = _copilot_usage_evidence(u_rows, u_cols)
            usage, turn_models, usage_bytes = _extract_copilot_usage(
                u_rows, u_cols, u_bytes, session_id, session_cwd, turn_stamps, mtime, raw_created or ""
            )
            usage_error: Exception | None = None
        except (sqlite3.Error, ValueError) as error:
            usage, turn_models, usage_bytes, usage_error = None, {}, 0, error
    evidence, logs = _build_copilot_turns(turn_rows, turn_models, session_id, session_cwd, cwd_text)
    if usage is not None:
        usage.source_bytes = turn_bytes + usage_bytes
    fp = fingerprint_json({"turns": evidence, "usage": usage_evidence})
    return ParsedSession(logs, fp, "copilot-db", usage=usage, usage_error=usage_error)


def _build_copilot_turns(
    turn_rows: Sequence[sqlite3.Row],
    turn_models: Mapping[int, str],
    session_id: str,
    session_cwd: str,
    cwd_text: str,
) -> tuple[list[dict[str, Any]], list[SessionLog]]:
    evidence: list[dict[str, Any]] = []
    logs: list[SessionLog] = []
    for row in turn_rows:
        t_idx = row["turn_index"]
        model = turn_models.get(t_idx, "") if isinstance(t_idx, int) else ""
        user_msg, asst_msg = row["user_message"], row["assistant_response"]
        evidence.append(
            {
                "session_id": sqlite_text(row["session_id"]),
                "user_message": sqlite_text(user_msg),
                "assistant_response": sqlite_text(asst_msg),
                "timestamp": sqlite_text(row["timestamp"]),
                "cwd": cwd_text,
                "turn_index": t_idx if isinstance(t_idx, int) else sqlite_text(t_idx),
            }
        )
        ts = row["timestamp"] if isinstance(row["timestamp"], str) else ""
        for role, text in (("user", user_msg), ("assistant", asst_msg)):
            if isinstance(text, str) and text.strip():
                logs.append(SessionLog(ts, "copilot", session_id, role, text, session_cwd, model))
    propagate_models(logs)
    return evidence, logs


def enumerate_opencode(root: Path) -> list[SessionCandidate]:
    with connect_read_only(root) as conn:
        tables = sqlite_tables(conn)
        table = "session_v2" if "session_v2" in tables else ("session" if "session" in tables else "")
        if not table:
            return []
        rows = conn.execute(f"SELECT id, directory FROM {table} ORDER BY id LIMIT ?", (_SESSIONS_LIMIT + 1,)).fetchall()  # noqa: S608
    if len(rows) > _SESSIONS_LIMIT:
        raise ValueError(f"OpenCode sessions exceed {_SESSIONS_LIMIT}")
    return [
        (sid, row[1] if isinstance(row[1], str) else "", root)
        for row in rows
        if isinstance(sid := row[0], str) and is_valid_session_id(sid)
    ]


def _opencode_time(value: object) -> str:
    if type(value) is not int or not 0 <= value <= _MAX_EPOCH_MS:
        raise ValueError("invalid OpenCode message time")
    return format_utc_z(datetime.fromtimestamp(value / 1000, UTC))


def _opencode_model(data: Mapping[str, Any]) -> str:
    if isinstance(m := data.get("model"), Mapping) and isinstance(mid := m.get("id"), str) and mid:
        prov = m.get("providerID")
        return f"{prov}/{mid}" if isinstance(prov, str) and prov and not mid.startswith(f"{prov}/") else mid
    if isinstance(mid := data.get("modelID"), str) and mid:
        prov = data.get("providerID")
        return f"{prov}/{mid}" if isinstance(prov, str) and prov and not mid.startswith(f"{prov}/") else mid
    return ""


def _opencode_sample(
    data: Mapping[str, Any], created: object, session_id: str, cwd: str
) -> tuple[UsageRecord, float | None]:
    raw_tokens = data.get("tokens")
    if not isinstance(raw_tokens, Mapping):
        raise ValueError("OpenCode assistant message missing tokens object")
    sample = UsageRecord(harness="opencode", session_id=session_id, cwd=cwd, turn_count=1)
    apply_counters(
        sample, raw_tokens, {"input": "input_tokens", "output": "output_tokens", "reasoning": "reasoning_tokens"}
    )
    cache = mapping(raw_tokens.get("cache"), "cache")
    apply_counters(sample, cache, {"read": "cached_tokens", "write": "cache_write_tokens"})
    # OpenCode reports reasoning beside output; canonical archive records include reasoning inside output_tokens.
    sample.output_tokens += sample.reasoning_tokens
    sample.model = _opencode_model(data)
    completed = mapping(data.get("time"), "time").get("completed")
    sample.timestamp = _opencode_time(completed if completed is not None else created)
    return sample.finalize(), check_cost(data.get("cost"))


@dataclass(frozen=True, slots=True)
class _OpenCodeSnapshot:
    session_id: str
    cwd: str
    parent_id: str
    forked: bool
    sess_created: object
    source_bytes: int
    messages: list[sqlite3.Row]
    parts: list[sqlite3.Row]


def _load_opencode_snapshot(path: Path, session_id: str, cwd: str) -> _OpenCodeSnapshot:
    with connect_read_only(path) as conn:
        conn.execute("BEGIN")
        tables = sqlite_tables(conn)
        v2 = "session_v2" in tables
        if not v2 and "session" not in tables:
            raise ValueError("OpenCode session tables missing")
        stbl, mtbl, ptbl = ("session_v2", "session_message", "session_part") if v2 else ("session", "message", "part")
        scols = sqlite_columns(conn, stbl)
        sel = ", ".join(["directory", *(c for c in ("parent_id", "fork_session_id", "time_created") if c in scols)])
        srow = conn.execute(f"SELECT {sel} FROM {stbl} WHERE id = ?", (session_id,)).fetchone()  # noqa: S608
        if srow is None:
            raise ValueError("OpenCode session disappeared")
        raw_dir = srow["directory"]
        if raw_dir is not None and not isinstance(raw_dir, str):
            raise ValueError("OpenCode session directory must be a string")
        raw_parent = srow["parent_id"] if "parent_id" in scols else None
        if raw_parent is not None and (
            not isinstance(raw_parent, str) or (raw_parent and not is_valid_session_id(raw_parent))
        ):
            raise ValueError("invalid OpenCode parent_id")
        forked = bool(srow["fork_session_id"]) if "fork_session_id" in scols else False
        sess_created = srow["time_created"] if "time_created" in scols else None
        if forked and (type(sess_created) is not int or sess_created < 0):
            raise ValueError("forked OpenCode session requires valid time_created")
        sizes = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM {mtbl} WHERE session_id = ? "  # noqa: S608
            f"UNION ALL SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM {ptbl} WHERE session_id = ?",
            (session_id, session_id),
        ).fetchall()
        source_bytes = int(sum(r[1] for r in sizes))
        if sizes[0][0] > _MAX_MESSAGES or sizes[1][0] > _MAX_PARTS or source_bytes > _MAX_BYTES:
            raise ValueError("OpenCode session exceeds transcript bounds")
        m_cols = "id, type, time_created, data" if v2 else "id, '' AS type, time_created, data"
        m_order = "seq, time_created, id" if v2 else "time_created, id"
        messages = conn.execute(
            f"SELECT {m_cols} FROM {mtbl} WHERE session_id = ? ORDER BY {m_order}",  # noqa: S608
            (session_id,),
        ).fetchall()
        p_cols = "message_id, type, data" if v2 else "message_id, '' AS type, data"
        p_order = "message_id, ordinal, time_created" if v2 else "time_created, id"
        parts = conn.execute(
            f"SELECT {p_cols} FROM {ptbl} WHERE session_id = ? ORDER BY {p_order}",  # noqa: S608
            (session_id,),
        ).fetchall()
    return _OpenCodeSnapshot(
        session_id, resolve_cwd(raw_dir or cwd), raw_parent or "", forked, sess_created, source_bytes, messages, parts
    )


def _decode_opencode_parts(
    part_rows: Sequence[sqlite3.Row],
) -> tuple[dict[str, list[str]], list[tuple[str, str, str]], int]:
    malformed = 0
    parts_by_msg: dict[str, list[str]] = {}
    raw_parts_fp: list[tuple[str, str, str]] = []
    for prow in part_rows:
        mid, ptype_col, raw_pdata = sqlite_text(prow["message_id"]), sqlite_text(prow["type"]), prow["data"]
        raw_parts_fp.append((mid, ptype_col, sqlite_text(raw_pdata)))
        if not isinstance(raw_pdata, str):
            malformed += 1
            continue
        try:
            pdata = json.loads(raw_pdata)
        except ValueError, RecursionError:
            malformed += 1
            continue
        if not isinstance(pdata, dict):
            malformed += 1
            continue
        ptype = ptype_col or (pdata.get("type") if isinstance(pdata.get("type"), str) else "")
        if ptype == "text" and not pdata.get("synthetic") and not pdata.get("ignored"):
            text = pdata.get("text")
            if isinstance(text, str) and text:
                parts_by_msg.setdefault(mid, []).append(text)
    return parts_by_msg, raw_parts_fp, malformed


@dataclass(slots=True)
class _OpenCodeUsageAcc:
    samples: list[UsageRecord]
    usage_error: Exception | None = None
    total_cost: float = 0.0
    all_costs: bool = True
    unmeasured: bool = False


def _collect_opencode_assistant_usage(
    mdata: Mapping[str, Any], mcreated: object, session_id: str, cwd: str, acc: _OpenCodeUsageAcc
) -> None:
    if mdata.get("tokens") is None:
        acc.unmeasured = True
        return
    try:
        sample, scost = _opencode_sample(mdata, mcreated, session_id, cwd)
    except ValueError as error:
        acc.usage_error = error
        return
    acc.samples.append(sample)
    if scost is None:
        acc.all_costs = False
    else:
        acc.total_cost += scost


def parse_opencode_session(path: Path, session_id: str, cwd: str = "") -> ParsedSession:
    if not is_valid_session_id(session_id):
        raise ValueError(f"invalid OpenCode session id {session_id!r}")
    mtime = db_mtime(path)
    snap = _load_opencode_snapshot(path, session_id, cwd)
    parts_by_msg, raw_parts_fp, malformed = _decode_opencode_parts(snap.parts)
    logs, acc, decoded = [], _OpenCodeUsageAcc([]), 0
    raw_msgs_fp: list[tuple[str, str, int | str, str]] = []
    for mrow in snap.messages:
        mid, mtype_col = sqlite_text(mrow["id"]), sqlite_text(mrow["type"])
        mcreated, raw_mdata = mrow["time_created"], mrow["data"]
        raw_msgs_fp.append(
            (mid, mtype_col, mcreated if type(mcreated) is int else sqlite_text(mcreated), sqlite_text(raw_mdata))
        )
        if snap.forked:
            if type(mcreated) is not int:
                acc.usage_error = ValueError("forked OpenCode message missing integer time_created")
                continue
            if type(snap.sess_created) is int and mcreated < snap.sess_created:
                continue
        if not isinstance(raw_mdata, str):
            malformed += 1
            continue
        try:
            mdata = json.loads(raw_mdata)
        except ValueError, RecursionError:
            malformed += 1
            continue
        if not isinstance(mdata, dict):
            malformed += 1
            continue
        decoded += 1
        role = mtype_col or (mdata.get("role") if isinstance(mdata.get("role"), str) else "")
        if role == "assistant":
            _collect_opencode_assistant_usage(mdata, mcreated, session_id, snap.cwd, acc)
        if role not in {"user", "assistant"} or mdata.get("summary") is True:
            continue
        content = "\n".join(parts_by_msg.get(mid, ())) or text_blocks(mdata.get("content"))
        if content.strip():
            ts = _opencode_time(mcreated) if type(mcreated) is int and 0 <= mcreated <= _MAX_EPOCH_MS else ""
            logs.append(SessionLog(ts, "opencode", session_id, role, content, snap.cwd, _opencode_model(mdata)))
    propagate_models(logs)
    usage = UsageRecord(
        harness="opencode", agent="opencode", session_id=session_id, cwd=snap.cwd, source_bytes=snap.source_bytes
    )
    usage_error = acc.usage_error
    parsed_usage: UsageRecord | None = None
    if acc.samples and not acc.unmeasured and all(s.measurement_kind for s in acc.samples):
        apply_samples(usage, acc.samples, timed=True)
        if acc.all_costs:
            usage.cost_usd, usage.cost_known = acc.total_cost, True
        parsed_usage, usage_error = finalize_usage(usage, usage_error, logs, mtime)
    fp = fingerprint_json(
        {
            "cwd": snap.cwd,
            "parent_id": snap.parent_id,
            "fork_created": snap.sess_created if snap.forked else None,
            "messages": raw_msgs_fp,
            "parts": raw_parts_fp,
        }
    )
    return ParsedSession(
        logs,
        fp,
        "opencode-db",
        malformed,
        max(0, decoded - len(logs)),
        parsed_usage,
        usage_error,
        sidechain=bool(snap.parent_id),
        parent_session_id=snap.parent_id,
    )
