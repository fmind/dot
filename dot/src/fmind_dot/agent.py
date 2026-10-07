"""Command contracts for agent workflows."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import typer

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
    UsageRecord,
    aggregate_usage,
    iter_usage_records,
    list_usage_records,
    parse_flexible_time,
    write_usage_stats,
)
from fmind_dot.command_group import JsonOption, help_group
from fmind_dot.context_budget import register as register_context
from fmind_dot.errors import DotError
from fmind_dot.hooks import build_notification, notification_title, notification_workspace, send_notification
from fmind_dot.reporting import write_json, write_report_line
from fmind_dot.state import State, state_from

agent_app = help_group("Manage AI agent integrations and sessions")
register_context(agent_app)
session_app = help_group("Manage agent session logs")
hook_app = help_group("Run native agent notification hooks")
# Choices render in --help and Fish completions and are validated before any sync.
AgentName = StrEnum("AgentName", {name: name for name in AGENT_ADAPTERS})
SessionStatus = StrEnum("SessionStatus", {name: name for name in SESSION_STATUSES})


def _parse_time(value: str, option: str) -> datetime | None:
    try:
        return parse_flexible_time(value, end_of_day=option == "--until") if value else None
    except (ValueError, OverflowError) as error:
        raise typer.BadParameter("expected a duration (7d, 24h), UTC date, or timestamp", param_hint=option) from error


def _project(cwd: str) -> str:
    """Resolve a project filter; a path that cannot be expanded is a usage error, not a crash."""
    try:
        return resolve_cwd(cwd)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--project") from None


def _query(agent: str, cwd: str, identity: str, since: str, until: str) -> SessionQuery:
    query = SessionQuery(
        agent=agent,
        cwd=_project(cwd),
        identity=identity,
        since=_parse_time(since, "--since"),
        until=_parse_time(until, "--until"),
    )
    if query.since and query.until and query.since > query.until:
        raise typer.BadParameter("must not be after --until", param_hint="--since")
    return query


NoSyncOption = Annotated[
    bool, typer.Option("--no-sync", help="Report the archive as stored, without capturing changed sessions first")
]
# Shared filters keep one documented contract across session and report commands.
AgentOption = Annotated[AgentName | None, typer.Option("--agent", "--harness", "-a", help="Filter by agent")]
ProjectOption = Annotated[
    str, typer.Option("--project", "--cwd", help="Filter by project directory; relative paths resolve first")
]
SessionOption = Annotated[str, typer.Option("--session", help="Filter by session identity")]
LimitOption = Annotated[int, typer.Option("--limit", "-n", min=0, help="Maximum rows to return; 0 returns all")]
# Each date filter names its time basis: ingestion for archive queries, activity for reports.
_SINCE_VALUES = "duration (7d, 24h), UTC date, or timestamp"
_UNTIL_VALUES = "duration, UTC date (whole day), or timestamp"
SinceOption = Annotated[str, typer.Option("--since", help=f"Ingested since {_SINCE_VALUES}")]
UntilOption = Annotated[str, typer.Option("--until", help=f"Ingested until {_UNTIL_VALUES}")]


def _agent(agent: AgentName | None) -> str:
    """Typer rejects a misspelled agent before a report syncs, so a typo never becomes an all-agent capture."""
    return str(agent) if agent else ""


@session_app.command(
    "list",
    help="List archived sessions, newest ingestion first",
    epilog="Example: dot agent session list --agent claude --since 7d --status partial --json",
)
def session_list(
    context: typer.Context,
    agent: AgentOption = None,
    cwd: ProjectOption = "",
    identity: SessionOption = "",
    since: SinceOption = "",
    until: UntilOption = "",
    limit: LimitOption = 50,
    as_json: JsonOption = False,
    status: Annotated[
        list[SessionStatus] | None, typer.Option("--status", help="Filter by session status; repeatable")
    ] = None,
) -> None:
    state = state_from(context)
    selected_statuses = {str(item) for item in status or ()}
    query = _query(_agent(agent), cwd, identity, since, until)
    summaries = query_session_summaries(
        query,
        validate_content="invalid" in selected_statuses,
        statuses=selected_statuses,
        limit=limit or None,
    )
    if as_json:
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


@session_app.command(
    "show",
    help="Print one archived session as JSON; --content adds its records",
    epilog="Example: dot agent session show SESSION_ID --content --role user --tail 20. "
    "Transcripts can be megabytes: bound --content with --tail or --role.",
)
def session_show(
    context: typer.Context,
    identity: Annotated[str, typer.Argument(help="Session identity, as session list prints it")],
    agent: AgentOption = None,
    cwd: ProjectOption = "",
    since: SinceOption = "",
    until: UntilOption = "",
    content: Annotated[bool, typer.Option("--content", help="Include prompt and response content")] = False,
    role: Annotated[
        Literal["user", "assistant"] | None, typer.Option("--role", help="With --content, keep only this role")
    ] = None,
    tail: Annotated[
        int, typer.Option("--tail", min=0, help="With --content, keep only the last N records; 0 keeps all")
    ] = 0,
) -> None:
    state = state_from(context)
    if (role or tail) and not content:
        raise typer.BadParameter("--role and --tail select --content records", param_hint="--content")
    query = _query(_agent(agent), cwd, identity, since, until)
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
        raise DotError(
            f"archived transcript for {summary.agent} session {summary.session_id} is unreadable; "
            f"move {session_bundle_path(summary.agent, summary.session_id)} aside (sync skips an unchanged source), "
            f"then recapture it with: dot agent session sync --agent {summary.agent} --session {summary.session_id}"
        )


@session_app.command(
    "sync",
    help="Capture new and changed sessions from configured agent sources",
    epilog="Progress goes to stderr; exit 1 after any failed session, once the others are captured.",
)
def session_sync(
    context: typer.Context,
    agent: Annotated[
        AgentName | None, typer.Option("--agent", "--harness", "-a", help="Synchronize one adapter")
    ] = None,
    session: Annotated[str, typer.Option("--session", help="Synchronize one session identity")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd", help="Filter by resolved project path")] = "",
    since: Annotated[str, typer.Option("--since", help=f"Only sources modified since {_SINCE_VALUES}")] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Inspect candidates without writing archives or usage")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    sync_sessions(
        state_from(context),
        agent=_agent(agent),
        session=session,
        cwd=_project(cwd),
        since=_parse_time(since, "--since"),
        dry_run=dry_run,
        as_json=as_json,
    )


def _print_prompt_statistics(state: State, document: dict[str, Any]) -> None:
    def write(text: str = "") -> None:
        write_report_line(state.stdout, text)

    write()
    write(f"Prompt activity · {document['prompts']:,} archived user messages")
    write("Conversation timestamps (UTC); user messages may include injected context.")
    if not document["rows"]:
        write("No prompt records found for this selection.")
    for row in document["rows"]:
        write()
        write(row["agent"])
        if row["project"]:
            write(f"  Project: {row['project']}")
        write(f"  Sessions: {row['sessions']:,} · Prompts: {row['prompts']:,} · Responses: {row['responses']:,}")
        write(f"  Active days: {row['active_days']:,} · Words: {row['words']:,} · Characters: {row['characters']:,}")
        write(f"  Prompt length (characters): median {row['median_characters']:,} · p95 {row['p95_characters']:,}")
        if row["partial_sessions"]:
            write(f"  Partial sessions: {row['partial_sessions']:,}")
    if document["excluded_sessions"] or document["invalid_timestamps"]:
        write(
            f"Excluded sessions: {document['excluded_sessions']:,} · Invalid timestamps: {document['invalid_timestamps']:,}"
        )
    write(f"Prompt coverage: {'complete' if document['complete'] else 'INCOMPLETE'} within the selected archive.")


@hook_app.command("notify", help="Send a desktop notification for a native agent event")
def hook_notify(
    context: typer.Context,
    agent: Annotated[str, typer.Argument(help="Agent adapter name")],
    event: Annotated[str, typer.Argument(help="Native hook event name")],
) -> None:
    state = state_from(context, require_config=False)
    try:
        # Consume the hook payload so re-entrant and mid-turn events remain quiet.
        workspace = notification_workspace(state.stdin, agent, event)
        if workspace is None:
            return
        cwd = Path(workspace) if workspace else None
        send_notification(state, build_notification(agent, event, cwd, title=notification_title(state.runner)))
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


@agent_app.command(
    "stats",
    help="Sync changed sessions (unless --no-sync), then report prompts, tokens, costs, and API equivalents",
    epilog="Examples: dot agent stats --since 7d --tokens-only --json · dot agent stats --sessions -n 10 --since 7d · "
    "dot agent stats --billing --agent codex. Exit 1 when prompt statistics are incomplete; JSON is still printed.",
)
def agent_stats(
    context: typer.Context,
    agent: AgentOption = None,
    since: Annotated[str, typer.Option("--since", help=f"Active since {_SINCE_VALUES}")] = "",
    until: Annotated[str, typer.Option("--until", help=f"Active until {_UNTIL_VALUES}")] = "",
    cwd: ProjectOption = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m", help="Group usage by model")] = False,
    by_project: Annotated[bool, typer.Option("--by-project", help="Group prompts and usage by project")] = False,
    as_json: JsonOption = False,
    monthly: Annotated[bool, typer.Option("--monthly", help="Group usage by calendar month in UTC")] = False,
    billing: Annotated[bool, typer.Option("--billing", help="Group usage by configured subscription cycles")] = False,
    tokens_only: Annotated[
        bool, typer.Option("--tokens-only", help="Skip prompt analysis for a quick usage report")
    ] = False,
    prompts_only: Annotated[
        bool, typer.Option("--prompts-only", help="Skip token analysis and report prompt activity")
    ] = False,
    no_sync: NoSyncOption = False,
    sessions: Annotated[
        bool, typer.Option("--sessions", help="List per-session usage, newest activity first, instead of totals")
    ] = False,
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=0, help="With --sessions, maximum rows; 0 returns all")
    ] = 50,
) -> None:
    state = state_from(context)
    selected = _agent(agent)
    if sessions and (by_model or by_project or monthly or billing or tokens_only or prompts_only):
        raise typer.BadParameter("lists sessions; drop the grouping and --*-only options", param_hint="--sessions")
    if tokens_only and prompts_only:
        raise typer.BadParameter("cannot be combined with --prompts-only", param_hint="--tokens-only")
    if monthly and billing:
        raise typer.BadParameter("cannot be combined with --billing", param_hint="--monthly")
    if prompts_only and (monthly or billing or by_model):
        raise typer.BadParameter(
            "--monthly, --billing, and --by-model require token statistics", param_hint="--prompts-only"
        )
    query = _query(selected, cwd, "", since, until)
    if not no_sync:
        sync_sessions(state, agent=selected, quiet=True)
    if sessions:
        records = list_usage_records(
            iter_usage_records(), harness=selected, limit=limit, since=query.since, until=query.until, cwd=query.cwd
        )
        if as_json:
            document = {"schema": "dot.agent.stats.sessions/v1", "records": [record.to_dict() for record in records]}
            write_json(state.stdout, document)
        else:
            _print_session_usage(state, records)
        return
    prompts = None if tokens_only else prompt_statistics(query, by_project=by_project)
    rows = (
        []
        if prompts_only
        else aggregate_usage(
            iter_usage_records(),
            harness=selected,
            since=query.since,
            until=query.until,
            cwd=query.cwd,
            by_model=by_model,
            by_project=by_project,
            pricing=state.config.agent.pricing,
            monthly=monthly,
            billing=billing,
            subscriptions=state.config.agent.subscriptions,
        )
    )
    coverage = " without a sync (--no-sync)" if no_sync else " after an incremental sync"
    if as_json:
        write_json(
            state.stdout,
            {
                "schema": "dot.agent.stats/v3",
                "coverage": f"Archived records{coverage}. Prompt and usage coverage can differ.",
                "prompts": prompts,
                "usage": [row.to_dict() for row in rows],
            },
        )
    else:
        write_report_line(state.stdout, f"Archived records{coverage}.")
        if prompts is not None:
            _print_prompt_statistics(state, prompts)
        if not prompts_only:
            write_usage_stats(state.stdout, rows, by_model=by_model)
    if prompts is not None and not prompts["complete"]:
        raise DotError("prompt statistics are incomplete; inspect excluded sessions and partial counts")


@agent_app.command(
    "doctor",
    help="Check discovery, notify hooks, session sync, and archive readability per agent",
    epilog="Exit 1 when any agent is unhealthy; each failing agent names its next command.",
)
def agent_doctor(
    context: typer.Context,
    agent: Annotated[
        AgentName | None, typer.Option("--agent", "--harness", "-a", help="Inspect only one agent")
    ] = None,
    as_json: JsonOption = False,
) -> None:
    run_agent_doctor(state_from(context), as_json=as_json, agent=_agent(agent))


agent_app.add_typer(hook_app, name="hook", hidden=True)


agent_app.add_typer(session_app, name="session")
