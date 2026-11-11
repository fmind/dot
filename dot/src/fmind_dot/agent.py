"""Command contracts for agent workflows."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from fmind_dot.agent_doctor import run_agent_doctor
from fmind_dot.archive.parsers import AGENT_ADAPTERS, resolve_cwd
from fmind_dot.archive.query import (
    SESSION_STATUSES,
    SessionQuery,
    query_session_summaries,
    show_session,
)
from fmind_dot.archive.statistics import prompt_statistics
from fmind_dot.archive.store import session_bundle_path
from fmind_dot.archive.sync import bounded_failure, sync_sessions
from fmind_dot.archive.usage import (
    RETIRED_AGENTS,
    USAGE_TIME_BASIS,
    UsageRecord,
    aggregate_usage,
    iter_usage_records,
    list_usage_records,
    parse_flexible_time,
    write_usage_stats,
)
from fmind_dot.command import Parser, add_json, non_negative
from fmind_dot.config import NotifyConfig
from fmind_dot.context_budget import register as register_context
from fmind_dot.errors import DotError, UsageError
from fmind_dot.hooks import build_notification, notification_workspace, send_notification, zellij_pane
from fmind_dot.reporting import write_json, write_report_line
from fmind_dot.state import State

# Choices render in --help and Fish completions and are validated before any sync, so a typo never becomes
# an all-agent capture. Retired agents stay selectable where their archived sessions are queried; the doctor
# inspects live adapters only.
_AGENTS = (*AGENT_ADAPTERS, *RETIRED_AGENTS)
# Each date filter names its time basis: ingestion for archive queries, activity for reports.
_SINCE_VALUES = "duration (7d, 24h), UTC date, or timestamp"
_UNTIL_VALUES = "duration, UTC date (whole day), or timestamp"


def _parse_time(value: str, option: str) -> datetime | None:
    try:
        return parse_flexible_time(value, end_of_day=option == "--until") if value else None
    except (ValueError, OverflowError) as error:
        raise UsageError(f"{option}: expected a duration (7d, 24h), UTC date, or timestamp") from error


def _project(cwd: str) -> str:
    """Resolve a project filter; a path that cannot be expanded is a usage error, not a crash."""
    try:
        return resolve_cwd(cwd)
    except ValueError as error:
        raise UsageError(f"--project: {error}") from None


def _query(agent: str, cwd: str, identity: str, since: str, until: str) -> SessionQuery:
    query = SessionQuery(
        agent=agent,
        cwd=_project(cwd),
        identity=identity,
        since=_parse_time(since, "--since"),
        until=_parse_time(until, "--until"),
    )
    if query.since and query.until and query.since > query.until:
        raise UsageError("--since: must not be after --until")
    return query


def _add_filters(parser: Parser, *, basis: str, session: bool = False) -> None:
    """Shared filters keep one documented contract across session and report commands."""
    parser.add_argument("-a", "--agent", choices=_AGENTS, default="", help="Filter by agent")
    parser.add_argument(
        "--project",
        dest="cwd",
        default="",
        metavar="PATH",
        help="Filter by project directory; relative paths resolve first",
    )
    if session:
        parser.add_argument("--session", dest="identity", default="", metavar="ID", help="Filter by session identity")
    parser.add_argument("--since", default="", metavar="WHEN", help=f"{basis} since {_SINCE_VALUES}")
    parser.add_argument("--until", default="", metavar="WHEN", help=f"{basis} until {_UNTIL_VALUES}")


def _session_list(state: State, args: argparse.Namespace) -> None:
    selected_statuses = set(args.status)
    query = _query(args.agent, args.cwd, args.identity, args.since, args.until)
    summaries = query_session_summaries(
        query,
        validate_content="invalid" in selected_statuses,
        statuses=selected_statuses,
        limit=args.limit or None,
    )
    if args.as_json:
        write_json(
            state.stdout,
            {
                "schema": "dot.agent.session.list/v2",
                "sessions": [summary.to_dict(include_records=False) for summary in summaries],
            },
        )
        return
    for summary in summaries:
        state.stdout.write(
            f"{summary.ingested_at} {summary.agent} {summary.session_id} records={summary.record_count} "
            f"status={','.join(summary.status)} cwd={summary.cwd}\n"
        )


def _session_show(state: State, args: argparse.Namespace) -> None:
    content, role, tail = args.content, args.role, args.tail
    if (role or tail) and not content:
        raise UsageError("--role and --tail select --content records")
    query = _query(args.agent, args.cwd, args.identity, args.since, args.until)
    summary = show_session(query, include_content=content)
    if role:
        summary.records = [record for record in summary.records if record.role == role]
    if tail:
        summary.records = summary.records[-tail:]
    write_json(
        state.stdout, {"schema": "dot.agent.session.show/v2", "session": summary.to_dict(include_records=content)}
    )
    # The metadata above stays useful, but requested content that cannot be read is a failure.
    if content and "invalid" in summary.status:
        if summary.agent in RETIRED_AGENTS:
            raise DotError(
                f"archived transcript for {summary.agent} session {summary.session_id} is unreadable, and dot no "
                f"longer captures {summary.agent}: restore {session_bundle_path(summary.agent, summary.session_id)} "
                "from a backup instead of moving it aside"
            )
        raise DotError(
            f"archived transcript for {summary.agent} session {summary.session_id} is unreadable; "
            f"move {session_bundle_path(summary.agent, summary.session_id)} aside (sync skips an unchanged source), "
            f"then recapture it with: dot agent session sync --agent {summary.agent} --session {summary.session_id}"
        )


def _session_sync(state: State, args: argparse.Namespace) -> None:
    sync_sessions(
        state,
        agent=args.agent,
        session=args.session,
        cwd=_project(args.cwd),
        since=_parse_time(args.since, "--since"),
        dry_run=args.dry_run,
        as_json=args.as_json,
        verbose=args.verbose,
    )


def _print_prompt_statistics(state: State, document: dict[str, Any]) -> None:
    def write(text: str = "") -> None:
        write_report_line(state.stdout, text)

    write()
    write(f"Prompt activity · {document['prompts']:,} archived user messages")
    write("Conversation timestamps (UTC); Claude meta turns are counted as injected, not prompts.")
    if not document["rows"]:
        write("No prompt records found for this selection.")
    for row in document["rows"]:
        write()
        write(row["agent"])
        if row["project"]:
            write(f"  Project: {row['project']}")
        write(f"  Sessions: {row['sessions']:,} · Prompts: {row['prompts']:,} · Responses: {row['responses']:,}")
        if row["injected"]:
            write(f"  Injected (Claude meta): {row['injected']:,}")
        write(f"  Active days: {row['active_days']:,} · Words: {row['words']:,} · Characters: {row['characters']:,}")
        write(f"  Prompt length (characters): median {row['median_characters']:,} · p95 {row['p95_characters']:,}")
        if row["partial_sessions"]:
            write(f"  Partial sessions: {row['partial_sessions']:,}")
    if document["excluded_sessions"] or document["invalid_timestamps"]:
        write(
            f"Excluded sessions: {document['excluded_sessions']:,} · Invalid timestamps: {document['invalid_timestamps']:,}"
        )
    write(f"Prompt coverage: {'complete' if document['complete'] else 'INCOMPLETE'} within the selected archive.")


def _hook_notify(state: State, args: argparse.Namespace) -> None:
    agent, event = args.agent, args.event
    try:
        # Consume the hook payload so re-entrant and mid-turn events remain quiet.
        workspace = notification_workspace(state.stdin, agent, event, runner=state.runner)
        if workspace is None:
            return
        cwd = Path(workspace) if workspace else None
        try:
            settings = state.config.agent.notify
        except (OSError, ValueError, DotError) as error:
            # A broken config must not silence the turn alert; it only loses its overrides.
            state.stderr.write(f"agent hook notify used default settings: {bounded_failure(error)}\n")
            settings = NotifyConfig()
        pane = zellij_pane(state.runner) if settings.tab or settings.title else None
        notification = build_notification(agent, event, cwd, pane=pane, tab=settings.tab, title=settings.title)
        send_notification(state, notification, sound=settings.sound)
    except (OSError, ValueError, DotError) as error:
        # Notifications are best effort: a failing hook would surface as a failed agent turn.
        state.stderr.write(f"agent hook notify failed: {bounded_failure(error)}\n")


def _print_session_usage(state: State, records: list[UsageRecord]) -> None:
    if not records:
        state.stdout.write("No usage records found.\n")
        return
    state.stdout.write("TIMESTAMP\tAGENT\tSESSION ID\tMODEL\tTOTAL TOKENS\tCOST (USD)\n")
    for record in records:
        cost = f"${record.cost_usd:.4f}" if record.cost_known or record.cost_usd else "unknown"
        state.stdout.write(
            f"{record.timestamp[:19]}\t{record.harness}\t{record.session_id}\t{record.model or '-'}\t"
            f"{record.total_tokens:,}\t{cost}\n"
        )


def _agent_stats(state: State, args: argparse.Namespace) -> None:
    selected, as_json, no_sync, limit = args.agent, args.as_json, args.no_sync, args.limit
    by_model, by_project, monthly = args.by_model, args.by_project, args.monthly
    sessions, tokens_only, prompts_only = args.sessions, args.tokens_only, args.prompts_only
    if sessions and (by_model or by_project or monthly or tokens_only or prompts_only):
        raise UsageError("--sessions: lists sessions; drop the grouping and --*-only options")
    if tokens_only and prompts_only:
        raise UsageError("--tokens-only: cannot be combined with --prompts-only")
    if prompts_only and (monthly or by_model):
        raise UsageError("--prompts-only: --monthly and --by-model require token statistics")
    query = _query(selected, args.cwd, "", args.since, args.until)
    # A retired agent has nothing to capture: report its archive as stored.
    synced = not no_sync and selected not in RETIRED_AGENTS
    if synced:
        sync_sessions(state, agent=selected, quiet=True)
    if sessions:
        records = list_usage_records(
            iter_usage_records(query.since, query.until),
            harness=selected,
            limit=limit,
            since=query.since,
            until=query.until,
            cwd=query.cwd,
        )
        if as_json:
            document = {"schema": "dot.agent.stats.sessions/v1", "records": [record.to_dict() for record in records]}
            write_json(state.stdout, document)
        else:
            _print_session_usage(state, records)
        return
    prompts = None if tokens_only else prompt_statistics(query, by_project=by_project)
    rates = state.config.agent.pricing
    rows = (
        []
        if prompts_only
        else aggregate_usage(
            iter_usage_records(query.since, query.until),
            harness=selected,
            since=query.since,
            until=query.until,
            cwd=query.cwd,
            by_model=by_model,
            by_project=by_project,
            pricing=rates,
            monthly=monthly,
        )
    )
    coverage = (
        " after an incremental sync"
        if synced
        else " without a sync (--no-sync)"
        if no_sync
        else f" without a sync ({selected} is retired)"
    )
    if as_json:
        write_json(
            state.stdout,
            {
                "schema": "dot.agent.stats/v4",
                "coverage": f"Archived records{coverage}. Prompt and usage coverage can differ.",
                # Shared by every usage row, so stated once instead of per row.
                "time_basis": None if prompts_only else USAGE_TIME_BASIS,
                "pricing": None
                if prompts_only
                else {"as_of": rates.as_of, "basis": rates.basis, "sources": rates.sources},
                "prompts": prompts,
                "usage": [row.to_dict() for row in rows],
            },
        )
    else:
        write_report_line(state.stdout, f"Archived records{coverage}.")
        if prompts is not None:
            _print_prompt_statistics(state, prompts)
        if not prompts_only:
            write_usage_stats(state.stdout, rows, by_model=by_model, pricing=rates)
    if prompts is not None and not prompts["complete"]:
        raise DotError("prompt statistics are incomplete; inspect excluded sessions and partial counts")


def _agent_doctor(state: State, args: argparse.Namespace) -> None:
    run_agent_doctor(state, as_json=args.as_json, agent=args.agent)


def _register_session(commands: Parser) -> None:
    group = commands.group("session", "Manage agent session logs")
    listing = group.command(
        "list",
        "List archived sessions, newest ingestion first",
        _session_list,
        epilog="Example: dot agent session list --agent claude --since 7d --status partial --json",
    )
    _add_filters(listing, basis="Ingested", session=True)
    listing.add_argument(
        "-n", "--limit", type=non_negative, default=50, metavar="N", help="Maximum rows to return; 0 returns all"
    )
    add_json(listing)
    listing.add_argument(
        "--status", action="append", choices=SESSION_STATUSES, default=[], help="Filter by session status; repeatable"
    )
    show = group.command(
        "show",
        "Print one archived session as JSON; --content adds its records",
        _session_show,
        epilog="Example: dot agent session show SESSION_ID --content --role user --tail 20. "
        "Transcripts can be megabytes: bound --content with --tail or --role.",
    )
    show.add_argument("identity", metavar="SESSION", help="Session identity, as session list prints it")
    _add_filters(show, basis="Ingested")
    show.add_argument("--content", action="store_true", help="Include prompt and response content")
    show.add_argument("--role", choices=("user", "assistant"), help="With --content, keep only this role")
    show.add_argument(
        "--tail",
        type=non_negative,
        default=0,
        metavar="N",
        help="With --content, keep only the last N records; 0 keeps all",
    )
    sync = group.command(
        "sync",
        "Capture new and changed sessions from configured agent sources",
        _session_sync,
        epilog=(
            "Progress goes to stderr: one summary per agent plus each retained session; --verbose also lists "
            "every ingested session. Exit 1 after any failed session, once the others are captured."
        ),
    )
    sync.add_argument("-a", "--agent", choices=_AGENTS, default="", help="Synchronize one adapter")
    sync.add_argument("--session", default="", metavar="ID", help="Synchronize one session identity")
    sync.add_argument("--project", dest="cwd", default="", metavar="PATH", help="Filter by resolved project path")
    sync.add_argument("--since", default="", metavar="WHEN", help=f"Only sources modified since {_SINCE_VALUES}")
    sync.add_argument("--dry-run", action="store_true", help="Inspect candidates without writing archives or usage")
    add_json(sync)
    sync.add_argument("-v", "--verbose", action="store_true", help="Also list every ingested session")


def _register_stats(commands: Parser) -> None:
    stats = commands.command(
        "stats",
        "Sync changed sessions (unless --no-sync), then report prompts, tokens, costs, and API equivalents",
        _agent_stats,
        epilog="Examples: dot agent stats --since 7d --tokens-only --json · dot agent stats --sessions -n 10 --since 7d "
        "· dot agent stats --monthly --agent agy. Exit 1 when prompt statistics are incomplete; JSON is still printed.",
    )
    _add_filters(stats, basis="Active")
    stats.add_argument("-m", "--by-model", action="store_true", help="Group usage by model")
    stats.add_argument("--by-project", action="store_true", help="Group prompts and usage by project")
    add_json(stats)
    stats.add_argument("--monthly", action="store_true", help="Group usage by calendar month in UTC")
    stats.add_argument("--tokens-only", action="store_true", help="Skip prompt analysis for a quick usage report")
    stats.add_argument("--prompts-only", action="store_true", help="Skip token analysis and report prompt activity")
    stats.add_argument(
        "--no-sync",
        action="store_true",
        help="Report the archive as stored, without capturing changed sessions first",
    )
    stats.add_argument(
        "--sessions", action="store_true", help="List per-session usage, newest activity first, instead of totals"
    )
    stats.add_argument(
        "-n",
        "--limit",
        type=non_negative,
        default=50,
        metavar="N",
        help="With --sessions, maximum rows; 0 returns all",
    )


def register(commands: Parser) -> None:
    group = commands.group("agent", "Manage AI agent integrations and sessions")
    register_context(group)
    doctor = group.command(
        "doctor",
        "Check discovery, notify hooks, session sync, and archive readability per agent",
        _agent_doctor,
        epilog="Exit 1 when any agent is unhealthy; each failing agent names its next command.",
    )
    doctor.add_argument("-a", "--agent", choices=tuple(AGENT_ADAPTERS), default="", help="Inspect only one agent")
    add_json(doctor)
    # Native harness hooks call this; it stays out of everyday help and never needs a valid dot.yaml.
    hook = group.group("hook", "Run native agent notification hooks", hidden=True)
    notify = hook.command("notify", "Send a desktop notification for a native agent event", _hook_notify, config=False)
    notify.add_argument("agent", help="Agent adapter name")
    notify.add_argument("event", help="Native hook event name")
    _register_session(group)
    _register_stats(group)
