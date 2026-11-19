"""OpenCode SQLite session discovery, per-session change stamps, transcript parsing, and usage extraction."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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
    apply_counters,
    apply_samples,
    combine_row_hashes,
    connect_read_only,
    db_mtime,
    finalize_usage,
    hash_stamp,
    mapping,
    register_row_hash,
    resolve_cwd,
    sqlite_columns,
    sqlite_tables,
    sqlite_text,
    text_blocks,
)
from fmind_dot.archive.store import (
    SessionLog,
    fingerprint_json,
    format_utc_z,
    is_valid_session_id,
    propagate_models,
)
from fmind_dot.archive.usage import UsageRecord, check_cost

_MAX_EPOCH_MS = 253_402_300_799_000
_OPENCODE_MSG_STAMP_COLS = ("id", "type", "seq", "time_created", "data")
_OPENCODE_PART_STAMP_COLS = ("id", "message_id", "type", "ordinal", "time_created", "data")


def _opencode_session_stamp(
    v2: bool,
    raw_dir: object,
    raw_parent: object,
    raw_fork: object,
    sess_created: object,
    msg_hash: str,
    part_hash: str,
) -> str:
    return hash_stamp("oc", (int(v2), raw_dir, raw_parent, raw_fork, sess_created, msg_hash, part_hash))


def _opencode_table_stamps(
    conn: sqlite3.Connection, tables: set[str], table: str, stamp_cols: Sequence[str]
) -> dict[str, str] | None:
    if table not in tables:
        return {}
    cols = sqlite_columns(conn, table)
    if "session_id" not in cols:
        return None
    exprs = ", ".join(c if c in cols else "NULL" for c in stamp_cols)
    try:
        rows = conn.execute(
            f"SELECT session_id, dot_row_hash({exprs}) FROM {table} GROUP BY session_id"  # noqa: S608
        ).fetchall()
    except sqlite3.Error:
        return None
    return {row[0]: str(row[1] or "") for row in rows if isinstance(row[0], str)}


def enumerate_opencode(root: Path) -> list[SessionCandidate]:
    """List OpenCode sessions using a lightweight session-table-only query."""
    with connect_read_only(root) as conn:
        tables = sqlite_tables(conn)
        stbl = "session_v2" if "session_v2" in tables else ("session" if "session" in tables else "")
        if not stbl:
            return []
        rows = conn.execute(f"SELECT id, directory FROM {stbl} ORDER BY id LIMIT ?", (SESSIONS_LIMIT + 1,)).fetchall()  # noqa: S608
    if len(rows) > SESSIONS_LIMIT:
        raise ValueError(f"OpenCode sessions exceed {SESSIONS_LIMIT}")
    return [
        (sid, row[1] if isinstance(row[1], str) else "", root)
        for row in rows
        if isinstance(sid := row[0], str) and is_valid_session_id(sid)
    ]


def enumerate_opencode_stamped(root: Path) -> list[StampedSessionCandidate]:
    """List OpenCode sessions with content-sensitive, type-tagged per-session change stamps."""
    with connect_read_only(root) as conn:
        register_row_hash(conn)
        conn.execute("BEGIN")
        tables = sqlite_tables(conn)
        v2 = "session_v2" in tables
        if not v2 and "session" not in tables:
            return []
        stbl, mtbl, ptbl = ("session_v2", "session_message", "session_part") if v2 else ("session", "message", "part")
        scols = sqlite_columns(conn, stbl)
        opt_cols = [c for c in ("parent_id", "fork_session_id", "time_created") if c in scols]
        sel = ", ".join(["id", "directory", *opt_cols])
        rows = conn.execute(f"SELECT {sel} FROM {stbl} ORDER BY id LIMIT ?", (SESSIONS_LIMIT + 1,)).fetchall()  # noqa: S608
        if len(rows) > SESSIONS_LIMIT:
            raise ValueError(f"OpenCode sessions exceed {SESSIONS_LIMIT}")
        msg_stamps = _opencode_table_stamps(conn, tables, mtbl, _OPENCODE_MSG_STAMP_COLS)
        part_stamps = _opencode_table_stamps(conn, tables, ptbl, _OPENCODE_PART_STAMP_COLS)
    out: list[StampedSessionCandidate] = []
    for row in rows:
        sid = row["id"]
        if not isinstance(sid, str) or not is_valid_session_id(sid):
            continue
        directory = row["directory"] if isinstance(row["directory"], str) else ""
        stamp = (
            ""
            if msg_stamps is None or part_stamps is None
            else _opencode_session_stamp(
                v2,
                row["directory"],
                row["parent_id"] if "parent_id" in scols else None,
                row["fork_session_id"] if "fork_session_id" in scols else None,
                row["time_created"] if "time_created" in scols else None,
                msg_stamps.get(sid, ""),
                part_stamps.get(sid, ""),
            )
        )
        out.append((sid, directory, root, stamp))
    return out


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
    session_stamp: str


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
        raw_fork = srow["fork_session_id"] if "fork_session_id" in scols else None
        forked = bool(raw_fork)
        sess_created = srow["time_created"] if "time_created" in scols else None
        if forked and (type(sess_created) is not int or sess_created < 0):
            raise ValueError("forked OpenCode session requires valid time_created")
        sizes = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM {mtbl} WHERE session_id = ? "  # noqa: S608
            f"UNION ALL SELECT COUNT(*), COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM {ptbl} WHERE session_id = ?",
            (session_id, session_id),
        ).fetchall()
        source_bytes = int(sum(r[1] for r in sizes))
        if sizes[0][0] > MAX_MESSAGES or sizes[1][0] > MAX_PARTS or source_bytes > MAX_BYTES:
            raise ValueError("OpenCode session exceeds transcript bounds")
        mcols = sqlite_columns(conn, mtbl)
        m_cols = ", ".join(c if c in mcols else f"NULL AS {c}" for c in _OPENCODE_MSG_STAMP_COLS)
        m_order = "seq, time_created, id" if v2 else "time_created, id"
        messages = conn.execute(
            f"SELECT {m_cols} FROM {mtbl} WHERE session_id = ? ORDER BY {m_order}",  # noqa: S608
            (session_id,),
        ).fetchall()
        pcols = sqlite_columns(conn, ptbl)
        p_cols = ", ".join(c if c in pcols else f"NULL AS {c}" for c in _OPENCODE_PART_STAMP_COLS)
        p_order = "message_id, ordinal, time_created" if v2 else "time_created, id"
        parts = conn.execute(
            f"SELECT {p_cols} FROM {ptbl} WHERE session_id = ? ORDER BY {p_order}",  # noqa: S608
            (session_id,),
        ).fetchall()
    msg_hash = combine_row_hashes(tuple(row[c] for c in _OPENCODE_MSG_STAMP_COLS) for row in messages)
    part_hash = combine_row_hashes(tuple(row[c] for c in _OPENCODE_PART_STAMP_COLS) for row in parts)
    session_stamp = _opencode_session_stamp(v2, raw_dir, raw_parent, raw_fork, sess_created, msg_hash, part_hash)
    return _OpenCodeSnapshot(
        session_id,
        resolve_cwd(raw_dir or cwd),
        raw_parent or "",
        forked,
        sess_created,
        source_bytes,
        messages,
        parts,
        session_stamp,
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
        session_stamp=snap.session_stamp,
    )
