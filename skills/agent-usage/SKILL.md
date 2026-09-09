---
name: agent-usage
description: Analyze LLM token usage across agent harnesses with dot, DuckDB, or jq. Use when auditing consumption, cost drivers, or harness efficiency.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-09-09"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Bound the question**: harnesses, time range, sessions, models, and the comparison needed; inspect the existing archive before collecting more data.
1. **Use the owner**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Analyze comparable data**: account for missing sessions, model aliases, cache tokens, provider accounting differences, and time zones before aggregating.
1. **Report**: include period, sources, completeness, units, assumptions, and the query or artifact supporting the result; protect prompt and account data.

## Gotchas

- **Unknown is not free**: Claude can report cost through `cost-state`; absent prices are `null`/`unknown`, not zero. Read `cost_known_sessions` and `cost_complete` before comparing cost. A known zero is distinct from missing cost.
- **Model attribution**: switched sessions are labeled `mixed`; older extractor records retain totals but use `unknown` model attribution. `usage sync` refreshes derivable records. Whole-session date filters use recorded session timestamps, not interval billing.
- **Read the provenance**: `measurement_kind` distinguishes provider-reported totals, Antigravity's byte-based estimate, and Grok's final context size. Statistics group these separately and do not combine unlike measurements into one total.
- **Atomic rewrites prevent duplicates**: each session uses one `<session_id>.json` file overwritten at durable capture boundaries, so aggregation counts a session once.
- **Capture is single-pass**: the session hook derives normalized logs and usage from one transcript snapshot; the standalone `usage sync` command remains available for backfills.
- **Both harness and agent fields exist**: queries can group by either `harness` or `agent` interchangeably.
- **`sync` fails loud, hooks fail soft**: `dot agent usage sync` aborts on an unreadable store rather than reporting `Synced 0`, and it rewrites every record it can re-derive — so it is the way to backfill after an extractor changes.
- **Background hooks fail soft**: hooks spool errors to `~/.agents/hook-failures` so a failure in usage tracking never aborts the agent CLI.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
