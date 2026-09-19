"""Incremental capture of agent sessions from their native stores."""

import json
import re
import sqlite3
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    GROK_TRANSCRIPT_NAME,
    AgentAdapter,
    ParsedSession,
    agent_adapters,
    enumerate_sessions,
    resolve_cwd,
)
from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionIngestionResult,
    SessionSource,
    ensure_session_store,
    ingest_session,
    read_session_manifest,
    report_ingestion,
    session_store_root,
)
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import private_directory, write_private_file
from fmind_dot.state import State

SYNC_SCHEMA = "dot.agent.session.sync/v2"
SYNC_STATE_NAME = ".sync.json"
SYNC_STATE_SCHEMA = "dot.agent.session.sync-state/v1"
FAILURE_DETAIL_LIMIT = 512
_UUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
_SESSION_ERRORS = (OSError, ValueError, TypeError, sqlite3.Error, DotError)


@dataclass
class SyncOutcome:
    """Session counts: parsed (selected) sources publish as ingested, unchanged, retained, or skipped."""

    selected: int = 0
    ingested: int = 0
    unchanged: int = 0
    retained: int = 0
    skipped: int = 0
    failed: int = 0


def source_root(state: State, agent: str) -> Path:
    source = state.config.agent.sources.get(agent)
    if not source:
        raise DotError(f"missing configured source for agent {agent!r}")
    return expand_path(source)


def _validated_source_root(state: State, adapter: AgentAdapter) -> Path | None:
    root = source_root(state, adapter.name)
    try:
        mode = root.stat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        raise DotError(f"failed to inspect {adapter.label} session source {root}: {error}") from error
    if adapter.database:
        if stat.S_ISDIR(mode):
            raise DotError(f"{adapter.label} database path is a directory: {root}")
        if not stat.S_ISREG(mode):
            raise DotError(f"{adapter.label} database path is not a regular file: {root}")
    elif not stat.S_ISDIR(mode):
        raise DotError(f"{adapter.label} session path is not a directory: {root}")
    return root


def _source_files(adapter: AgentAdapter, path: Path) -> list[Path]:
    """Name every file whose change can change the parse."""
    if adapter.name == "grok":
        return [path.parent / GROK_TRANSCRIPT_NAME, path.parent / "signals.json"]
    if adapter.database:
        # SQLite write-ahead logging can commit rows without touching the main file.
        return [path, path.with_name(f"{path.name}-wal")]
    return [path]


def _source_signature(files: list[Path]) -> tuple[str, float]:
    """Return size/mtime evidence and the newest modification time of the source files."""
    parts: list[str] = []
    modified = 0.0
    for file in files:
        try:
            info = file.stat()
        except FileNotFoundError:
            parts.append("-")
            continue
        parts.append(f"{info.st_size}:{info.st_mtime_ns}")
        modified = max(modified, info.st_mtime)
    return ",".join(parts), modified


def _stored_sources(root: Path, agent: str) -> dict[str, tuple[str, str, str]]:
    """Map session ids to stored parser version, source signature, and CWD."""
    stored: dict[str, tuple[str, str, str]] = {}
    directory = root / agent
    if not directory.is_dir():
        return stored
    for path in directory.glob("*.jsonl"):
        try:
            manifest = read_session_manifest(path)
        except OSError, ValueError:
            # Publication reports the unreadable bundle for this session instead of skipping it.
            continue
        stored[manifest.session_id] = (manifest.parser_version, manifest.source_signature, manifest.cwd)
    return stored


def _capture(
    adapter: AgentAdapter, session_id: str, parsed: ParsedSession, signature: str
) -> tuple[SessionIngestionResult | None, DotError | None]:
    """Publish one parse; a usage extraction failure never replaces the archived copy."""
    source = SessionSource(
        type=parsed.source_type,
        fingerprint=parsed.fingerprint,
        signature=signature,
        malformed=parsed.malformed,
        skipped=parsed.skipped,
    )
    if parsed.usage_error is None:
        usage = parsed.usage.to_dict() if parsed.usage is not None else None
        return ingest_session(adapter.name, session_id, parsed.logs, source, usage=usage), None
    # Provider metric errors can quote source values: report the outcome, not the detail.
    # If nothing is archived, keep the transcript without usage. Check under the publication
    # lock; an empty signature makes the next sync retry rather than skip this source.
    source.signature = ""
    result = ingest_session(adapter.name, session_id, parsed.logs, source, preserve_existing=True)
    if result.status == "retained":
        return None, DotError("usage extraction failed; kept the archived copy and its usage")
    return result, DotError("usage extraction failed; archived the transcript without usage")


def _write_sync_state(root: Path, agent: str, failed: int) -> None:
    document = {
        "schema": SYNC_STATE_SCHEMA,
        "synced_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "failed": failed,
    }
    directory = private_directory(private_directory(root) / agent)
    write_private_file(directory / SYNC_STATE_NAME, (json.dumps(document) + "\n").encode())


def sync_sessions(
    state: State,
    *,
    agent: str = "",
    session: str = "",
    cwd: str = "",
    since: datetime | None = None,
    dry_run: bool = False,
    as_json: bool = False,
    quiet: bool = False,
) -> SyncOutcome:
    """Capture changed sessions; quiet mode reports only failures and never raises for them."""
    if agent and agent not in AGENT_ADAPTERS:
        raise DotError(f"unknown session agent {agent!r}")
    root = session_store_root() if dry_run else ensure_session_store(state.stderr)
    outcome = SyncOutcome()
    # Only an unfiltered pass proves every available session of an agent was considered.
    complete_pass = not (session or cwd or since or dry_run)

    def fail(adapter: AgentAdapter, operation: str, error: BaseException, session_id: str = "") -> None:
        outcome.failed += 1
        detail = bounded_failure(error, session_id)
        state.stderr.write(f"agent-session: failed to {operation} for {adapter.label}: {detail}\n")

    for adapter in agent_adapters():
        if agent and adapter.name != agent:
            continue
        failed_before = outcome.failed
        try:
            source = _validated_source_root(state, adapter)
        except DotError as error:
            if not quiet:
                raise
            fail(adapter, "inspect the session source", error)
            continue
        if source is None:
            continue
        try:
            candidates = enumerate_sessions(source, adapter.name)
        except _SESSION_ERRORS as error:
            # One unreadable store must not block the adapters after it.
            fail(adapter, "scan sessions", error)
            continue
        stored = _stored_sources(root, adapter.name)
        counts = SyncOutcome()
        for session_id, source_cwd, path in candidates:
            if session and session_id != session:
                continue
            try:
                signature, modified = _source_signature(_source_files(adapter, path))
                if since and datetime.fromtimestamp(modified, UTC) < since:
                    continue
                previous = stored.get(session_id)
                if previous and signature and previous[:2] == (SESSION_PARSER_VERSION, signature):
                    if not cwd or previous[2] == cwd:
                        counts.unchanged += 1
                    continue
                parsed = adapter.parser(path, session_id, source_cwd)
                parsed_cwd = next((record.cwd for record in parsed.logs if record.cwd), source_cwd)
                if cwd and resolve_cwd(parsed_cwd) != cwd:
                    continue
                counts.selected += 1
                if dry_run:
                    continue
                result, failure = _capture(adapter, session_id, parsed, signature)
            except _SESSION_ERRORS as error:
                # One malformed session must not block the sessions and adapters after it.
                fail(adapter, "capture session", error, session_id)
                continue
            if result is not None:
                setattr(counts, result.status, getattr(counts, result.status) + 1)
                if not quiet and result.status in {"ingested", "retained"}:
                    state.stderr.write(report_ingestion(result) + "\n")
            if failure is not None:
                fail(adapter, "capture session", failure, session_id)
        for name in ("selected", "ingested", "unchanged", "retained", "skipped"):
            setattr(outcome, name, getattr(outcome, name) + getattr(counts, name))
        if not quiet:
            verb = "selected" if dry_run else "ingested"
            state.stderr.write(
                f"{adapter.name}: {getattr(counts, verb)} {verb}, {counts.unchanged} unchanged, "
                f"{counts.retained} retained\n"
            )
        if complete_pass:
            try:
                _write_sync_state(root, adapter.name, outcome.failed - failed_before)
            except OSError as error:
                fail(adapter, "record sync state", error)
    if not quiet:
        state.stderr.write(f"agent-session-sync: done ({outcome.failed} failed)\n")
    if as_json:
        document = {"schema": SYNC_SCHEMA, "parser_version": SESSION_PARSER_VERSION, "dry_run": dry_run}
        state.stdout.write(json.dumps(document | asdict(outcome)) + "\n")
    if outcome.failed and not quiet:
        raise DotError(f"session sync recorded {outcome.failed} failure(s); see errors above")
    return outcome


def bounded_failure(error: BaseException, session_id: str = "", limit: int = FAILURE_DETAIL_LIMIT) -> str:
    """Keep failure text short and free of session identities."""
    detail = str(error).replace(session_id, "<session>") if session_id else str(error)
    detail = _UUID.sub("<session>", detail)
    return " ".join(detail.split())[:limit]
