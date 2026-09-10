"""Source snapshots and atomic session ingestion."""

import json
import re
import sqlite3
import stat
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    AgentAdapter,
    ParsedSession,
    agent_adapters,
    enumerate_sessions,
    find_transcript,
    resolve_cwd,
)
from fmind_dot.archive.store import (
    SESSION_PARSER_VERSION,
    SessionIngestionResult,
    SessionSource,
    ingest_session,
    is_valid_session_id,
    report_ingestion,
)
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.state import State
from fmind_dot.system import read_hook_payload

_UUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _source_root(state: State, agent: str) -> Path:
    source = state.config.agent.sources.get(agent)
    if not source:
        raise DotError(f"missing configured source for agent {agent!r}")
    return expand_path(source)


def _validated_source_root(state: State, adapter: AgentAdapter) -> Path | None:
    root = _source_root(state, adapter.name)
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


@dataclass(frozen=True)
class HookIdentity:
    session_id: str
    cwd: str
    transcript_path: str = ""
    from_hook: bool = False
    halt: bool = False


def resolve_hook_identity(
    state: State, session_id: str = "", cwd: str = "", *, require_idle: bool = False
) -> HookIdentity:
    raw = read_hook_payload(state.stdin)
    if raw is not None:
        stopped = raw.get("stop_hook_active") is True or raw.get("stopHookActive") is True
        fully_idle = raw.get("fullyIdle") is True
        if stopped or (require_idle and not fully_idle):
            return HookIdentity("", "", from_hook=True, halt=True)
        session_id = session_id or next(
            (
                value
                for key in ("session_id", "conversationId", "sessionId")
                if isinstance((value := raw.get(key)), str) and value
            ),
            "",
        )
        if not cwd:
            raw_cwd = raw.get("cwd")
            if isinstance(raw_cwd, str):
                cwd = raw_cwd
            if not cwd and isinstance(raw.get("workspacePaths"), list):
                cwd = next((item for item in raw["workspacePaths"] if isinstance(item, str) and item), "")
        transcript = raw.get("transcript_path") or raw.get("transcriptPath") or ""
        if not isinstance(transcript, str):
            transcript = ""
        from_hook = True
    else:
        transcript = ""
        from_hook = False
    if not session_id:
        raise DotError("missing session_id")
    if not is_valid_session_id(session_id):
        raise DotError(f"invalid session_id format: {session_id!r}")
    return HookIdentity(session_id, resolve_cwd(cwd), transcript, from_hook)


def _resolved_transcript(state: State, adapter: AgentAdapter, identity: HookIdentity) -> Path:
    if identity.transcript_path:
        path = expand_path(identity.transcript_path)
        if not path.is_file():
            raise DotError(f"{adapter.name} transcript from hook payload is unavailable at {path}")
        return path
    return find_transcript(_source_root(state, adapter.name), adapter.name, identity.session_id, identity.cwd)


def ingest_agent_session(state: State, agent: str, session_id: str = "", cwd: str = "", *, hook: bool = False) -> None:
    adapter = AGENT_ADAPTERS.get(agent)
    if adapter is None or adapter.parser is None or not adapter.verified:
        raise DotError(f"unknown session agent {agent!r}")
    if agent == "copilot":
        if not session_id:
            raise DotError("missing session_id")
        if not is_valid_session_id(session_id):
            raise DotError(f"invalid session_id format: {session_id!r}")
        identity = HookIdentity(session_id, resolve_cwd(cwd))
        path = _source_root(state, agent)
    else:
        identity = resolve_hook_identity(state, session_id, cwd, require_idle=agent == "agy")
        if identity.halt:
            if agent == "agy":
                state.stdout.write('{"decision":""}\n')
            return
        path = _resolved_transcript(state, adapter, identity)
    # Parsing owns the sole raw-source snapshot so logs, usage, and generation
    # identity can never describe different points in a growing transcript.
    parsed = adapter.parser(path, identity.session_id, identity.cwd)
    result = _publish_session(adapter, identity.session_id, parsed)
    state.stderr.write(report_ingestion(result) + "\n")
    if hook and agent == "agy":
        state.stdout.write('{"decision":""}\n')


def _publish_session(adapter: AgentAdapter, session_id: str, parsed: ParsedSession) -> SessionIngestionResult:
    """Reject incomplete extraction before publishing any part of a generation."""
    if parsed.usage_error is not None:
        raise DotError(f"{adapter.name}: usage extraction failed; retry session ingestion") from parsed.usage_error
    return ingest_session(
        adapter.name,
        session_id,
        parsed.logs,
        SessionSource(
            type=parsed.source_type, fingerprint=parsed.fingerprint, malformed=parsed.malformed, skipped=parsed.skipped
        ),
        usage=parsed.usage.to_dict() if parsed.usage is not None else None,
    )


def sync_sessions(
    state: State,
    *,
    agent: str = "",
    session: str = "",
    cwd: str = "",
    since: datetime | None = None,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    if agent and agent not in AGENT_ADAPTERS:
        raise DotError(f"unknown session agent {agent!r}")
    total = 0
    outcomes: dict[str, int] = {"ingested": 0, "duplicate": 0, "skipped": 0, "selected": 0}
    for adapter in agent_adapters(verified_only=True):
        if adapter.parser is None or (agent and adapter.name != agent):
            continue
        root = _validated_source_root(state, adapter)
        if root is None:
            continue
        count = 0
        try:
            candidates = enumerate_sessions(root, adapter.name)
        except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
            raise _workflow_failure(state, adapter, "scan sessions", error) from error
        for session_id, source_cwd, path in candidates:
            if session and session_id != session:
                continue
            try:
                if since:
                    modified = path.stat().st_mtime
                    if adapter.name == "grok" and path.name != "signals.json":
                        with suppress(FileNotFoundError):
                            modified = max(modified, (path.parent / "signals.json").stat().st_mtime)
                    if datetime.fromtimestamp(modified, UTC) < since:
                        continue
                parsed = adapter.parser(path, session_id, source_cwd)
                parsed_cwd = next((record.cwd for record in parsed.logs if record.cwd), source_cwd)
                if cwd and resolve_cwd(parsed_cwd) != cwd:
                    continue
                outcomes["selected"] += 1
                if dry_run:
                    count += 1
                    continue
                result = _publish_session(adapter, session_id, parsed)
            except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
                raise _workflow_failure(state, adapter, "ingest session", error, session_id) from error
            state.stderr.write(report_ingestion(result) + "\n")
            outcomes[result.status] += 1
            if not adapter.database or result.status == "ingested":
                count += 1
        verb = "ingested" if adapter.database else "checked"
        state.stderr.write(f"{adapter.name}: {count} {verb}\n")
        total += count
    state.stderr.write(f"agent-session-sync: done ({total} total processed)\n")
    if as_json:
        state.stdout.write(
            json.dumps(
                {
                    "schema": "dot.agent.session.sync/v1",
                    "parser_version": SESSION_PARSER_VERSION,
                    "dry_run": dry_run,
                    **outcomes,
                }
            )
            + "\n"
        )
    return total


def _workflow_failure(
    state: State, adapter: AgentAdapter, operation: str, error: BaseException, session_id: str = ""
) -> DotError:
    detail = _bounded_failure(error, session_id, state.config.agent.hook_failures.detail_limit)
    return DotError(f"failed to {operation} for {adapter.label}: {detail}")


def _bounded_failure(error: BaseException, session_id: str, limit: int) -> str:
    detail = str(error).replace(session_id, "<session>") if session_id else str(error)
    detail = _UUID.sub("<session>", detail)
    return " ".join(detail.split())[:limit]
