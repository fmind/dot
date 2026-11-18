"""Command contract for agent session usage statistics."""

import argparse
from datetime import datetime
from typing import Any

from fmind_dot.archive.parsers import AGENT_ADAPTERS, resolve_cwd
from fmind_dot.archive.sync import sync_sessions
from fmind_dot.archive.usage import (
    RETIRED_AGENTS,
    aggregate_usage,
    iter_usage_records,
    parse_flexible_time,
    write_usage_stats,
)
from fmind_dot.command import Parser, add_json
from fmind_dot.config import default_pricing
from fmind_dot.errors import UsageError
from fmind_dot.reporting import write_json, write_report_line
from fmind_dot.state import State

STATS_SCHEMA = "dot.stats/v5"
_AGENTS = tuple(sorted((*AGENT_ADAPTERS, *RETIRED_AGENTS)))
_WHEN = "duration (7d, 24h), UTC date, or timestamp"


def _parse_time(value: str, option: str) -> datetime | None:
    try:
        return parse_flexible_time(value, end_of_day=option == "--until") if value else None
    except (ValueError, OverflowError) as error:
        raise UsageError(f"{option}: expected a {_WHEN}") from error


def _stats(state: State, args: argparse.Namespace) -> None:
    selected = args.agent
    try:
        cwd = resolve_cwd(args.cwd)
    except ValueError as error:
        raise UsageError(f"--project: {error}") from None
    since, until = _parse_time(args.since, "--since"), _parse_time(args.until, "--until")
    if since and until and since > until:
        raise UsageError("--since: must not be after --until")
    outcome = sync_sessions(state, agent=selected) if not args.no_sync and selected not in RETIRED_AGENTS else None
    rates = default_pricing()
    rows = aggregate_usage(
        iter_usage_records(since=since, until=until),
        harness=selected,
        since=since,
        until=until,
        cwd=cwd,
        by_model=args.by_model,
        by_project=args.by_project,
        pricing=rates,
    )
    suffix = (
        "after an incremental sync"
        if outcome is not None
        else ("without a sync (--no-sync)" if args.no_sync else f"without a sync ({selected} is retired)")
    )
    coverage = f"Archived records {suffix}."
    if args.as_json:
        payload: dict[str, Any] = {
            "schema": STATS_SCHEMA,
            "coverage": coverage,
            "pricing": {"as_of": rates.as_of, "basis": rates.basis, "sources": rates.sources},
            "usage": [row.to_dict() for row in rows],
        }
        if outcome is not None:
            payload["sync"] = {
                "failed": outcome.failed,
                "retained": outcome.retained,
                "retained_current_transcripts": outcome.retained_current_transcripts,
            }
        write_json(state.stdout, payload)
    else:
        write_report_line(state.stdout, coverage)
        write_usage_stats(state.stdout, rows, by_model=args.by_model, pricing=rates)
    if outcome is not None and outcome.failed > 0:
        raise SystemExit(1)


def register(commands: Parser) -> None:
    stats = commands.command(
        "stats",
        "Sync changed sessions (unless --no-sync), then report tokens, costs, and API equivalents",
        _stats,
        epilog="Examples: dot stats --since 7d --json · dot stats --by-model --agent agy",
    )
    stats.add_argument("-a", "--agent", choices=_AGENTS, default="", help="Filter by agent")
    stats.add_argument("--project", dest="cwd", default="", metavar="PATH", help="Filter by resolved project directory")
    stats.add_argument("--since", default="", metavar="WHEN", help=f"Active since {_WHEN}")
    stats.add_argument(
        "--until", default="", metavar="WHEN", help="Active until duration, UTC date (whole day), or timestamp"
    )
    stats.add_argument("-m", "--by-model", action="store_true", help="Group usage by model")
    stats.add_argument("--by-project", action="store_true", help="Group usage by project")
    add_json(stats)
    stats.add_argument(
        "--no-sync", action="store_true", help="Report the archive as stored, without capturing changed sessions first"
    )
