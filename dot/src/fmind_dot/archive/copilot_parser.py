"""Copilot SQLite session discovery, per-session change stamps, transcript parsing, and usage extraction."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from fmind_dot.archive.common import (
    MAX_BYTES,
    MAX_MESSAGES,
    MAX_PARTS,
    SESSIONS_LIMIT,
    ParsedSession,
    SessionCandidate,
    StampedSessionCandidate,
    apply_samples,
    combine_row_hashes,
    connect_read_only,
    db_mtime,
    hash_stamp,
    latest_ts,
    register_row_hash,
    resolve_cwd,
    sqlite_columns,
    sqlite_tables,
    sqlite_text,
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
from fmind_dot.archive.usage import UsageRecord

# Providers whose raw input_tokens column includes cached prompt tokens when token_details_json is absent.
_CACHE_INCLUSIVE_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4", "openai/", "gemini-", "google/", "grok-", "x-ai/")
_COPILOT_TURN_REQ_COLS = ("session_id", "turn_index", "user_message", "assistant_response", "timestamp")
_COPILOT_USAGE_BASE_COLS = (
    "model",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
)
_COPILOT_USAGE_OPT_COLS = ("id", "turn_index", "token_details_json", "created_at")
_COPILOT_USAGE_STAMP_COLS = (*_COPILOT_USAGE_OPT_COLS, *_COPILOT_USAGE_BASE_COLS)


def _copilot_session_stamp(raw_cwd: object, raw_created: object, turn_hash: str, usage_hash: str) -> str:
    return hash_stamp("cop", (raw_cwd, raw_created, turn_hash, usage_hash))


def _copilot_turn_stamps(conn: sqlite3.Connection, tables: set[str]) -> dict[str, str] | None:
    if "turns" not in tables:
        return {}
    cols = sqlite_columns(conn, "turns")
    if not set(_COPILOT_TURN_REQ_COLS) <= cols:
        return None
    id_expr = "id" if "id" in cols else "NULL"
    try:
        rows = conn.execute(
            f"SELECT session_id, dot_row_hash({id_expr}, turn_index, user_message, assistant_response, timestamp) "  # noqa: S608
            "FROM turns GROUP BY session_id"
        ).fetchall()
    except sqlite3.Error:
        return None
    return {row[0]: str(row[1] or "") for row in rows if isinstance(row[0], str)}


def _copilot_usage_stamps(conn: sqlite3.Connection, tables: set[str]) -> dict[str, str] | None:
    if "assistant_usage_events" not in tables:
        return {}
    cols = sqlite_columns(conn, "assistant_usage_events")
    if not {"session_id", *_COPILOT_USAGE_BASE_COLS} <= cols:
        return None
    exprs = ", ".join(c if c in cols else "NULL" for c in _COPILOT_USAGE_STAMP_COLS)
    try:
        rows = conn.execute(
            f"SELECT session_id, dot_row_hash({exprs}) FROM assistant_usage_events GROUP BY session_id"  # noqa: S608
        ).fetchall()
    except sqlite3.Error:
        return None
    return {row[0]: str(row[1] or "") for row in rows if isinstance(row[0], str)}


def enumerate_copilot(root: Path) -> list[SessionCandidate]:
    """List Copilot sessions using a lightweight sessions-only query."""
    with connect_read_only(root) as conn:
        if "sessions" not in sqlite_tables(conn):
            return []
        rows = conn.execute("SELECT id, cwd FROM sessions ORDER BY id LIMIT ?", (SESSIONS_LIMIT + 1,)).fetchall()
    if len(rows) > SESSIONS_LIMIT:
        raise ValueError(f"Copilot sessions exceed {SESSIONS_LIMIT}")
    return [
        (sid, row[1] if isinstance(row[1], str) else "", root)
        for row in rows
        if isinstance(sid := row[0], str) and is_valid_session_id(sid)
    ]


def enumerate_copilot_stamped(root: Path) -> list[StampedSessionCandidate]:
    """List Copilot sessions with content-sensitive, type-tagged per-session change stamps."""
    with connect_read_only(root) as conn:
        register_row_hash(conn)
        conn.execute("BEGIN")
        tables = sqlite_tables(conn)
        if "sessions" not in tables:
            return []
        scols = sqlite_columns(conn, "sessions")
        created_col = "created_at" if "created_at" in scols else "NULL AS created_at"
        rows = conn.execute(
            f"SELECT id, cwd, {created_col} FROM sessions ORDER BY id LIMIT ?",  # noqa: S608
            (SESSIONS_LIMIT + 1,),
        ).fetchall()
        if len(rows) > SESSIONS_LIMIT:
            raise ValueError(f"Copilot sessions exceed {SESSIONS_LIMIT}")
        turn_stamps = _copilot_turn_stamps(conn, tables)
        usage_stamps = _copilot_usage_stamps(conn, tables)
    out: list[StampedSessionCandidate] = []
    for row in rows:
        sid = row[0]
        if not isinstance(sid, str) or not is_valid_session_id(sid):
            continue
        cwd = row[1] if isinstance(row[1], str) else ""
        stamp = (
            ""
            if turn_stamps is None or usage_stamps is None
            else _copilot_session_stamp(row[1], row[2], turn_stamps.get(sid, ""), usage_stamps.get(sid, ""))
        )
        out.append((sid, cwd, root, stamp))
    return out


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
    if model.lower().startswith(_CACHE_INCLUSIVE_MODEL_PREFIXES):
        uncached = raw_input - cache_read - cache_write
        if uncached < 0:
            raise ValueError("Copilot cache-inclusive input_tokens smaller than cached prompt tokens")
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
    if ubounds is not None and (ubounds[0] > MAX_PARTS or ubounds[1] > MAX_BYTES):
        raise ValueError("Copilot usage events exceed bounds")
    opt_cols = [c for c in _COPILOT_USAGE_OPT_COLS if c in cols]
    select_cols = ", ".join((*_COPILOT_USAGE_BASE_COLS, *opt_cols))
    order = " ORDER BY id" if "id" in cols else ""
    rows = conn.execute(
        f"SELECT {select_cols} FROM assistant_usage_events WHERE session_id = ?{order}",  # noqa: S608
        (session_id,),
    ).fetchall()
    return rows, cols, int(ubounds[1]) if ubounds is not None else 0


def _copilot_usage_evidence(rows: Sequence[sqlite3.Row], cols: set[str]) -> list[dict[str, object]]:
    return [
        {
            "turn_index": row["turn_index"] if "turn_index" in cols and type(row["turn_index"]) is int else None,
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
        if "turn_index" in cols and type(row["turn_index"]) is int and isinstance(row["model"], str) and row["model"]
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
        model = turn_models.get(t_idx, "") if type(t_idx) is int else ""
        user_msg, asst_msg = row["user_message"], row["assistant_response"]
        evidence.append(
            {
                "session_id": sqlite_text(row["session_id"]),
                "user_message": sqlite_text(user_msg),
                "assistant_response": sqlite_text(asst_msg),
                "timestamp": sqlite_text(row["timestamp"]),
                "cwd": cwd_text,
                "turn_index": t_idx if type(t_idx) is int else sqlite_text(t_idx),
            }
        )
        ts = row["timestamp"] if isinstance(row["timestamp"], str) else ""
        for role, text in (("user", user_msg), ("assistant", asst_msg)):
            if isinstance(text, str) and text.strip():
                logs.append(SessionLog(ts, "copilot", session_id, role, text, session_cwd, model))
    propagate_models(logs)
    return evidence, logs


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
        if bounds is not None and (bounds[0] > MAX_MESSAGES or turn_bytes > MAX_BYTES):
            raise ValueError("Copilot session exceeds transcript bounds")
        tcols = sqlite_columns(conn, "turns")
        has_turn_id = "id" in tcols
        turn_id_col = "id" if has_turn_id else "NULL AS id"
        turn_order = "turn_index, id" if has_turn_id else "turn_index"
        turn_rows = conn.execute(
            f"SELECT {turn_id_col}, session_id, turn_index, user_message, assistant_response, timestamp "  # noqa: S608
            f"FROM turns WHERE session_id = ? ORDER BY {turn_order}",
            (session_id,),
        ).fetchall()
        turn_stamps = [r["timestamp"] for r in turn_rows if isinstance(r["timestamp"], str)]
        session_stamp = ""
        try:
            u_rows, u_cols, u_bytes = _fetch_copilot_usage_rows(conn, session_id)
            usage_evidence = _copilot_usage_evidence(u_rows, u_cols)
            usage, turn_models, usage_bytes = _extract_copilot_usage(
                u_rows, u_cols, u_bytes, session_id, session_cwd, turn_stamps, mtime, raw_created or ""
            )
            usage_error: Exception | None = None
            turn_hash = combine_row_hashes(
                (row["id"], row["turn_index"], row["user_message"], row["assistant_response"], row["timestamp"])
                for row in turn_rows
            )
            usage_hash = combine_row_hashes(
                tuple(row[c] if c in u_cols else None for c in _COPILOT_USAGE_STAMP_COLS) for row in u_rows
            )
            session_stamp = _copilot_session_stamp(raw_cwd, raw_created, turn_hash, usage_hash)
        except (sqlite3.Error, ValueError) as error:
            usage, turn_models, usage_bytes, usage_error = None, {}, 0, error
    evidence, logs = _build_copilot_turns(turn_rows, turn_models, session_id, session_cwd, cwd_text)
    if usage is not None:
        usage.source_bytes = turn_bytes + usage_bytes
    fp = fingerprint_json({"turns": evidence, "usage": usage_evidence})
    return ParsedSession(logs, fp, "copilot-db", usage=usage, usage_error=usage_error, session_stamp=session_stamp)
