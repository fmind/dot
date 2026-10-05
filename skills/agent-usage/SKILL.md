---
name: agent-usage
description: "Analyze agent token usage, costs, and subscriptions with dot and DuckDB queries."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-10-05"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Bound the question**: harnesses, time range, sessions, models, and the comparison needed; inspect the existing archive before collecting more data.
1. **Let dot own sync and schemas**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Analyze comparable data**: account for missing sessions, model aliases, cache tokens, provider accounting differences, and time zones before aggregating.
1. **Report**: include period, sources, completeness, units, assumptions, and the query or artifact supporting the result; protect prompt and account data.

Quick total: `dot agent stats --tokens-only` (coverage dates and API equivalents). [queries.md](references/queries.md) owns flags, pricing fields, and billing configuration. API equivalents are offline rate-card estimates, never the bill or verified savings.

## Gotchas

- **Unknown is not free**: Claude can report cost through `cost-state`; absent prices are `null`/`unknown`, not zero. Read `cost_known_sessions` and `cost_complete` before comparing cost. A known zero is distinct from missing cost.
- **Attribution follows request samples**: Claude/Codex/Grok request samples retain per-request models and timestamps, including model switches and month boundaries. Sources without reliable samples use whole-session timestamps; check `session_timestamp_sessions`. Codex 0.153+ samples come from per-response records, including compaction requests; when they disagree with the thread total, or an older cumulative counter is corrected, the provider total stays without request allocation rather than inventing deltas.
- **Read the provenance**: `measurement_kind` distinguishes provider-reported totals, Antigravity's byte-based estimate, and Grok's context-only fallback when turn usage is unavailable. Grok turn ledgers can instead provide real consumption measurements; inspect the record rather than assuming a measurement kind from the harness name. Statistics group these separately and do not combine unlike measurements into one total.
- **One copy per session**: transcript and usage are replaced together, never by a shorter transcript or a failed extraction, so each session counts once. When only the measurement becomes unavailable, the longer transcript publishes with the archived measurement, counted as retained.
- **Subagents are sidechains**: their tokens join the parent session and project without another session or recorded cost; exclude `sidechain` records when counting sessions.
- **Capture uses one write path**: `session sync` reads each harness's own store; hooks only notify. Check `legacy_accounting_sessions` before trusting older totals ([contracts](../dot-cli/references/contracts.md)).
- **`sync` fails loud, reports warn**: `dot agent session sync` records each failed session, continues, and exits 1 at the end; the sync before `stats` and `usage` only warns on stderr. A failed usage extraction keeps the archived measurement.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
