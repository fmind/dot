---
name: agent-usage
description: Query, analyze, and track LLM token usage across AI agent harnesses in ~/.agents/usages using the dot CLI, DuckDB, or jq. Use when auditing token consumption, comparing harness efficiency, or inspecting agent costs.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-09-05"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Bound the question**: harnesses, time range, sessions, models, and the comparison needed; inspect the existing archive before collecting more data.
1. **Use the owner**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Analyze comparable data**: account for missing sessions, model aliases, cache tokens, provider accounting differences, and time zones before aggregating.
1. **Report**: include period, sources, completeness, units, assumptions, and the query or artifact supporting the result; protect prompt and account data.

## Gotchas

- **Only Claude and OpenCode report cost**: `cost_usd` comes from Claude's `cost-state` transcript lines and OpenCode's session database; `agy`, `codex`, `copilot`, and `grok` expose no price, so they always total `$0.00`. Compare those four on tokens, never on cost.
- **Grok counts context, not consumption**: Grok records no cumulative token totals, so its `input_tokens` carries the final context-window occupancy and its output tokens are unobservable — a documented undercount.
- **Atomic rewrites prevent duplicates**: each session uses a single `<session_id>.json` file overwritten on turn updates, preventing double-counting across `Stop` and `SessionEnd` hooks.
- **Both harness and agent fields exist**: queries can group by either `harness` or `agent` interchangeably.
- **`sync` fails loud, hooks fail soft**: `dot agent usage sync` aborts on an unreadable store rather than reporting `Synced 0`, and it rewrites every record it can re-derive — so it is the way to backfill after an extractor changes.
- **Background hooks fail soft**: hooks spool errors to `~/.agents/hook-failures` so a failure in usage tracking never aborts the agent CLI.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
