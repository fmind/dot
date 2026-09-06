"""Typer command tree for agent transcript and usage management."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import platform
import re
import secrets
import shlex
import sqlite3
import stat
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import closing, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO, Annotated, Any
from urllib.parse import quote

import typer
import yaml

from fmind_dot.agent_parsers import (
    AGENT_ADAPTERS,
    AGY_TRANSCRIPT_NAMES,
    GROK_TRANSCRIPT_NAME,
    AgentAdapter,
    agent_adapters,
    claude_session_id,
    codex_session_id,
    enumerate_sessions,
    enumerate_usage_sessions,
    extract_grok_usage,
    find_transcript,
    grok_cwd_from_path,
    resolve_cwd,
)
from fmind_dot.commands import add_group, record_alias, state_from
from fmind_dot.config import duration_seconds, expand_path
from fmind_dot.errors import DotError
from fmind_dot.session_query import (
    SessionQuery,
    export_sessions,
    migrate_legacy_sessions,
    parse_session_date,
    query_session_summaries,
    show_session,
)
from fmind_dot.session_store import (
    SESSION_PARSER_VERSION,
    SESSION_SCHEMA_VERSION,
    SESSION_STORE_VERSION,
    SessionManifest,
    SessionSource,
    fingerprint_file,
    ingest_session,
    is_valid_session_id,
    read_session_manifest,
    report_ingestion,
    session_generation_id,
    session_lineage_id,
    stored_generation,
    validate_session_generation,
)
from fmind_dot.state import State
from fmind_dot.system import build_notification, read_hook_payload, send_notification
from fmind_dot.usage import (
    aggregate_usage,
    list_usage_records,
    load_usage_records,
    parse_flexible_time,
    show_usage_record,
    write_usage_record,
    write_usage_stats,
)

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_UUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)

agent_app = typer.Typer(
    name="agent",
    help="Manage AI agent integrations and sessions",
    no_args_is_help=True,
    context_settings=_CONTEXT_SETTINGS,
)
session_app = typer.Typer(help="Manage agent session logs", no_args_is_help=True, context_settings=_CONTEXT_SETTINGS)
hook_app = typer.Typer(help="Run observable agent hooks", no_args_is_help=True, context_settings=_CONTEXT_SETTINGS)
usage_app = typer.Typer(
    help="Manage agent token usage in ~/.agents/usages",
    invoke_without_command=True,
    context_settings=_CONTEXT_SETTINGS,
)


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
    if adapter is None or adapter.parser is None:
        raise DotError(f"unknown session hook agent {agent!r}")
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
    fingerprint = fingerprint_file(path) if not adapter.database else ""
    existing = stored_generation(agent, identity.session_id, fingerprint) if fingerprint else None
    if existing is not None:
        from fmind_dot.session_store import SessionIngestionResult

        result = SessionIngestionResult("duplicate", existing.lineage_id, manifest=existing)
        state.stderr.write(report_ingestion(result) + "\n")
    else:
        parsed = adapter.parser(path, identity.session_id, identity.cwd)
        result = ingest_session(
            agent,
            identity.session_id,
            parsed.logs,
            SessionSource(
                type=parsed.source_type,
                fingerprint=parsed.fingerprint,
                malformed=parsed.malformed,
                skipped=parsed.skipped,
            ),
        )
        state.stderr.write(report_ingestion(result) + "\n")
        try:
            record_agent_usage(state, agent, identity.session_id, identity.cwd, path=path)
        except (OSError, ValueError, DotError) as error:
            state.stderr.write(f"{agent}: usage not recorded for this session: {error}\n")
    if hook and agent == "agy":
        state.stdout.write('{"decision":""}\n')


def record_agent_usage(state: State, agent: str, session_id: str, cwd: str = "", *, path: Path | None = None) -> None:
    adapter = AGENT_ADAPTERS.get(agent)
    if adapter is None or not adapter.verified:
        raise DotError(f"unknown usage hook agent {agent!r}")
    source = _source_root(state, agent)
    if agent == "grok":
        if path is None:
            path = find_transcript(source, agent, session_id, cwd)
        record = extract_grok_usage(path.parent, session_id, cwd or grok_cwd_from_path(source, path))
    else:
        if adapter.usage_parser is None:
            raise DotError(f"agent {agent!r} has no verified usage parser")
        if path is None:
            path = source if adapter.database else find_transcript(source, agent, session_id, cwd)
        record = adapter.usage_parser(path, session_id, cwd)
    write_usage_record(record)


def sync_sessions(state: State) -> int:
    total = 0
    for adapter in agent_adapters(verified_only=True):
        if adapter.parser is None:
            continue
        root = _validated_source_root(state, adapter)
        if root is None:
            continue
        count = 0
        try:
            candidates = enumerate_sessions(root, adapter.name)
        except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
            raise _workflow_failure(state, adapter, "scan sessions", error) from error
        for session_id, cwd, path in candidates:
            try:
                parsed = adapter.parser(path, session_id, cwd)
                result = ingest_session(
                    adapter.name,
                    session_id,
                    parsed.logs,
                    SessionSource(
                        type=parsed.source_type,
                        fingerprint=parsed.fingerprint,
                        malformed=parsed.malformed,
                        skipped=parsed.skipped,
                    ),
                )
            except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
                raise _workflow_failure(state, adapter, "ingest session", error, session_id) from error
            state.stderr.write(report_ingestion(result) + "\n")
            if not adapter.database and result.status != "duplicate":
                try:
                    record_agent_usage(state, adapter.name, session_id, cwd, path=path)
                except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
                    state.stderr.write(
                        f"{adapter.name}: usage not recorded for this session: "
                        f"{_bounded_failure(error, session_id, state.config.agent.hook_failures.detail_limit)}\n"
                    )
            if not adapter.database or result.status == "ingested":
                count += 1
        verb = "ingested" if adapter.database else "checked"
        state.stderr.write(f"{adapter.name}: {count} {verb}\n")
        total += count
    state.stderr.write(f"agent-session-sync: done ({total} total processed)\n")
    return total


def sync_usage(state: State) -> int:
    total = harnesses = 0
    for adapter in agent_adapters(verified_only=True):
        if adapter.parser is None:
            continue
        root = _validated_source_root(state, adapter)
        if root is None:
            continue
        written = 0
        try:
            candidates = enumerate_usage_sessions(root, adapter.name)
        except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
            raise _workflow_failure(state, adapter, "scan usage", error) from error
        for session_id, cwd, path in candidates:
            try:
                record_agent_usage(state, adapter.name, session_id, cwd, path=path)
            except (OSError, ValueError, TypeError, sqlite3.Error, DotError) as error:
                raise _workflow_failure(state, adapter, "record usage", error, session_id) from error
            written += 1
        if written:
            state.stderr.write(f"{adapter.name}: {written} recorded\n")
            total += written
            harnesses += 1
    state.stdout.write(f"Synced {total} usage records across {harnesses} harnesses into ~/.agents/usages\n")
    return total


def _workflow_failure(
    state: State, adapter: AgentAdapter, operation: str, error: BaseException, session_id: str = ""
) -> DotError:
    detail = _bounded_failure(error, session_id, state.config.agent.hook_failures.detail_limit)
    return DotError(f"failed to {operation} for {adapter.label}: {detail}")


def _query(agent: str, cwd: str, identity: str, since: str, until: str) -> SessionQuery:
    query = SessionQuery(
        agent=agent,
        cwd=cwd,
        identity=identity,
        since=parse_session_date(since),
        until=parse_session_date(until, end_of_day=True),
    )
    if query.since and query.until and query.since > query.until:
        raise DotError("--since must not be after --until")
    return query


@session_app.command("list")
def session_list(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", help="Filter by agent")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project", help="Filter by exact project/CWD")] = "",
    identity: Annotated[str, typer.Option("--session", help="Filter by session or lineage identity")] = "",
    since: Annotated[str, typer.Option("--since", help="RFC3339 timestamp or YYYY-MM-DD")] = "",
    until: Annotated[str, typer.Option("--until", help="RFC3339 timestamp or YYYY-MM-DD")] = "",
) -> None:
    state = state_from(context)
    for summary in query_session_summaries(_query(agent, cwd, identity, since, until)):
        state.stdout.write(
            f"{summary.ingested_at} {summary.agent} {summary.session_id} records={summary.record_count} "
            f"status={','.join(summary.status)} cwd={summary.cwd}\n"
        )


@session_app.command("show")
def session_show(
    context: typer.Context,
    identity: Annotated[str, typer.Argument(help="Session, lineage, or generation identity")] = "",
    agent: Annotated[str, typer.Option("--agent")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project")] = "",
    session: Annotated[str, typer.Option("--session")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    content: Annotated[bool, typer.Option("--content", help="Include prompt and response content")] = False,
) -> None:
    if not session and not identity:
        raise DotError("show requires a session or lineage identity")
    summary = show_session(_query(agent, cwd, session or identity, since, until), include_content=content)
    json.dump(summary.to_dict(include_records=content), state_from(context).stdout, ensure_ascii=False, indent=2)
    state_from(context).stdout.write("\n")


@session_app.command("export")
def session_export(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project")] = "",
    session: Annotated[str, typer.Option("--session")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    format: Annotated[str, typer.Option("--format")] = "json",  # noqa: A002 - CLI flag name
    content: Annotated[bool, typer.Option("--content")] = False,
    redact_content: Annotated[bool, typer.Option("--redact-content")] = False,
) -> None:
    export_sessions(
        state_from(context).stdout,
        _query(agent, cwd, session, since, until),
        format=format,
        include_content=content,
        redact_content=redact_content,
    )


@session_app.command("sync")
def session_sync(context: typer.Context) -> None:
    sync_sessions(state_from(context))


@session_app.command("migrate")
def session_migrate(
    context: typer.Context,
    apply: Annotated[bool, typer.Option("--apply", help="Write selected transcripts to the versioned store")] = False,
) -> None:
    migrate_legacy_sessions(state_from(context).stdout, apply=apply)


def _register_session_agent(adapter: AgentAdapter) -> None:
    if adapter.parser is None:
        return

    def command(
        context: typer.Context,
        session_id: Annotated[str, typer.Argument()] = "",
        cwd: Annotated[str, typer.Argument()] = "",
    ) -> None:
        ingest_agent_session(state_from(context), adapter.name, session_id, cwd)

    command.__name__ = f"session_{adapter.name}"
    session_app.command(adapter.name, help=f"Process a {adapter.label} session")(command)
    if adapter.alias:
        record_alias(session_app, adapter.name, adapter.alias)
        session_app.command(adapter.alias, hidden=True)(command)


for _adapter in agent_adapters(verified_only=True):
    _register_session_agent(_adapter)


@hook_app.command("session")
def hook_session(
    context: typer.Context,
    agent: Annotated[str, typer.Argument()],
    session_id: Annotated[str, typer.Argument()] = "",
    cwd: Annotated[str, typer.Argument()] = "",
) -> None:
    state = state_from(context)
    try:
        ingest_agent_session(state, agent, session_id, cwd, hook=True)
    except Exception as error:
        _spool_hook_failure(state, agent, "session", session_id, error)
        raise


@hook_app.command("usage")
def hook_usage(
    context: typer.Context,
    agent: Annotated[str, typer.Argument()],
    session_id: Annotated[str, typer.Argument()] = "",
    cwd: Annotated[str, typer.Argument()] = "",
) -> None:
    state = state_from(context)
    identity: HookIdentity | None = None
    try:
        if agent == "copilot" and not session_id:
            payload = decode_copilot_session_end(state.stdin)
            identity = HookIdentity(payload["sessionId"], resolve_cwd(payload["cwd"]))
        else:
            identity = resolve_hook_identity(state, session_id, cwd, require_idle=agent == "agy")
        if identity.halt:
            if agent == "agy":
                state.stdout.write('{"decision":""}\n')
            return
        path: Path | None = None
        adapter = AGENT_ADAPTERS.get(agent)
        if identity.transcript_path and adapter is not None and not adapter.database:
            path = _resolved_transcript(state, adapter, identity)
        record_agent_usage(state, agent, identity.session_id, identity.cwd, path=path)
        if agent == "agy" and identity.from_hook:
            state.stdout.write('{"decision":""}\n')
        if agent == "copilot":
            state.stdout.write("{}\n")
    except Exception as error:
        _spool_hook_failure(state, agent, "usage", identity.session_id if identity else session_id, error)
        if agent == "copilot":
            state.stdout.write("{}\n")
        raise


def decode_copilot_session_end(stream: IO[str] | None) -> dict[str, Any]:
    if stream is None:
        raise DotError("missing Copilot sessionEnd payload")
    content = stream.read()
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise DotError(f"invalid Copilot sessionEnd payload: {error}") from error
    expected = {"sessionId", "cwd", "reason", "timestamp"}
    if not isinstance(value, dict) or set(value) != expected:
        raise DotError("invalid Copilot sessionEnd payload: expected documented fields")
    if not isinstance(value["sessionId"], str) or not is_valid_session_id(value["sessionId"]):
        raise DotError(f"invalid Copilot sessionEnd sessionId: {value['sessionId']!r}")
    if not isinstance(value["cwd"], str) or not value["cwd"]:
        raise DotError("invalid Copilot sessionEnd payload: missing cwd")
    if isinstance(value["timestamp"], bool) or not isinstance(value["timestamp"], int) or value["timestamp"] <= 0:
        raise DotError("invalid Copilot sessionEnd payload: timestamp must be Unix milliseconds")
    if not isinstance(value["reason"], str):
        raise DotError("invalid Copilot sessionEnd payload: reason must be a string")
    if value["reason"] not in {"complete", "error", "abort", "timeout", "user_exit"}:
        raise DotError(f"unsupported Copilot sessionEnd reason {value['reason']!r}")
    return value


@hook_app.command("copilot-session-end")
def copilot_session_end(context: typer.Context) -> None:
    state = state_from(context)
    session_id = ""
    try:
        payload = decode_copilot_session_end(state.stdin)
        session_id = payload["sessionId"]
        ingest_agent_session(state, "copilot", session_id, payload["cwd"], hook=True)
    except Exception as error:
        # Copilot documents sessionEnd as non-blocking. Keep unexpected adapter
        # failures observable while always returning its neutral hook response.
        reported_error = error
        try:
            _spool_hook_failure(state, "copilot", "sessionEnd", session_id, error)
        except Exception as spool_error:
            reported_error = spool_error
        state.stderr.write(
            "copilot sessionEnd sync failed without blocking the session: "
            f"{_bounded_failure(reported_error, session_id, state.config.agent.hook_failures.detail_limit)}\n"
        )
    state.stdout.write("{}\n")


@hook_app.command("notify")
def hook_notify(
    context: typer.Context,
    agent: Annotated[str, typer.Argument()],
    event: Annotated[str, typer.Argument()],
) -> None:
    state = state_from(context)
    identity: HookIdentity | None = None
    try:
        # Consume the hook payload so re-entrant and mid-turn events remain quiet.
        identity = resolve_hook_identity(state, "notification", "", require_idle=agent == "agy")
        if identity.halt:
            return
        cwd = Path(identity.cwd) if identity.cwd else None
        send_notification(state, build_notification(agent, event, cwd, Path.home()))
    except (OSError, ValueError, DotError) as error:
        _spool_hook_failure(state, agent, f"notify:{event}", identity.session_id if identity else "", error)
        raise


def _bounded_failure(error: BaseException, session_id: str, limit: int) -> str:
    detail = str(error).replace(session_id, "<session>") if session_id else str(error)
    detail = _UUID.sub("<session>", detail)
    return " ".join(detail.split())[:limit]


def _safe_agent_fs_available() -> bool:
    required_dir_fd = (os.open, os.stat, os.unlink, os.mkdir, os.rmdir, os.rename)
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and callable(getattr(os, "fwalk", None))
        and all(function in os.supports_dir_fd for function in required_dir_fd)
        and os.stat in os.supports_follow_symlinks
        and os.listdir in os.supports_fd
        and all(callable(getattr(os, name, None)) for name in ("fchmod", "fsync", "listdir", "write"))
    )


def _same_file_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _open_verified_directory(path: Path) -> int:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise OSError(f"unsafe directory {path}")
    descriptor = os.open(path, _DIRECTORY_FLAGS)
    try:
        opened = os.fstat(descriptor)
        after = path.lstat()
        if not _same_file_identity(opened, before) or not _same_file_identity(opened, after):
            raise OSError(f"directory changed while opening {path}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_directory_at(parent: int, name: str) -> int:
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise OSError(f"unsafe directory {name}")
    descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
    try:
        opened = os.fstat(descriptor)
        after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not _same_file_identity(opened, before) or not _same_file_identity(opened, after):
            raise OSError(f"directory changed while opening {name}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_or_create_directory_at(parent: int, name: str, mode: int, *, enforce_mode: bool = True) -> int:
    with suppress(FileExistsError):
        os.mkdir(name, mode=mode, dir_fd=parent)
    descriptor = _open_directory_at(parent, name)
    try:
        if enforce_mode:
            os.fchmod(descriptor, mode)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _publish_owner_only_at(directory: int, name: str, content: bytes) -> None:
    temporary = f".{name}.{secrets.token_hex(8)}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        os.fchmod(descriptor, 0o600)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("failed to write hook failure record")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.rename(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory)
        raise


def _write_hook_failure_record(state: State, agent: str, operation: str, session_id: str, error: BaseException) -> None:
    home = _open_verified_directory(Path.home())
    try:
        agents = _open_or_create_directory_at(home, ".agents", 0o700, enforce_mode=False)
        try:
            failures = _open_or_create_directory_at(agents, "hook-failures", 0o700)
            try:
                root = _open_or_create_directory_at(failures, "v1", 0o700)
            finally:
                os.close(failures)
        finally:
            os.close(agents)
    finally:
        os.close(home)

    try:
        detail = _bounded_failure(error, session_id, state.config.agent.hook_failures.detail_limit)
        session_hash = hashlib.sha256(f"{agent}\0{session_id}\0".encode()).hexdigest()[:12] if session_id else ""
        record: dict[str, Any] = {
            "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "agent": agent,
            "operation": operation,
        }
        if session_hash:
            record["session_hash"] = session_hash
        record["detail"] = detail
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        suffix = hashlib.sha256(f"{agent}\0{operation}\0{detail}\0".encode()).hexdigest()[:12]
        records: list[str] = []
        for name in os.listdir(root):  # noqa: PTH208 - the descriptor preserves confinement during races.
            if not name.endswith(".json"):
                continue
            try:
                mode = os.stat(name, dir_fd=root, follow_symlinks=False).st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISREG(mode):
                records.append(name)
        published = f"{stamp}-{suffix}.json"
        content = (json.dumps(record, separators=(",", ":")) + "\n").encode()
        _publish_owner_only_at(root, published, content)
        if published not in records:
            records.append(published)
        records.sort()
        excess = max(0, len(records) - state.config.agent.hook_failures.limit)
        for name in records[:excess]:
            with suppress(FileNotFoundError):
                os.unlink(name, dir_fd=root)
    finally:
        os.close(root)


def _spool_hook_failure(state: State, agent: str, operation: str, session_id: str, error: BaseException) -> None:
    detail_limit = state.config.agent.hook_failures.detail_limit
    if not _safe_agent_fs_available():
        state.stderr.write("agent hook failure spool unavailable: safe filesystem operations are unavailable\n")
        return
    try:
        _write_hook_failure_record(state, agent, operation, session_id, error)
    except Exception as spool_error:
        detail = _bounded_failure(spool_error, session_id, detail_limit)
        state.stderr.write(f"agent hook failure spool unavailable: {detail}\n")


def _usage_rows(harness: str, since: str, until: str, by_model: bool):
    return aggregate_usage(
        load_usage_records(),
        harness=harness,
        since=parse_flexible_time(since) if since else None,
        until=parse_flexible_time(until) if until else None,
        by_model=by_model,
    )


@usage_app.callback(invoke_without_command=True)
def usage_stats(
    context: typer.Context,
    harness: Annotated[str, typer.Option("--harness", "-a")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    if context.invoked_subcommand is None:
        state = state_from(context)
        write_usage_stats(
            state.stdout, _usage_rows(harness, since, until, by_model), as_json=as_json, by_model=by_model
        )


@usage_app.command("stats")
def usage_stats_command(
    context: typer.Context,
    harness: Annotated[str, typer.Option("--harness", "-a")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    state = state_from(context)
    write_usage_stats(state.stdout, _usage_rows(harness, since, until, by_model), as_json=as_json, by_model=by_model)


@usage_app.command("list")
def usage_list(
    context: typer.Context,
    harness: Annotated[str, typer.Option("--harness", "-a")] = "",
    limit: Annotated[int, typer.Option("--limit", "-n")] = 50,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    state = state_from(context)
    records = list_usage_records(load_usage_records(), harness=harness, limit=limit)
    if as_json:
        json.dump([record.to_dict() for record in records], state.stdout, ensure_ascii=False, indent=2)
        state.stdout.write("\n")
        return
    if not records:
        state.stdout.write("No usage records found.\n")
        return
    state.stdout.write("TIMESTAMP\tHARNESS\tSESSION ID\tMODEL\tTOTAL TOKENS\tCOST (USD)\n")
    for record in records:
        state.stdout.write(
            f"{record.timestamp[:19]}\t{record.harness}\t{record.session_id}\t{record.model or '-'}\t"
            f"{record.total_tokens:,}\t${record.cost_usd:.4f}\n"
        )


@usage_app.command("show")
def usage_show(
    context: typer.Context,
    harness: Annotated[str, typer.Argument()],
    session_id: Annotated[str, typer.Argument()],
) -> None:
    state_from(context).stdout.write(show_usage_record(harness, session_id).decode())


@usage_app.command("sync")
def usage_sync(context: typer.Context) -> None:
    sync_usage(state_from(context))


_SHARED_PERSONA = "~/.agents/AGENTS.md"
_SHARED_SKILLS = "~/.agents/skills"


@dataclass(frozen=True)
class DoctorIntegration:
    agent: str
    persona_path: str
    skills_path: str = ""
    skills_config: str = ""
    hook_path: str = ""
    hook_commands: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    hook_format: str = ""
    notifications: bool = False
    discovery_only: bool = False
    source_time_query: str = ""


# This table describes only integrations managed by the active Python-first tree.
_DOCTOR_INTEGRATIONS = (
    DoctorIntegration(
        "agy",
        "~/.gemini/GEMINI.md",
        skills_path="~/.gemini/config/skills",
        hook_path="~/.gemini/config/hooks.json",
        hook_commands=(
            "dot agent hook session agy",
            "dot agent hook notify agy stop",
            "dot agent hook usage agy",
        ),
        tools=("dot", "agy"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "claude",
        "~/.claude/CLAUDE.md",
        skills_path="~/.claude/skills",
        hook_path="~/.claude/settings.json",
        hook_commands=(
            "dot agent hook session claude",
            "dot agent hook notify claude stop",
            "dot agent hook usage claude",
        ),
        tools=("dot", "claude"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "codex",
        "~/.codex/AGENTS.md",
        hook_path="~/.codex/config.toml",
        hook_commands=(
            "dot agent hook session codex",
            "dot agent hook notify codex stop",
            "dot agent hook usage codex",
        ),
        tools=("dot", "codex"),
        hook_format="toml",
        notifications=True,
    ),
    DoctorIntegration(
        "grok",
        "~/.grok/AGENTS.md",
        skills_path="~/.grok/skills",
        hook_path="~/.grok/hooks/hooks.json",
        hook_commands=(
            "dot agent hook session grok",
            "dot agent hook notify grok stop",
            "dot agent hook usage grok",
        ),
        tools=("dot", "grok"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "copilot",
        "~/.copilot/copilot-instructions.md",
        hook_path="~/.copilot/hooks/session-log.json",
        hook_commands=("dot agent hook copilot-session-end", "dot agent hook usage copilot"),
        tools=("dot", "copilot"),
        hook_format="json",
        source_time_query="SELECT strftime('%Y-%m-%dT%H:%M:%SZ', MAX(updated_at)) AS at FROM sessions",
    ),
)


@dataclass(frozen=True)
class AgentDoctorResult:
    agent: str
    discovery: str
    hooks: str
    tools: str
    source: str
    last_ingestion: str
    last_failure: str
    archive_lag: str
    truncated: bool
    healthy: bool


@dataclass(frozen=True)
class _SourceInspection:
    status: str
    latest: datetime | None
    present: bool
    healthy: bool
    truncated: bool = False


@dataclass
class _LineageSummary:
    last_complete: datetime | None = None
    latest: datetime | None = None
    latest_partial: bool = False
    unreadable: bool = False
    truncated: bool = False


def _same_resolved_path(path: Path, target: Path) -> bool:
    try:
        return path.resolve(strict=True) == target.resolve(strict=True)
    except OSError:
        return False


def _structured_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _structured_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _structured_strings(item)


def _load_configuration(path: Path, format_name: str) -> object:
    content = path.read_bytes()
    if format_name == "json":
        return json.loads(content)
    if format_name == "toml":
        return tomllib.loads(content.decode())
    if format_name == "yaml":
        return yaml.safe_load(content)
    raise ValueError(f"unsupported configuration format {format_name!r}")


def _check_discovery(definition: DoctorIntegration) -> tuple[str, bool]:
    canonical_persona = expand_path(_SHARED_PERSONA)
    canonical_skills = expand_path(_SHARED_SKILLS)
    if not _same_resolved_path(expand_path(definition.persona_path), canonical_persona):
        return "persona-broken", False
    if not canonical_skills.is_dir():
        return "skills-missing", False
    if definition.skills_path and not _same_resolved_path(expand_path(definition.skills_path), canonical_skills):
        return "skills-broken", False
    if definition.skills_config:
        try:
            config = _load_configuration(expand_path(definition.skills_config), "yaml")
        except OSError, UnicodeError, ValueError, yaml.YAMLError:
            return "skills-broken", False
        if _SHARED_SKILLS not in set(_structured_strings(config)):
            return "skills-broken", False
    return "healthy", True


def _command_arguments(command: str) -> tuple[str, ...]:
    fields = shlex.split(command)
    if len(fields) < 2 or fields[0] != "dot":
        return ()
    agents = set(AGENT_ADAPTERS)
    for index, field in enumerate(fields[1:]):
        if field.startswith("-") or field in agents:
            return tuple(fields[1 : index + 1])
    return tuple(fields[1:])


def _dot_command_prober(state: State):
    binary = state.runner.which("dot")
    cache: dict[tuple[str, ...], bool] = {}

    def runnable(arguments: tuple[str, ...]) -> bool:
        if not arguments:
            return True
        if binary is None:
            return False
        if arguments not in cache:
            try:
                result = state.runner.run([str(binary), *arguments, "--help"], check=False)
            except OSError, DotError:
                cache[arguments] = False
            else:
                cache[arguments] = result.returncode == 0
        return cache[arguments]

    return runnable


def _check_hooks(definition: DoctorIntegration, runnable) -> tuple[str, bool]:
    if not definition.hook_path:
        return "sync-only", True
    try:
        config = _load_configuration(expand_path(definition.hook_path), definition.hook_format)
    except OSError, UnicodeError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError:
        return "malformed", False
    if definition.agent == "copilot" and (not isinstance(config, dict) or config.get("version") != 1):
        return "unsupported-version", False
    commands = set(_structured_strings(config))
    for command in definition.hook_commands:
        if command not in commands:
            return "command-mismatch", False
        if not runnable(_command_arguments(command)):
            return "command-unavailable", False
    return "healthy", True


def _notifier_available(state: State) -> bool:
    if platform.system() == "Darwin":
        return state.runner.which("osascript") is not None
    if platform.system() == "Linux":
        return any(state.runner.which(command) is not None for command in ("notify-send", "gdbus"))
    return False


def _check_tools(state: State, definition: DoctorIntegration) -> tuple[str, bool]:
    missing = sorted(f"{name}:missing" for name in definition.tools if state.runner.which(name) is None)
    return (",".join(missing), False) if missing else ("healthy", True)


def _raw_session_identity(root: Path, path: Path, agent: str) -> str:
    if agent == "claude":
        identity = claude_session_id(path)
    elif agent == "codex":
        identity = codex_session_id(path)
    elif agent == "grok":
        identity = path.parent.name if path.name == GROK_TRANSCRIPT_NAME else ""
    elif agent == "agy":
        try:
            relative = path.relative_to(root)
        except ValueError:
            return ""
        identity = relative.parts[0] if len(relative.parts) >= 2 and path.name in AGY_TRANSCRIPT_NAMES else ""
    else:
        return ""
    return identity if is_valid_session_id(identity) else ""


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(UTC)


def _query_database_source_time(path: Path, definition: DoctorIntegration) -> datetime | None:
    if not definition.source_time_query:
        raise ValueError("database source has no timestamp query")
    uri = f"file:{quote(str(path))}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        row = connection.execute(definition.source_time_query).fetchone()
    if row is None or row[0] is None or row[0] == "":
        return None
    return _parse_timestamp(str(row[0]))


def _database_source_time(path: Path, definition: DoctorIntegration, fallback: datetime) -> datetime | None:
    """Retain the legacy conservative fallback for callers outside doctor health."""
    try:
        return _query_database_source_time(path, definition)
    except OSError, ValueError, sqlite3.Error:
        return fallback


def _source_file_metadata(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns, info.st_size


def _source_fingerprint_at(directory_fd: int, name: str, expected: os.stat_result) -> str:
    """Hash one stable regular-file snapshot through its already-open parent."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or _source_file_metadata(before) != _source_file_metadata(expected):
            raise OSError(errno.ESTALE, "session source changed before inspection", name)
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        snapshot = _source_file_metadata(expected)
        if _source_file_metadata(after) != snapshot or _source_file_metadata(current) != snapshot:
            raise OSError(errno.ESTALE, "session source changed during inspection", name)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _inspect_source(state: State, definition: DoctorIntegration) -> _SourceInspection:
    source_text = state.config.agent.sources.get(definition.agent, "")
    if not source_text:
        return _SourceInspection("unconfigured", None, False, False)
    root = expand_path(source_text)
    try:
        info = root.lstat()
    except FileNotFoundError:
        return _SourceInspection("missing", None, False, True)
    except OSError:
        return _SourceInspection("unreadable", None, False, False)
    if stat.S_ISLNK(info.st_mode):
        return _SourceInspection("linked", None, False, False)
    if definition.source_time_query:
        if not stat.S_ISREG(info.st_mode):
            return _SourceInspection("wrong-kind", None, True, False)
        try:
            latest = _query_database_source_time(root, definition)
        except OSError, ValueError, sqlite3.Error:
            return _SourceInspection("unreadable", None, True, False)
        return _SourceInspection("present", latest, True, True)
    if definition.discovery_only:
        return _SourceInspection(
            "present", datetime.fromtimestamp(info.st_mtime, UTC), True, stat.S_ISREG(info.st_mode)
        )
    if not stat.S_ISDIR(info.st_mode):
        return _SourceInspection("wrong-kind", None, True, False)

    seen = 0
    latest: datetime | None = None
    failed = False
    reconciled = True
    limit = state.config.agent.doctor.scan_limit

    def onerror(_error: OSError) -> None:
        nonlocal failed
        failed = True

    try:
        root_fd = os.open(root, _DIRECTORY_FLAGS)
    except OSError:
        return _SourceInspection("unreadable", None, True, False)
    try:
        opened_root = os.fstat(root_fd)
        if (opened_root.st_dev, opened_root.st_ino) != (info.st_dev, info.st_ino):
            return _SourceInspection("unreadable", None, True, False)
        for walk_root, directories, files, directory_fd in os.fwalk(
            ".", topdown=True, onerror=onerror, follow_symlinks=False, dir_fd=root_fd
        ):
            relative = Path(walk_root)
            current_path = root if relative == Path() else root / relative
            kept_directories: list[str] = []
            for name in sorted(directories):
                try:
                    directory_info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError:
                    failed = True
                    continue
                if stat.S_ISDIR(directory_info.st_mode):
                    kept_directories.append(name)
            directories[:] = kept_directories
            for name in sorted(files):
                path = current_path / name
                try:
                    entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError:
                    failed = True
                    continue
                if not stat.S_ISREG(entry.st_mode):
                    continue
                if seen >= limit:
                    return _SourceInspection("present", latest, True, not failed and reconciled, True)
                seen += 1
                if definition.agent == "agy" and name == AGY_TRANSCRIPT_NAMES[1] and AGY_TRANSCRIPT_NAMES[0] in files:
                    continue
                session_id = _raw_session_identity(root, path, definition.agent)
                if not session_id:
                    continue
                try:
                    fingerprint = _source_fingerprint_at(directory_fd, name, entry)
                    manifest = stored_generation(definition.agent, session_id, fingerprint)
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if _source_file_metadata(current) != _source_file_metadata(entry):
                        raise OSError(errno.ESTALE, "session source changed during archive reconciliation", name)
                except OSError, ValueError:
                    failed = True
                    continue
                if manifest is None or manifest.completeness != "complete":
                    reconciled = False
                modified = datetime.fromtimestamp(entry.st_mtime, UTC)
                latest = max(latest, modified) if latest is not None else modified
    finally:
        os.close(root_fd)
    if failed:
        return _SourceInspection("unreadable", latest, True, False)
    if not reconciled:
        return _SourceInspection("unreconciled", latest, True, False)
    return _SourceInspection("present", latest, True, True)


def _valid_manifest_path(root: Path, path: Path, manifest: SessionManifest, agent: str) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    if len(parts) != 3 or parts[-1] != "manifest.json":
        return False
    lineage, generation = parts[:2]
    return (
        manifest.agent == agent
        and manifest.lineage_id == lineage == session_lineage_id(agent, manifest.session_id)
        and manifest.schema_version == SESSION_SCHEMA_VERSION
        and manifest.parser_version == SESSION_PARSER_VERSION
        and generation == session_generation_id(manifest.source_fingerprint)
    )


def _inspect_lineage(state: State, definition: DoctorIntegration) -> _LineageSummary:
    root = Path.home() / ".agents/sessions" / SESSION_STORE_VERSION / definition.agent
    summary = _LineageSummary()
    try:
        info = root.lstat()
    except FileNotFoundError:
        return summary
    except OSError:
        summary.unreadable = True
        return summary
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        summary.unreadable = True
        return summary

    manifests: list[Path] = []
    failed = False

    def onerror(_error: OSError) -> None:
        nonlocal failed
        failed = True

    for current, directories, files in os.walk(root, topdown=True, onerror=onerror, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(name for name in directories if not (current_path / name).is_symlink())
        manifests.extend(current_path / name for name in sorted(files) if name == "manifest.json")
        if len(manifests) > state.config.agent.doctor.scan_limit:
            summary.truncated = True
            break
    for path in manifests[: state.config.agent.doctor.scan_limit]:
        try:
            manifest = read_session_manifest(path.parent)
            if not _valid_manifest_path(root, path, manifest, definition.agent):
                raise ValueError("manifest identity does not match its lineage")
            validate_session_generation(path.parent, manifest)
            ingested = _parse_timestamp(manifest.ingested_at)
        except OSError, UnicodeError, ValueError, json.JSONDecodeError:
            summary.unreadable = True
            continue
        if summary.latest is None or ingested > summary.latest:
            summary.latest = ingested
            summary.latest_partial = manifest.completeness != "complete"
        if manifest.completeness == "complete" and (summary.last_complete is None or ingested > summary.last_complete):
            summary.last_complete = ingested
    summary.unreadable = summary.unreadable or failed
    return summary


def _inspect_last_hook_failure(state: State, agent: str) -> tuple[str, bool]:
    root = Path.home() / ".agents/hook-failures/v1"
    try:
        info = root.lstat()
    except FileNotFoundError:
        return "none", True
    except OSError:
        return "unreadable", False
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return "unreadable", False
    try:
        entries = sorted(root.iterdir())[-state.config.agent.hook_failures.limit :]
    except OSError:
        return "unreadable", False
    unreadable = False
    for path in reversed(entries):
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            content = path.read_bytes()
            if not content.strip():
                continue
            record = json.loads(content)
            if not isinstance(record, dict):
                raise ValueError("failure record is not an object")
            if record.get("agent") == agent:
                occurred_at, operation = record.get("occurred_at"), record.get("operation")
                if not isinstance(occurred_at, str) or not isinstance(operation, str):
                    raise ValueError("failure record metadata is invalid")
                return f"{occurred_at}:{operation}", True
        except OSError, UnicodeError, ValueError, json.JSONDecodeError:
            unreadable = True
    return ("unreadable", False) if unreadable else ("none", True)


def _format_duration(value: timedelta) -> str:
    seconds = max(0, int(value.total_seconds()))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours}h{minutes}m{seconds}s"
    if minutes:
        return f"{minutes}m{seconds}s"
    return f"{seconds}s"


def _summarize_lineage(
    state: State,
    definition: DoctorIntegration,
    now: datetime,
    source: _SourceInspection,
    summary: _LineageSummary,
) -> tuple[str, str, bool]:
    if summary.unreadable:
        return "unreadable", "unknown", False
    if definition.discovery_only:
        return "discovery-only", "unknown", True
    if summary.last_complete is None:
        if summary.latest_partial:
            return "partial-only", "unknown", False
        return "none", "unknown", not source.present or source.latest is None
    if not source.healthy:
        ingestion = summary.last_complete.isoformat(timespec="seconds").replace("+00:00", "Z")
        return ingestion, "unknown", False
    ingestion = summary.last_complete.isoformat(timespec="seconds").replace("+00:00", "Z")
    if summary.latest_partial and summary.latest is not None and summary.latest > summary.last_complete:
        return f"{ingestion}:newer-partial", "unknown", False
    if not source.present or source.latest is None or source.latest <= summary.last_complete:
        return ingestion, "0s", True
    lag = source.latest - summary.last_complete
    healthy = lag.total_seconds() <= duration_seconds(state.config.agent.doctor.stale_lag)
    healthy = healthy and source.latest <= now + timedelta(minutes=1)
    return ingestion, _format_duration(lag), healthy


def gather_agent_doctor(state: State, *, now: datetime | None = None) -> list[AgentDoctorResult]:
    current = now or datetime.now(UTC)
    runnable = _dot_command_prober(state)
    notifier_available = _notifier_available(state)
    results: list[AgentDoctorResult] = []
    for definition in _DOCTOR_INTEGRATIONS:
        discovery, discovery_ok = _check_discovery(definition)
        hooks, hooks_ok = _check_hooks(definition, runnable)
        if definition.notifications and not notifier_available:
            hooks, hooks_ok = "notification-unavailable", False
        tools, tools_ok = _check_tools(state, definition)
        source = _inspect_source(state, definition)
        lineage = _inspect_lineage(state, definition)
        failure, failure_ok = _inspect_last_hook_failure(state, definition.agent)
        ingestion, lag, lineage_ok = _summarize_lineage(state, definition, current, source, lineage)
        truncated = source.truncated or lineage.truncated
        results.append(
            AgentDoctorResult(
                definition.agent,
                discovery,
                hooks,
                tools,
                source.status,
                ingestion,
                failure,
                lag,
                truncated,
                discovery_ok
                and hooks_ok
                and tools_ok
                and source.healthy
                and lineage_ok
                and failure_ok
                and not truncated,
            )
        )
    return results


def _doctor_repair_targets() -> list[Path]:
    targets = {expand_path(_SHARED_PERSONA), expand_path(_SHARED_SKILLS)}
    for definition in _DOCTOR_INTEGRATIONS:
        targets.add(expand_path(definition.persona_path))
        for value in (definition.skills_path, definition.skills_config, definition.hook_path):
            if value:
                targets.add(expand_path(value))
    return sorted(targets)


def repair_agent_integrations(state: State, *, dry_run: bool = False) -> None:
    args = ["chezmoi", "apply"]
    if dry_run:
        args.append("--dry-run")
    args.extend(("--force", *(str(path) for path in _doctor_repair_targets())))
    try:
        state.runner.run(args)
    except (OSError, DotError) as error:
        raise DotError("failed to repair agent integrations") from error


def run_agent_doctor(
    state: State, *, fix: bool = False, dry_run: bool = False, now: datetime | None = None
) -> list[AgentDoctorResult]:
    if dry_run and not fix:
        raise DotError("--dry-run requires --fix")
    if fix:
        repair_agent_integrations(state, dry_run=dry_run)
    results = gather_agent_doctor(state, now=now)
    state.stdout.write("Agent doctor\n")
    for result in results:
        mark = "✓" if result.healthy else "✗"
        state.stdout.write(
            f"{mark} {result.agent}: discovery={result.discovery} hooks={result.hooks} tools={result.tools} "
            f"source={result.source} ingestion={result.last_ingestion} failure={result.last_failure} "
            f"lag={result.archive_lag} truncated={str(result.truncated).lower()}\n"
        )
    if not all(result.healthy for result in results):
        raise DotError("agent doctor found unhealthy integrations")
    return results


@agent_app.command("doctor")
def agent_doctor(
    context: typer.Context,
    fix: Annotated[
        bool, typer.Option("--fix", "-f", help="Apply the managed agent integration targets with chezmoi")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-N", help="Preview --fix without changing deployed files")
    ] = False,
) -> None:
    run_agent_doctor(state_from(context), fix=fix, dry_run=dry_run)


@agent_app.command("clean")
def agent_clean(
    context: typer.Context,
    targets: Annotated[list[str] | None, typer.Argument()] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n")] = False,
) -> None:
    state = state_from(context)
    requested = targets or ["prompts", "proposals", "reports"]
    expanded: set[str] = set()
    for raw in requested:
        for target in raw.lower().split(","):
            target = target.strip()
            if target == "all":
                expanded.update({"prompts", "proposals", "reports"})
            elif target in {"prompts", "proposals", "reports"}:
                expanded.add(target)
            elif target:
                raise DotError(f"unknown target {target!r}: must be one of all, prompts, proposals, reports")
    if not _safe_agent_fs_available():
        raise DotError("safe agent cleanup is unavailable on this platform")
    result = state.runner.run(["git", "rev-parse", "--show-toplevel"], check=False)
    project = Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else Path.cwd()
    try:
        project_descriptor = _open_verified_directory(project)
    except OSError as error:
        raise DotError(f"failed to open cleanup root: {error}") from error
    try:
        try:
            agents_mode = os.stat(".agents", dir_fd=project_descriptor, follow_symlinks=False).st_mode
        except FileNotFoundError:
            agents_descriptor = None
        else:
            if stat.S_ISLNK(agents_mode):
                raise DotError("refusing symlinked cleanup directory .agents")
            if not stat.S_ISDIR(agents_mode):
                raise DotError("cleanup target .agents is not a directory")
            try:
                agents_descriptor = _open_directory_at(project_descriptor, ".agents")
            except OSError as error:
                raise DotError(f"failed to open cleanup directory .agents: {error}") from error

        try:
            for target in sorted(expanded):
                entries: list[str] = []
                target_descriptor: int | None = None
                if agents_descriptor is not None:
                    try:
                        mode = os.stat(target, dir_fd=agents_descriptor, follow_symlinks=False).st_mode
                    except FileNotFoundError:
                        pass
                    else:
                        if stat.S_ISLNK(mode):
                            raise DotError(f"refusing symlinked cleanup directory .agents/{target}")
                        if not stat.S_ISDIR(mode):
                            raise DotError(f"cleanup target .agents/{target} is not a directory")
                        try:
                            target_descriptor = _open_directory_at(agents_descriptor, target)
                        except OSError as error:
                            raise DotError(f"failed to open cleanup directory .agents/{target}: {error}") from error
                        try:
                            # Pathlib would reopen the raced pathname; list the held directory instead.
                            entries = sorted(os.listdir(target_descriptor))  # noqa: PTH208
                        except BaseException:
                            os.close(target_descriptor)
                            target_descriptor = None
                            raise
                try:
                    if dry_run:
                        for entry in entries:
                            state.stdout.write(f"  ○ .agents/{target}/{entry}\n")
                    elif target_descriptor is not None:
                        _clear_directory(target_descriptor, target)
                finally:
                    if target_descriptor is not None:
                        os.close(target_descriptor)
                state.stdout.write(
                    f"✓ {'Would clean' if dry_run else 'Cleaned'} {len(entries)} file(s) in .agents/{target}\n"
                )
        finally:
            if agents_descriptor is not None:
                os.close(agents_descriptor)
    finally:
        os.close(project_descriptor)


def _clear_directory(directory: int, target: str) -> None:
    def fail(error: OSError) -> None:
        raise error

    try:
        walk = os.fwalk(".", topdown=False, onerror=fail, follow_symlinks=False, dir_fd=directory)
        for _root, directory_names, file_names, current in walk:
            for name in sorted(file_names):
                mode = os.stat(name, dir_fd=current, follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    raise DotError(f"cleanup entry .agents/{target}/{name} changed during removal")
                with suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=current)
            for name in sorted(directory_names):
                try:
                    mode = os.stat(name, dir_fd=current, follow_symlinks=False).st_mode
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
                    os.unlink(name, dir_fd=current)
                    continue
                child = _open_directory_at(current, name)
                try:
                    if os.listdir(child):  # noqa: PTH208 - keep the emptiness check on the verified descriptor.
                        raise DotError(f"cleanup directory .agents/{target}/{name} changed during removal")
                    opened = os.fstat(child)
                    current_entry = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if not _same_file_identity(opened, current_entry):
                        raise DotError(f"cleanup directory .agents/{target}/{name} changed during removal")
                    os.rmdir(name, dir_fd=current)
                finally:
                    os.close(child)
    except (DotError, OSError) as error:
        if isinstance(error, DotError):
            raise
        raise DotError(f"failed to clean .agents/{target}: {error}") from error


add_group(agent_app, hook_app, "hook", "h")
add_group(agent_app, session_app, "session", "s")
add_group(agent_app, usage_app, "usage", "u")

# Preserve the terse aliases used by hooks and interactive shell workflows.
for _parent, _name, _callback, _alias in (
    (agent_app, "clean", agent_clean, "c"),
    (agent_app, "doctor", agent_doctor, "d"),
    (session_app, "list", session_list, "l"),
    (session_app, "show", session_show, "w"),
    (session_app, "export", session_export, "e"),
    (session_app, "sync", session_sync, "s"),
    (session_app, "migrate", session_migrate, "m"),
    (hook_app, "session", hook_session, "s"),
    (hook_app, "usage", hook_usage, "u"),
    (hook_app, "notify", hook_notify, "n"),
    (hook_app, "copilot-session-end", copilot_session_end, "c"),
    (usage_app, "stats", usage_stats_command, "s"),
    (usage_app, "list", usage_list, "l"),
    (usage_app, "show", usage_show, "w"),
    (usage_app, "sync", usage_sync, "y"),
):
    record_alias(_parent, _name, _alias)
    _parent.command(_alias, hidden=True)(_callback)


__all__ = [
    "AgentDoctorResult",
    "HookIdentity",
    "agent_app",
    "decode_copilot_session_end",
    "gather_agent_doctor",
    "ingest_agent_session",
    "record_agent_usage",
    "repair_agent_integrations",
    "resolve_hook_identity",
    "run_agent_doctor",
    "sync_sessions",
    "sync_usage",
]
