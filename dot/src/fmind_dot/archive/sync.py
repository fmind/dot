"""Incremental agent session synchronization."""

from __future__ import annotations

import json
import re
import sqlite3
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Literal

from fmind_dot.archive.parsers import AGENT_ADAPTERS, AgentAdapter, claude_parent_session_id
from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionManifest,
    SessionSource,
    agent_bundle_paths,
    format_utc_z,
    ingest_session,
    read_session_manifest,
    session_store_root,
)
from fmind_dot.archive.usage import RETIRED_AGENTS
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import private_directory, write_private_file
from fmind_dot.state import State

SYNC_STATE_NAME = ".sync.json"
SYNC_STATE_SCHEMA = "dot.agent.session.sync-state/v1"
FAILURE_DETAIL_LIMIT = 512
_UUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
_SESSION_ERRORS = (OSError, ValueError, TypeError, sqlite3.Error, DotError)
AGENT_SOURCES = {
    "agy": "~/.gemini/antigravity-cli/brain",
    "claude": "~/.claude/projects",
    "copilot": "~/.copilot/session-store.db",
    "opencode": "~/.local/share/opencode/opencode.db",
    "pi": "~/.pi/agent/sessions",
}


@dataclass(slots=True)
class SyncOutcome:
    selected: int = 0
    ingested: int = 0
    unchanged: int = 0
    retained: int = 0
    retained_current_transcripts: int = 0
    skipped: int = 0
    failed: int = 0


def source_root(agent: str) -> Path:
    if not (source := AGENT_SOURCES.get(agent)):
        raise DotError(f"missing configured source for agent {agent!r}")
    return expand_path(source)


def _sig(path: Path, *, ignore_empty: bool = False) -> str:
    try:
        info = path.stat()
    except FileNotFoundError:
        return ""
    if ignore_empty and info.st_size == 0:
        return ""
    return f"{info.st_size}:{info.st_mtime_ns}"


def _db_sig(path: Path) -> str:
    resolved = path.resolve()
    # Read-only opens on WAL-mode DBs create a 0-byte -wal sidecar; treat empty WALs as absent so checkpoints hold.
    return f"{resolved}:{_sig(resolved)},{_sig(resolved.with_name(f'{resolved.name}-wal'), ignore_empty=True)}"


@dataclass(frozen=True, slots=True)
class SyncState:
    synced_at: str
    failed: int
    retained: int
    current: bool
    database_signature: str = ""


def read_sync_state(root: Path, agent: str) -> SyncState | Literal["never", "unreadable"]:
    try:
        doc = json.loads((root / agent / SYNC_STATE_NAME).read_bytes())
    except FileNotFoundError:
        return "never"
    except OSError, ValueError, RecursionError:
        return "unreadable"
    if not isinstance(doc, dict) or doc.get("schema") != SYNC_STATE_SCHEMA:
        return "unreadable"
    synced_at, failed, retained = doc.get("synced_at"), doc.get("failed"), doc.get("retained", 0)
    if not isinstance(synced_at, str) or any(type(v) is not int or v < 0 for v in (failed, retained)):
        return "unreadable"
    try:
        if datetime.fromisoformat(synced_at).tzinfo is None:
            return "unreadable"
    except ValueError:
        return "unreadable"
    db_sig = doc.get("database_signature", "")
    return SyncState(
        synced_at,
        failed,
        retained,
        doc.get("parser_version") == SESSION_PARSER_VERSION,
        db_sig if isinstance(db_sig, str) else "",
    )


def _stored_manifests(root: Path, adapter: AgentAdapter) -> dict[str, SessionManifest]:
    stored: dict[str, SessionManifest] = {}
    try:
        paths = agent_bundle_paths(root / adapter.name)
    except FileNotFoundError:
        return stored
    for path in paths:
        try:
            m = read_session_manifest(path, usage=False)
            stored[m.session_id] = m
        except OSError, ValueError:
            continue
    return stored


def _record_sync_failure(
    state: State, outcome: SyncOutcome, adapter: AgentAdapter, op: str, error: BaseException, sid: str = ""
) -> None:
    outcome.failed += 1
    state.stderr.write(f"agent-session: failed to {op} for {adapter.label}: {bounded_failure(error, sid)}\n")


def _source_path(state: State, outcome: SyncOutcome, adapter: AgentAdapter) -> Path | None:
    source = source_root(adapter.name)
    try:
        mode = source.stat().st_mode
        if adapter.database:
            if stat.S_ISDIR(mode):
                raise DotError(f"{adapter.label} database path is a directory: {source}")
            if not stat.S_ISREG(mode):
                raise DotError(f"{adapter.label} database path is not a regular file: {source}")
        elif not stat.S_ISDIR(mode):
            raise DotError(f"{adapter.label} session path is not a directory: {source}")
        return source
    except FileNotFoundError:
        return None
    except (OSError, DotError) as error:
        msg = f"failed to inspect {adapter.label} session source {source}: {error}"
        _record_sync_failure(
            state,
            outcome,
            adapter,
            "inspect the session source",
            error if isinstance(error, DotError) else DotError(msg),
        )
        return None


def _session_sig_and_unchanged(
    adapter: AgentAdapter,
    path: Path,
    source_cwd: str,
    prev: SessionManifest | None,
    db_sig: str,
    checkpoint: str,
) -> tuple[str, str, bool]:
    sig = "" if adapter.database else _sig(path)
    prev_sig = prev.source_signature if prev else ""
    stored_sig = (
        f"{sig};cwd={source_cwd}"
        if adapter.external_cwd and sig and source_cwd
        else (prev_sig if adapter.external_cwd and sig and prev_sig.startswith(f"{sig};cwd=") else sig)
    )
    unchanged = (
        bool(prev_sig) and bool(db_sig) and db_sig == checkpoint
        if adapter.database
        else bool(sig) and prev_sig == stored_sig
    )
    return sig, stored_sig, unchanged


def _write_sync_state(
    state: State,
    outcome: SyncOutcome,
    root: Path,
    adapter: AgentAdapter,
    source: Path,
    db_sig: str,
    agent_failed: int,
    counts: SyncOutcome,
) -> None:
    try:
        saved_db_sig = (
            db_sig
            if adapter.database and db_sig and not agent_failed and not counts.retained and _db_sig(source) == db_sig
            else ""
        )
        doc: dict[str, object] = {
            "schema": SYNC_STATE_SCHEMA,
            "synced_at": format_utc_z(seconds=True),
            "failed": agent_failed,
            "retained": counts.retained,
            "parser_version": SESSION_PARSER_VERSION,
        }
        if saved_db_sig:
            doc["database_signature"] = saved_db_sig
        dest = private_directory(private_directory(root) / adapter.name) / SYNC_STATE_NAME
        write_private_file(dest, (json.dumps(doc) + "\n").encode())
    except OSError as error:
        _record_sync_failure(state, outcome, adapter, "record sync state", error)


def _sync_agent(state: State, outcome: SyncOutcome, root: Path, adapter: AgentAdapter) -> None:
    if (source := _source_path(state, outcome, adapter)) is None:
        return
    failed_before, last = outcome.failed, read_sync_state(root, adapter.name)
    announced = isinstance(last, SyncState) and last.current
    db_sig = ""
    checkpoint = ""
    try:
        if adapter.database:
            db_sig = _db_sig(source)
            checkpoint = (
                last.database_signature
                if isinstance(last, SyncState) and last.current and not last.failed and not last.retained
                else ""
            )
        candidates = adapter.enumerate(source)
    except _SESSION_ERRORS as error:
        _record_sync_failure(state, outcome, adapter, "scan sessions", error)
        candidates = []
    try:
        stored = _stored_manifests(root, adapter)
    except _SESSION_ERRORS as error:
        _record_sync_failure(state, outcome, adapter, "inspect the session archive", error)
        return
    if adapter.name == "claude":
        owners = {s: m.parent_session_id for s, m in stored.items() if m.parent_session_id}
        candidates = [
            (f"{s}-{p}" if (p := claude_parent_session_id(p_)) and owners.setdefault(s, p) != p else s, c, p_)
            for s, c, p_ in candidates
        ]
    counts = SyncOutcome()
    for sid, source_cwd, path in candidates:
        try:
            prev = stored.get(sid)
            sig, stored_sig, unchanged = _session_sig_and_unchanged(adapter, path, source_cwd, prev, db_sig, checkpoint)
            if prev and prev.parser_version == SESSION_PARSER_VERSION and unchanged:
                counts.unchanged += 1
                continue
            if prev and prev.parser_version != SESSION_PARSER_VERSION and not announced:
                announced = True
                msg = f"agent-session: upgrading archived {adapter.name} sessions to parser {SESSION_PARSER_VERSION}; this can take minutes\n"
                state.stderr.write(msg)
            parse_cwd = source_cwd or (prev.cwd if adapter.external_cwd and prev else "")
            parsed = adapter.parser(path, sid, parse_cwd)
            if not adapter.database and _sig(path) != sig:
                raise DotError("session source changed during capture; retry sync")
            counts.selected += 1
            ok = parsed.usage_error is None and not parsed.malformed
            src = SessionSource(
                parsed.source_type,
                parsed.fingerprint,
                (parsed.fingerprint if adapter.database else stored_sig) if ok else "",
                parsed.malformed,
                parsed.skipped,
                parsed.sidechain,
                parsed.parent_session_id,
            )
            usage_doc = parsed.usage.to_dict() if ok and parsed.usage is not None else None
            result = ingest_session(adapter.name, sid, parsed.logs, src, usage=usage_doc)
            stored[sid] = replace(result.manifest, usage=None)
            setattr(counts, result.status, getattr(counts, result.status) + 1)
            counts.retained_current_transcripts += result.status == "retained" and result.current_transcript
            if result.status == "retained":
                m = result.manifest
                note = f"agent-session: {result.status} {m.agent} records={m.record_count} malformed={m.malformed_records} skipped={m.skipped_records} completeness={m.completeness}\n"
                state.stderr.write(note)
            if not ok:
                cause = "usage extraction failed" if parsed.usage_error is not None else "malformed source records"
                tail = (
                    "kept the archived usage"
                    if result.manifest.usage is not None
                    else "archived the transcript without usage"
                )
                _record_sync_failure(state, outcome, adapter, "capture session", DotError(f"{cause}; {tail}"), sid)
        except _SESSION_ERRORS as error:
            _record_sync_failure(state, outcome, adapter, "capture session", error, sid)
    for name in ("selected", "ingested", "unchanged", "retained", "retained_current_transcripts", "skipped"):
        setattr(outcome, name, getattr(outcome, name) + getattr(counts, name))
    _write_sync_state(state, outcome, root, adapter, source, db_sig, outcome.failed - failed_before, counts)


def sync_sessions(state: State, *, agent: str = "") -> SyncOutcome:
    """Capture changed live-agent sessions incrementally, reporting warnings/failures to stderr."""
    if agent in RETIRED_AGENTS:
        raise DotError(f"{agent} is retired: its archived sessions stay queryable, but dot no longer captures them")
    if agent and agent not in AGENT_ADAPTERS:
        raise DotError(f"unknown session agent {agent!r}")
    root, outcome = session_store_root(), SyncOutcome()
    for adapter in AGENT_ADAPTERS.values():
        if not agent or adapter.name == agent:
            _sync_agent(state, outcome, root, adapter)
    return outcome


def bounded_failure(error: BaseException, session_id: str = "") -> str:
    detail = str(error).replace(session_id, "<session>") if session_id else str(error)
    return " ".join(_UUID.sub("<session>", detail).split())[:FAILURE_DETAIL_LIMIT]
