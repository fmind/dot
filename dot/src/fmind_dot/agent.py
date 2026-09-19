"""Command contracts for agent workflows."""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from typer import _click

from fmind_dot.agent_doctor import run_agent_doctor
from fmind_dot.archive.parsers import AGENT_ADAPTERS, resolve_cwd
from fmind_dot.archive.query import (
    SESSION_STATUSES,
    SessionQuery,
    export_sessions,
    query_session_summaries,
    show_session,
)
from fmind_dot.archive.statistics import prompt_statistics, session_statistics
from fmind_dot.archive.store import ensure_session_store
from fmind_dot.archive.sync import bounded_failure, sync_sessions
from fmind_dot.archive.usage import (
    aggregate_usage,
    iter_usage_records,
    list_usage_records,
    load_usage_records,
    parse_flexible_time,
    show_usage_record,
    write_usage_stats,
)
from fmind_dot.command_group import JsonOption, help_group
from fmind_dot.context_budget import register as register_context
from fmind_dot.errors import DotError
from fmind_dot.hooks import notification_workspace
from fmind_dot.reporting import write_report_line
from fmind_dot.state import State, state_from
from fmind_dot.system import build_notification, notification_title, send_notification

agent_app = help_group("Manage AI agent integrations and sessions")
register_context(agent_app)
session_app = help_group("Manage agent session logs")
hook_app = help_group("Run native agent notification hooks")
usage_app = help_group("Inspect token usage from the session archive")


def _parse_time(value: str, option: str) -> datetime | None:
    try:
        return parse_flexible_time(value, end_of_day=option == "--until") if value else None
    except (ValueError, OverflowError) as error:
        raise typer.BadParameter("expected a duration (7d, 24h), UTC date, or timestamp", param_hint=option) from error


def _query(agent: str, cwd: str, identity: str, since: str, until: str) -> SessionQuery:
    query = SessionQuery(
        agent=agent,
        cwd=resolve_cwd(cwd),
        identity=identity,
        since=_parse_time(since, "--since"),
        until=_parse_time(until, "--until"),
    )
    if query.since and query.until and query.since > query.until:
        raise typer.BadParameter("must not be after --until", param_hint="--since")
    return query


def _refresh(state: State, agent: str = "") -> None:
    """Capture changed sessions before a report; failures warn on stderr without blocking it."""
    sync_sessions(state, agent=agent if agent in AGENT_ADAPTERS else "", quiet=True)


@session_app.command("list", help="List archived sessions")
def session_list(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a", help="Filter by agent")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project", help="Filter by exact project/CWD")] = "",
    identity: Annotated[str, typer.Option("--session", help="Filter by session identity")] = "",
    since: Annotated[str, typer.Option("--since", help="Duration (7d, 24h), UTC date, or timestamp")] = "",
    until: Annotated[str, typer.Option("--until", help="Duration (7d, 24h), UTC date, or timestamp")] = "",
    limit: Annotated[int, typer.Option("--limit", "-n", min=0, help="Maximum rows to return; 0 returns all")] = 50,
    as_json: JsonOption = False,
    status: Annotated[list[str] | None, typer.Option("--status", help="Filter by session status")] = None,
) -> None:
    state = state_from(context)
    selected_statuses = set(status or ())
    unknown = selected_statuses - set(SESSION_STATUSES)
    if unknown:
        raise typer.BadParameter(
            f"unknown status {min(unknown)!r}; choose {', '.join(SESSION_STATUSES)}", param_hint="--status"
        )
    query = _query(agent, cwd, identity, since, until)
    ensure_session_store(state.stderr)
    summaries = query_session_summaries(
        query,
        validate_content="invalid" in selected_statuses,
        statuses=selected_statuses,
        limit=limit or None,
    )
    if as_json:
        json.dump(
            {
                "schema": "dot.agent.session.list/v2",
                "sessions": [summary.to_dict(include_records=False) for summary in summaries],
            },
            state.stdout,
            ensure_ascii=False,
            indent=2,
        )
        state.stdout.write("\n")
        return
    for summary in summaries:
        state.stdout.write(
            f"{summary.ingested_at} {summary.agent} {summary.session_id} records={summary.record_count} "
            f"status={','.join(summary.status)} cwd={summary.cwd}\n"
        )


@session_app.command("show", help="Show one archived session")
def session_show(
    context: typer.Context,
    identity: Annotated[str, typer.Argument(help="Session identity")] = "",
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project")] = "",
    session: Annotated[str, typer.Option("--session")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    content: Annotated[bool, typer.Option("--content", help="Include prompt and response content")] = False,
) -> None:
    state = state_from(context)
    if not session and not identity:
        raise _click.exceptions.UsageError("show requires a session identity")
    if session and identity and session != identity:
        raise _click.exceptions.UsageError("choose either the identity argument or --session")
    query = _query(agent, cwd, session or identity, since, until)
    ensure_session_store(state.stderr)
    summary = show_session(query, include_content=content)
    json.dump(
        {"schema": "dot.agent.session.show/v2", "session": summary.to_dict(include_records=content)},
        state.stdout,
        ensure_ascii=False,
        indent=2,
    )
    state.stdout.write("\n")


@session_app.command("export", help="Export archived sessions")
def session_export(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a")] = "",
    cwd: Annotated[str, typer.Option("--cwd", "--project")] = "",
    session: Annotated[str, typer.Option("--session")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    format: Annotated[Literal["json", "ndjson"], typer.Option("--format")] = "json",  # noqa: A002 - CLI flag name
    content: Annotated[bool, typer.Option("--content")] = False,
    redact_content: Annotated[bool, typer.Option("--redact-content")] = False,
) -> None:
    if content and redact_content:
        raise _click.exceptions.UsageError("choose --content or --redact-content")
    state = state_from(context)
    query = _query(agent, cwd, session, since, until)
    ensure_session_store(state.stderr)
    export_sessions(
        state.stdout,
        query,
        format=format,
        include_content=content,
        redact_content=redact_content,
    )


@session_app.command("sync", help="Capture new and changed sessions from configured agent sources")
def session_sync(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a", help="Synchronize one adapter")] = "",
    session: Annotated[str, typer.Option("--session", help="Synchronize one session identity")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd", help="Filter by resolved project path")] = "",
    since: Annotated[
        str, typer.Option("--since", help="Only sources modified since duration, UTC date, or timestamp")
    ] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Inspect candidates without writing archives or usage")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    sync_sessions(
        state_from(context),
        agent=agent,
        session=session,
        cwd=resolve_cwd(cwd),
        since=_parse_time(since, "--since"),
        dry_run=dry_run,
        as_json=as_json,
    )


def _print_statistics(state: State, document: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        state.stdout.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    else:
        for key, value in document.items():
            state.stdout.write(
                f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, dict | list) else value}\n"
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


@session_app.command("stats", help="Count archived sessions, records, archive bytes, and status")
def session_stats(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    since: Annotated[str, typer.Option("--since", help="Filter latest ingestion timestamps")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    as_json: JsonOption = False,
) -> None:
    state = state_from(context)
    query = _query(agent, cwd, "", since, until)
    ensure_session_store(state.stderr)
    _print_statistics(state, session_statistics(query), as_json=as_json)


@hook_app.command("notify", help="Send a desktop notification for a native agent event")
def hook_notify(
    context: typer.Context,
    agent: Annotated[str, typer.Argument()],
    event: Annotated[str, typer.Argument()],
) -> None:
    state = state_from(context)
    try:
        # Consume the hook payload so re-entrant and mid-turn events remain quiet.
        workspace = notification_workspace(state.stdin, agent)
        if workspace is None:
            return
        cwd = Path(workspace) if workspace else None
        send_notification(state, build_notification(agent, event, cwd, title=notification_title(state.runner)))
    except (OSError, ValueError, DotError) as error:
        # Notifications are best effort: a failing hook would surface as a failed agent turn.
        state.stderr.write(f"agent hook notify failed: {bounded_failure(error)}\n")


@usage_app.command("list", help="Sync changed sessions, then list session usage measurements")
def usage_list(
    context: typer.Context,
    harness: Annotated[str, typer.Option("--agent", "--harness", "-a", help="Filter by agent")] = "",
    limit: Annotated[int, typer.Option("--limit", "-n", min=0, help="Maximum rows to return; 0 returns all")] = 50,
    as_json: JsonOption = False,
) -> None:
    state = state_from(context)
    _refresh(state, harness)
    records = list_usage_records(load_usage_records(), harness=harness, limit=limit)
    if as_json:
        json.dump(
            {"schema": "dot.agent.usage.list/v1", "records": [record.to_dict() for record in records]},
            state.stdout,
            ensure_ascii=False,
            indent=2,
        )
        state.stdout.write("\n")
        return
    if not records:
        state.stdout.write("No usage records found.\n")
        return
    state.stdout.write("TIMESTAMP\tAGENT\tSESSION ID\tMODEL\tTOTAL TOKENS\tCOST (USD)\n")
    for record in records:
        state.stdout.write(
            f"{record.timestamp[:19]}\t{record.harness}\t{record.session_id}\t{record.model or '-'}\t"
            f"{record.total_tokens:,}\t{f'${record.cost_usd:.4f}' if record.cost_known or record.cost_usd else 'unknown'}\n"
        )


@usage_app.command("show", help="Sync changed sessions, then show usage for one session")
def usage_show(
    context: typer.Context,
    agent: Annotated[str, typer.Argument(help="Agent adapter name")],
    session_id: Annotated[str, typer.Argument()],
) -> None:
    state = state_from(context)
    _refresh(state, agent)
    record = json.loads(show_usage_record(agent, session_id))
    state.stdout.write(
        json.dumps({"schema": "dot.agent.usage.show/v1", "record": record}, ensure_ascii=False, indent=2) + "\n"
    )


@agent_app.command("stats", help="Sync changed sessions, then report prompts, tokens, costs, and API equivalents")
def agent_stats(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a")] = "",
    since: Annotated[str, typer.Option("--since", help="Duration (7d, 24h), UTC date or timestamp")] = "",
    until: Annotated[str, typer.Option("--until", help="Inclusive UTC date (whole day) or exact timestamp")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m")] = False,
    by_project: Annotated[bool, typer.Option("--by-project")] = False,
    as_json: JsonOption = False,
    monthly: Annotated[bool, typer.Option("--monthly", help="Group usage by calendar month in UTC")] = False,
    billing: Annotated[bool, typer.Option("--billing", help="Group usage by configured subscription cycles")] = False,
    tokens_only: Annotated[
        bool, typer.Option("--tokens-only", help="Skip prompt analysis for a quick usage report")
    ] = False,
    prompts_only: Annotated[
        bool, typer.Option("--prompts-only", help="Skip token analysis and report prompt activity")
    ] = False,
) -> None:
    state = state_from(context)
    if tokens_only and prompts_only:
        raise _click.exceptions.UsageError("choose --tokens-only or --prompts-only")
    if monthly and billing:
        raise _click.exceptions.UsageError("choose --monthly or --billing")
    if prompts_only and (monthly or billing or by_model):
        raise _click.exceptions.UsageError("--monthly, --billing, and --by-model require token statistics")
    query = _query(agent, cwd, "", since, until)
    _refresh(state, agent)
    prompts = None if tokens_only else prompt_statistics(query, by_project=by_project)
    rows = (
        []
        if prompts_only
        else aggregate_usage(
            iter_usage_records(),
            harness=agent,
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
    if as_json:
        state.stdout.write(
            json.dumps(
                {
                    "schema": "dot.agent.stats/v2",
                    "coverage": "Archived records after an incremental sync. Prompt and usage coverage can differ.",
                    "prompts": prompts,
                    "usage": [row.to_dict() for row in rows],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        write_report_line(state.stdout, "Archived records after an incremental sync.")
        if prompts is not None:
            _print_prompt_statistics(state, prompts)
        if not prompts_only:
            write_usage_stats(state.stdout, rows, by_model=by_model)
    if prompts is not None and not prompts["complete"]:
        raise DotError("prompt statistics are incomplete; inspect excluded sessions and partial counts")


@agent_app.command("doctor", help="Check notify hooks, session sync, and archive readability per agent")
def agent_doctor(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a", help="Inspect only one agent")] = "",
    as_json: JsonOption = False,
) -> None:
    run_agent_doctor(state_from(context), as_json=as_json, agent=agent)


agent_app.add_typer(hook_app, name="hook", hidden=True)


agent_app.add_typer(session_app, name="session")


agent_app.add_typer(usage_app, name="usage")
