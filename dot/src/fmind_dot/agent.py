"""Command contracts for agent workflows."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from fmind_dot.agent_doctor import run_agent_doctor
from fmind_dot.archive.ingest import (
    HookIdentity,
    _bounded_failure,
    ingest_agent_session,
    resolve_hook_identity,
    sync_sessions,
)
from fmind_dot.archive.parsers import (
    resolve_cwd,
)
from fmind_dot.archive.query import (
    SessionQuery,
    compact_session_generations,
    export_sessions,
    parse_session_date,
    query_session_summaries,
    show_session,
)
from fmind_dot.archive.statistics import prompt_statistics, session_statistics
from fmind_dot.archive.usage import (
    aggregate_usage,
    list_usage_records,
    load_usage_records,
    parse_flexible_time,
    show_usage_record,
    write_usage_stats,
)
from fmind_dot.artifacts import prune_agent_artifacts
from fmind_dot.command_group import AlphabeticalGroup
from fmind_dot.config import PricingConfig
from fmind_dot.errors import DotError
from fmind_dot.hooks import _spool_hook_failure, decode_copilot_session_end
from fmind_dot.state import State, state_from
from fmind_dot.system import build_notification, send_notification

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


agent_app = typer.Typer(
    cls=AlphabeticalGroup,
    name="agent",
    help="Manage AI agent integrations and sessions",
    no_args_is_help=True,
    context_settings=_CONTEXT_SETTINGS,
)


session_app = typer.Typer(
    cls=AlphabeticalGroup, help="Manage agent session logs", no_args_is_help=True, context_settings=_CONTEXT_SETTINGS
)


hook_app = typer.Typer(
    cls=AlphabeticalGroup, help="Run observable agent hooks", no_args_is_help=True, context_settings=_CONTEXT_SETTINGS
)


usage_app = typer.Typer(
    cls=AlphabeticalGroup,
    help="Manage agent token usage in ~/.agents/usages",
    no_args_is_help=True,
    context_settings=_CONTEXT_SETTINGS,
)


prompts_app = typer.Typer(
    cls=AlphabeticalGroup,
    help="Statistics about archived user messages; never prints prompt text",
    context_settings=_CONTEXT_SETTINGS,
)


def _query(agent: str, cwd: str, identity: str, since: str, until: str) -> SessionQuery:
    query = SessionQuery(
        agent=agent,
        cwd=resolve_cwd(cwd),
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
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum rows to return")] = 50,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Emit structured JSON")] = False,
    all_generations: Annotated[bool, typer.Option("--all-generations", help="Include superseded generations")] = False,
    status: Annotated[list[str] | None, typer.Option("--status", help="Filter by generation status")] = None,
) -> None:
    state = state_from(context)
    selected_statuses = set(status or ())
    allowed_statuses = {"current", "duplicate", "invalid", "partial", "stale", "unsupported", "legacy"}
    unknown = selected_statuses - allowed_statuses
    if unknown:
        raise DotError(f"unknown session status {min(unknown)!r}")
    summaries = query_session_summaries(
        _query(agent, cwd, identity, since, until),
        validate_content="invalid" in selected_statuses,
        latest_only=not all_generations,
        statuses=selected_statuses,
        limit=limit,
    )
    if as_json:
        json.dump(
            [summary.to_dict(include_records=False) for summary in summaries],
            state.stdout,
            ensure_ascii=False,
            indent=2,
        )
        state.stdout.write("\n")
        return
    for summary in summaries:
        state.stdout.write(
            f"{summary.ingested_at} {summary.agent} {summary.session_id} records={summary.record_count} "
            f"status={','.join(summary.status)} cwd={summary.cwd} generation={summary.generation_id}\n"
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
    latest: Annotated[bool, typer.Option("--latest", help="Select the latest generation of this session")] = False,
) -> None:
    if not session and not identity:
        raise DotError("show requires a session or lineage identity")
    summary = show_session(
        _query(agent, cwd, session or identity, since, until), include_content=content, latest=latest
    )
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
def session_sync(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", help="Synchronize one adapter")] = "",
    session: Annotated[str, typer.Option("--session", help="Synchronize one session identity")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd", help="Filter by resolved project path")] = "",
    since: Annotated[str, typer.Option("--since", help="Only sources modified since RFC3339 or YYYY-MM-DD")] = "",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Inspect candidates without writing archives or usage")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    sync_sessions(
        state_from(context),
        agent=agent,
        session=session,
        cwd=resolve_cwd(cwd),
        since=parse_session_date(since),
        dry_run=dry_run,
        as_json=as_json,
    )


def _print_statistics(state: State, document: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        state.stdout.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    else:
        for key, value in document.items():
            if key == "rows":
                columns = (
                    "agent",
                    "project",
                    "sessions",
                    "prompts",
                    "responses",
                    "words",
                    "characters",
                    "active_days",
                    "median_characters",
                    "p95_characters",
                    "legacy_sessions",
                    "partial_sessions",
                )
                state.stdout.write("\t".join(column.upper() for column in columns) + "\n")
                for row in value:
                    state.stdout.write(
                        "\t".join(str(row[column]) if row[column] != "" else "-" for column in columns) + "\n"
                    )
                continue
            state.stdout.write(
                f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, dict | list) else value}\n"
            )


@session_app.command("stats", help="Count current sessions, retained generations, archive bytes, and health")
def session_stats(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    since: Annotated[str, typer.Option("--since", help="Filter latest ingestion timestamps")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    _print_statistics(state_from(context), session_statistics(_query(agent, cwd, "", since, until)), as_json=as_json)


@prompts_app.command("stats", help="Count archived user messages and lengths without exposing text")
def prompts_stats(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    since: Annotated[str, typer.Option("--since", help="Filter conversation timestamps, RFC3339 or YYYY-MM-DD")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    by_project: Annotated[bool, typer.Option("--by-project")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    document = prompt_statistics(_query(agent, cwd, "", since, until), by_project=by_project)
    _print_statistics(state_from(context), document, as_json=as_json)
    if not document["complete"]:
        raise DotError(
            "prompt statistics are incomplete; inspect excluded sessions, timestamps, and legacy/partial counts"
        )


@session_app.command(
    "compact",
    help="Validate and plan generation compaction; dry-run unless --apply is set",
)
def session_compact(
    context: typer.Context,
    apply: Annotated[bool, typer.Option("--apply", help="Delete superseded verified generations")] = False,
    agent: Annotated[str, typer.Option("--agent", help="Compact only one agent archive")] = "",
) -> None:
    compact_session_generations(state_from(context).stdout, apply=apply, agent=agent)


@session_app.command("ingest")
def session_ingest(
    context: typer.Context,
    agent: Annotated[str, typer.Argument(help="Agent adapter name")],
    session_id: Annotated[str, typer.Argument(help="Session identity, when known")] = "",
    cwd: Annotated[str, typer.Argument(help="Session working directory, when known")] = "",
) -> None:
    ingest_agent_session(state_from(context), agent, session_id, cwd)


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


def _usage_rows(
    harness: str,
    since: str,
    until: str,
    by_model: bool,
    cwd: str = "",
    by_project: bool = False,
    pricing: PricingConfig | None = None,
):
    return aggregate_usage(
        load_usage_records(),
        harness=harness,
        since=parse_flexible_time(since) if since else None,
        until=parse_flexible_time(until) if until else None,
        by_model=by_model,
        cwd=resolve_cwd(cwd),
        by_project=by_project,
        pricing=pricing,
    )


@usage_app.command("stats")
def usage_stats_command(
    context: typer.Context,
    harness: Annotated[str, typer.Option("--harness", "-a")] = "",
    since: Annotated[str, typer.Option("--since")] = "",
    until: Annotated[str, typer.Option("--until")] = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    by_project: Annotated[bool, typer.Option("--by-project")] = False,
) -> None:
    state = state_from(context)
    write_usage_stats(
        state.stdout,
        _usage_rows(harness, since, until, by_model, cwd, by_project, state.config.agent.pricing),
        as_json=as_json,
        by_model=by_model,
    )


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
            f"{record.total_tokens:,}\t{f'${record.cost_usd:.4f}' if record.cost_known or record.cost_usd else 'unknown'}\n"
        )


@usage_app.command("show")
def usage_show(
    context: typer.Context,
    harness: Annotated[str, typer.Argument()],
    session_id: Annotated[str, typer.Argument()],
) -> None:
    state_from(context).stdout.write(show_usage_record(harness, session_id).decode())


@agent_app.command("stats", help="Show archived prompt activity, tokens, recorded costs, and offline API equivalents")
def agent_stats(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", "--harness", "-a")] = "",
    since: Annotated[str, typer.Option("--since", help="Duration (7d, 24h), UTC date or timestamp")] = "",
    until: Annotated[str, typer.Option("--until", help="Inclusive exact UTC date or timestamp")] = "",
    cwd: Annotated[str, typer.Option("--project", "--cwd")] = "",
    by_model: Annotated[bool, typer.Option("--by-model", "-m")] = False,
    by_project: Annotated[bool, typer.Option("--by-project")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    state = state_from(context)
    query = SessionQuery(
        agent=agent,
        cwd=resolve_cwd(cwd),
        since=parse_flexible_time(since) if since else None,
        until=parse_flexible_time(until) if until else None,
    )
    prompts = prompt_statistics(query, by_project=by_project)
    rows = aggregate_usage(
        load_usage_records(),
        harness=agent,
        since=query.since,
        until=query.until,
        cwd=query.cwd,
        by_model=by_model,
        by_project=by_project,
        pricing=state.config.agent.pricing,
    )
    if as_json:
        state.stdout.write(
            json.dumps(
                {
                    "schema": "dot.agent.stats/v1",
                    "coverage": "Archived records only; run dot agent session sync to refresh. Prompt and usage coverage can differ.",
                    "prompts": prompts,
                    "usage": [row.to_dict() for row in rows],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        state.stdout.write("Archived records only; run 'dot agent session sync' to refresh.\n")
        _print_statistics(state, prompts, as_json=False)
        write_usage_stats(state.stdout, rows, as_json=False, by_model=by_model)
    if not prompts["complete"]:
        raise DotError("prompt statistics are incomplete; inspect excluded sessions and legacy/partial counts")


@agent_app.command("doctor")
def agent_doctor(
    context: typer.Context,
    agent: Annotated[str, typer.Option("--agent", help="Inspect or repair only one integration")] = "",
    explain: Annotated[
        bool, typer.Option("--explain", help="Include bounded session identities and failure reasons")
    ] = False,
    deep: Annotated[bool, typer.Option("--deep", help="Hash sources and validate every archived generation")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Emit structured JSON")] = False,
    fix: Annotated[
        bool, typer.Option("--fix", "-f", help="Apply the managed agent integration targets with chezmoi")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-N", help="Preview --fix without changing deployed files")
    ] = False,
) -> None:
    run_agent_doctor(
        state_from(context), fix=fix, dry_run=dry_run, deep=deep, as_json=as_json, agent=agent, explain=explain
    )


@agent_app.command("clean", help="Preview cleanup of generated project prompts, proposals, and reports")
def clean_artifacts(
    context: typer.Context,
    apply: Annotated[
        bool, typer.Option("--apply", help="Remove the previewed categories of generated artifacts")
    ] = False,
) -> None:
    prune_agent_artifacts(state_from(context), dry_run=not apply)


agent_app.add_typer(hook_app, name="hook", hidden=True)


agent_app.add_typer(session_app, name="session")


agent_app.add_typer(usage_app, name="usage")


agent_app.add_typer(prompts_app, name="prompts")
