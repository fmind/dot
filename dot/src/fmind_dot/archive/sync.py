"""Incremental capture of agent sessions from their native stores."""

import json
import re
import sqlite3
import stat
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    AgentAdapter,
    ParsedSession,
    SessionCandidate,
    claude_parent_session_id,
    resolve_cwd,
)
from fmind_dot.archive.store import (
    BUNDLE_SUFFIX,
    SESSION_PARSER_VERSION,
    SessionIngestionResult,
    SessionManifest,
    SessionSource,
    ingest_session,
    is_valid_session_id,
    read_session_manifest,
    report_ingestion,
    session_store_root,
    upgrade_session_bundle,
)
from fmind_dot.archive.usage import RETIRED_AGENTS
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import private_directory, write_private_file
from fmind_dot.reporting import write_json
from fmind_dot.state import State

SYNC_SCHEMA = "dot.agent.session.sync/v2"
SYNC_STATE_NAME = ".sync.json"
SYNC_STATE_SCHEMA = "dot.agent.session.sync-state/v1"
FAILURE_DETAIL_LIMIT = 512
_UUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
_SESSION_ERRORS = (OSError, ValueError, TypeError, sqlite3.Error, DotError)
_SCHEMA_3_PREFIX = re.compile(rb'\{\s*"schema_version"\s*:\s*3\s*,')


@dataclass
class SyncOutcome:
    """Session counts: parsed (selected) sources publish as ingested, unchanged, retained, or skipped.

    ``retained_current_transcripts`` counts the retained sessions whose archived bundle is proven to
    hold the complete current transcript (only usage was kept), so it never exceeds ``retained``.
    """

    selected: int = 0
    ingested: int = 0
    unchanged: int = 0
    retained: int = 0
    retained_current_transcripts: int = 0
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


def _stored_sources(root: Path, agent: str) -> dict[str, SessionManifest]:
    """Snapshot manifests before parsing, including the publication generation."""
    stored: dict[str, SessionManifest] = {}
    directory = root / agent
    try:
        paths = list(directory.iterdir())
    except FileNotFoundError:
        return stored
    # glob() suppresses scan errors, hiding captures that publication must retain.
    for path in paths:
        if path.suffix != BUNDLE_SUFFIX:
            continue
        try:
            # Keep only capture metadata in memory, not every session's request samples.
            manifest = read_session_manifest(path, usage=False)
        except OSError, ValueError:
            # Publication reports the unreadable bundle for this session instead of skipping it.
            continue
        stored[manifest.session_id] = manifest
    return stored


def _upgrade_bundles(root: Path, adapter: AgentAdapter, fail: Callable[..., None]) -> None:
    directory = root / adapter.name
    try:
        paths = sorted(directory.iterdir())
    except OSError:
        # Absent needs nothing; the archive inspection that follows reports an unreadable one once.
        return
    for path in paths:
        if path.suffix != BUNDLE_SUFFIX or not is_valid_session_id(path.stem):
            continue
        try:
            # Peek at the version without decoding: a schema 3 manifest line holds every usage sample.
            with path.open("rb") as stream:
                legacy = _SCHEMA_3_PREFIX.match(stream.read(64)) is not None
            if legacy:
                upgrade_session_bundle(path)
        except _SESSION_ERRORS as error:
            fail(adapter, "upgrade session bundle", error, path.stem)


def _capture(
    adapter: AgentAdapter,
    session_id: str,
    parsed: ParsedSession,
    signature: str,
    previous: SessionManifest | None,
) -> tuple[SessionIngestionResult, DotError | None]:
    """Publish one parse; a malformed source or usage failure never replaces an archived measurement."""
    source = SessionSource(
        type=parsed.source_type,
        fingerprint=parsed.fingerprint,
        signature=signature,
        malformed=parsed.malformed,
        skipped=parsed.skipped,
        sidechain=parsed.sidechain,
        parent_session_id=parsed.parent_session_id,
    )
    generation = (previous.parser_version, previous.source_fingerprint) if previous else ("", "")
    if parsed.usage_error is None and not parsed.malformed:
        usage = parsed.usage.to_dict() if parsed.usage is not None else None
        return ingest_session(
            adapter.name, session_id, parsed.logs, source, usage=usage, expected_generation=generation
        ), None
    # Provider metric errors can quote source values: report the outcome, not the detail.
    # The transcript still publishes under the usual non-shrink rules, keeping any archived
    # measurement; an empty signature makes the next sync retry rather than skip this source.
    source.signature = ""
    result = ingest_session(adapter.name, session_id, parsed.logs, source, expected_generation=generation)
    cause = "usage extraction failed" if parsed.usage_error is not None else "malformed source records"
    if result.manifest.usage is not None:
        return result, DotError(f"{cause}; kept the archived usage")
    return result, DotError(f"{cause}; archived the transcript without usage")


def _stable_parse(
    adapter: AgentAdapter, path: Path, session_id: str, cwd: str, signature: str
) -> tuple[ParsedSession, str]:
    """Parse a source that stayed unchanged throughout, returning it with that source signature.

    A file source starts from the signature its skip decision used; an agent still writing gets one retry.
    A database parse reads one SQLite transaction snapshot, so a running agent writing other sessions
    cannot tear it; the pass-wide checkpoint, not this parse, must observe database changes.
    """
    if adapter.database:
        return adapter.parser(path, session_id, cwd), signature
    for attempt in range(2):
        observed = signature if not attempt else _source_signature(_source_files(adapter, path))[0]
        parsed = adapter.parser(path, session_id, cwd)
        if _source_signature(_source_files(adapter, path))[0] == observed:
            return parsed, observed
    raise DotError("session source changed during capture; retry sync")


def _database_checkpoint(root: Path, agent: str) -> str:
    """Only a successful, complete scan by the current parser can skip database reads."""
    try:
        document = json.loads((root / agent / SYNC_STATE_NAME).read_bytes())
    except OSError, ValueError, RecursionError:
        return ""
    if (
        not isinstance(document, dict)
        or document.get("schema") != SYNC_STATE_SCHEMA
        or document.get("parser_version") != SESSION_PARSER_VERSION
        or document.get("failed") != 0
    ):
        return ""
    signature = document.get("database_signature", "")
    return signature if isinstance(signature, str) else ""


def _write_sync_state(
    root: Path,
    agent: str,
    failed: int,
    database_signature: str = "",
    *,
    retained: int = 0,
) -> None:
    """Record a complete pass; filtered passes never prove the archive and record nothing."""
    document: dict[str, object] = {
        "schema": SYNC_STATE_SCHEMA,
        "synced_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "failed": failed,
        # Sessions that kept their archived copy; a persistent count can signal a parser gap.
        "retained": retained,
        "parser_version": SESSION_PARSER_VERSION,
        "database_signature": database_signature,
    }
    directory = private_directory(private_directory(root) / agent)
    write_private_file(directory / SYNC_STATE_NAME, (json.dumps(document) + "\n").encode())


def _stored_signature(adapter: AgentAdapter, signature: str, source_cwd: str, previous: SessionManifest | None) -> str:
    """Return the source evidence that proves an archived capture current."""
    if not (adapter.external_cwd and signature):
        return signature
    if source_cwd:
        # A workspace discovered after capture must recapture an unchanged transcript.
        return f"{signature};cwd={source_cwd}"
    if previous is not None and previous.source_signature.startswith(f"{signature};cwd="):
        # Pruned metadata must not recapture an unchanged transcript without its workspace.
        return previous.source_signature
    return signature


def _claim_subagents(
    adapter: AgentAdapter, candidates: list[SessionCandidate], stored: dict[str, SessionManifest]
) -> list[SessionCandidate]:
    """Qualify a Claude subagent ID that a second parent session also claims.

    Resuming a subagent in a forked parent writes `<new-parent>/subagents/agent-<id>.jsonl`;
    keep the first owner's stem and qualify later parents so neither overwrites the other.
    """
    if adapter.name != "claude":
        return candidates
    owners = {sid: manifest.parent_session_id for sid, manifest in stored.items() if manifest.parent_session_id}
    claimed: list[SessionCandidate] = []
    for session_id, source_cwd, path in candidates:
        if (parent_id := claude_parent_session_id(path)) and owners.setdefault(session_id, parent_id) != parent_id:
            session_id = f"{session_id}-{parent_id}"
        claimed.append((session_id, source_cwd, path))
    return claimed


@dataclass
class _AgentScan:
    """State one adapter's sessions share during a sync pass."""

    adapter: AgentAdapter
    source: Path
    stored: dict[str, SessionManifest] = field(default_factory=dict)
    counts: SyncOutcome = field(default_factory=SyncOutcome)
    # A database store has one signature for all its sessions, proven by the last complete pass.
    signature: str = ""
    modified: float = 0.0
    database_signature: str = ""
    checkpoint: str = ""
    announced: bool = False


@dataclass
class _SyncPass:
    """One sync invocation: its filters, reporting mode, and running totals."""

    state: State
    root: Path
    session: str
    cwd: str
    since: datetime | None
    dry_run: bool
    quiet: bool
    verbose: bool
    outcome: SyncOutcome = field(default_factory=SyncOutcome)

    @property
    def complete(self) -> bool:
        """Only an unfiltered pass proves every available session of an agent was considered."""
        return not (self.session or self.cwd or self.since or self.dry_run)

    def fail(self, adapter: AgentAdapter, operation: str, error: BaseException, session_id: str = "") -> None:
        self.outcome.failed += 1
        detail = bounded_failure(error, session_id)
        self.state.stderr.write(f"agent-session: failed to {operation} for {adapter.label}: {detail}\n")

    def sync_agent(self, adapter: AgentAdapter) -> None:
        if not self.dry_run and not self.session:
            # Schema 3 bundles embed usage in their manifest line: rewrite them once, even when the
            # provider deleted the source, so later metadata reads skip the usage samples.
            _upgrade_bundles(self.root, adapter, self.fail)
        # An unreadable legacy bundle fails the command, but never this pass's capture state: it would
        # otherwise clear a database checkpoint and force a full re-parse on every later sync.
        failed_before = self.outcome.failed
        try:
            source = _validated_source_root(self.state, adapter)
        except DotError as error:
            if not self.quiet:
                raise
            self.fail(adapter, "inspect the session source", error)
            return
        if source is None:
            return
        scan = _AgentScan(adapter, source, announced=not self.quiet)
        scanned = True
        try:
            if adapter.database:
                scan.signature, scan.modified = _source_signature(_source_files(adapter, source))
                scan.database_signature = f"{source.resolve()}:{scan.signature}"
                scan.checkpoint = _database_checkpoint(self.root, adapter.name)
            candidates = adapter.enumerate(source)
        except _SESSION_ERRORS as error:
            # One unreadable store must not block the adapters after it.
            self.fail(adapter, "scan sessions", error)
            candidates, scanned = [], False
        try:
            scan.stored = _stored_sources(self.root, adapter.name)
        except _SESSION_ERRORS as error:
            self.fail(adapter, "inspect the session archive", error)
            return
        for session_id, source_cwd, path in _claim_subagents(adapter, candidates, scan.stored):
            if self.session and session_id != self.session:
                continue
            try:
                captured = self._capture_session(scan, session_id, source_cwd, path)
            except _SESSION_ERRORS as error:
                # One malformed session must not block the sessions and adapters after it.
                self.fail(adapter, "capture session", error, session_id)
                continue
            if captured is not None:
                self._record(scan, session_id, *captured)
        for name in ("selected", "ingested", "unchanged", "retained", "retained_current_transcripts", "skipped"):
            setattr(self.outcome, name, getattr(self.outcome, name) + getattr(scan.counts, name))
        if not self.quiet and scanned:
            counts = scan.counts
            # Retention is decided during capture, which a dry run never reaches.
            summary = (
                f"{counts.selected} selected, {counts.unchanged} unchanged"
                if self.dry_run
                else f"{counts.ingested} ingested, {counts.unchanged} unchanged, {counts.retained} retained"
            )
            self.state.stderr.write(f"{adapter.name}: {summary}\n")
        if self.complete:
            self._write_state(scan, self.outcome.failed - failed_before)

    def _capture_session(
        self, scan: _AgentScan, session_id: str, source_cwd: str, path: Path
    ) -> tuple[SessionIngestionResult, DotError | None] | None:
        """Parse and publish one changed session; return nothing when it is unchanged or filtered out."""
        adapter = scan.adapter
        previous = scan.stored.get(session_id)
        if adapter.database:
            signature, modified = scan.signature, scan.modified
        else:
            signature, modified = _source_signature(_source_files(adapter, path))
        stored_signature = _stored_signature(adapter, signature, source_cwd, previous)
        if self.since and datetime.fromtimestamp(modified, UTC) < self.since:
            return None
        unchanged = (
            bool(scan.database_signature) and scan.database_signature == scan.checkpoint
            if adapter.database
            else bool(signature) and previous is not None and previous.source_signature == stored_signature
        )
        current_parser = previous is not None and previous.parser_version == SESSION_PARSER_VERSION
        if previous and current_parser and unchanged:
            if not self.cwd or previous.cwd == self.cwd:
                scan.counts.unchanged += 1
            return None
        if previous and not current_parser and not scan.announced:
            # Quiet callers (stats, usage) would otherwise sit silent through a full recapture.
            scan.announced = True
            self.state.stderr.write(
                f"agent-session: upgrading archived {adapter.name} sessions to parser "
                f"{SESSION_PARSER_VERSION}; this can take minutes\n"
            )
        # A grown transcript keeps the captured workspace after its metadata row is pruned.
        parse_cwd = source_cwd or (previous.cwd if adapter.external_cwd and previous else "")
        parsed, observed = _stable_parse(adapter, path, session_id, parse_cwd, signature)
        if not adapter.database and observed != signature:
            # The retry parsed a newer stable source; record that file evidence instead.
            stored_signature = observed + stored_signature[len(signature) :]
        parsed_cwd = next((record.cwd for record in parsed.logs if record.cwd), parse_cwd)
        if self.cwd and resolve_cwd(parsed_cwd) != self.cwd:
            return None
        scan.counts.selected += 1
        if self.dry_run:
            return None
        # Database stat changes belong to the shared checkpoint, not every bundle.
        bundle_signature = parsed.fingerprint if adapter.database else stored_signature
        return _capture(adapter, session_id, parsed, bundle_signature, previous)

    def _record(
        self, scan: _AgentScan, session_id: str, result: SessionIngestionResult, failure: DotError | None
    ) -> None:
        scan.stored[session_id] = replace(result.manifest, usage=None)
        counts = scan.counts
        setattr(counts, result.status, getattr(counts, result.status) + 1)
        if result.status == "retained" and result.current_transcript:
            counts.retained_current_transcripts += 1
        if not self.quiet and (result.status == "retained" or (self.verbose and result.status == "ingested")):
            self.state.stderr.write(report_ingestion(result) + "\n")
        if failure is not None:
            self.fail(scan.adapter, "capture session", failure, session_id)

    def _write_state(self, scan: _AgentScan, failed: int) -> None:
        database_signature = scan.database_signature
        try:
            if database_signature:
                current, _ = _source_signature(_source_files(scan.adapter, scan.source))
                # A failure, a retained session, or a database written mid-pass leaves the checkpoint unproven.
                if failed or scan.counts.retained or database_signature != f"{scan.source.resolve()}:{current}":
                    database_signature = ""
            _write_sync_state(self.root, scan.adapter.name, failed, database_signature, retained=scan.counts.retained)
        except OSError as error:
            self.fail(scan.adapter, "record sync state", error)


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
    verbose: bool = False,
) -> SyncOutcome:
    """Capture changed sessions; quiet mode reports only failures and never raises for them.

    Progress prints one line per retained session, which needs attention, but only verbose mode
    adds one per ingested session: a parser bump recaptures thousands, which would flood an agent's
    context. Lines carry the agent and counts, never session identities.
    """
    if agent in RETIRED_AGENTS:
        raise DotError(f"{agent} is retired: its archived sessions stay queryable, but dot no longer captures them")
    if agent and agent not in AGENT_ADAPTERS:
        raise DotError(f"unknown session agent {agent!r}")
    run = _SyncPass(state, session_store_root(), session, cwd, since, dry_run, quiet, verbose)
    for adapter in AGENT_ADAPTERS.values():
        if not agent or adapter.name == agent:
            run.sync_agent(adapter)
    outcome = run.outcome
    if not quiet:
        state.stderr.write(f"agent-session-sync: done ({outcome.failed} failed)\n")
    if as_json:
        document = {"schema": SYNC_SCHEMA, "parser_version": SESSION_PARSER_VERSION, "dry_run": dry_run}
        write_json(state.stdout, document | asdict(outcome))
    if outcome.failed and not quiet:
        raise DotError(f"session sync recorded {outcome.failed} failure(s); see errors above")
    return outcome


def bounded_failure(error: BaseException, session_id: str = "", limit: int = FAILURE_DETAIL_LIMIT) -> str:
    """Keep failure text short and free of session identities."""
    detail = str(error).replace(session_id, "<session>") if session_id else str(error)
    detail = _UUID.sub("<session>", detail)
    return " ".join(detail.split())[:limit]
