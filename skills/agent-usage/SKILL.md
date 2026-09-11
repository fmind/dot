---
name: agent-usage
description: Analyze LLM token usage across agent harnesses with dot, DuckDB, or jq. Use when auditing consumption, cost drivers, or harness efficiency.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-09-11"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Bound the question**: harnesses, time range, sessions, models, and the comparison needed; inspect the existing archive before collecting more data.
1. **Use the owner**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Analyze comparable data**: account for missing sessions, model aliases, cache tokens, provider accounting differences, and time zones before aggregating.
1. **Report**: include period, sources, completeness, units, assumptions, and the query or artifact supporting the result; protect prompt and account data.

Use `dot agent stats --tokens-only` (or `dot agent usage stats`) for a quick total with coverage dates and API equivalents. Add `--monthly` for UTC months or `--billing --harness codex` for configured subscription cycles. Add `--by-model` or `--json` for detail; omit `--tokens-only` when prompt statistics are also needed. [queries.md](references/queries.md) owns configuration examples and accounting limitations. Reports are read-only; `dot agent session sync` explicitly refreshes available sources.

API equivalents use the offline rate card in `agent.pricing`, independently of recorded cost. Check `priced_measurements`, `pricing_complete`, `legacy_accounting_sessions`, and `unpriced_reasons`. Rates assume standard short context and 5-minute cache writes. Unknown models and unsupported accounting remain unpriced. API-equivalent value divided by the configured USD subscription charge is a usage comparison, not verified savings or a quality score.

## Gotchas

- **Unknown is not free**: Claude can report cost through `cost-state`; absent prices are `null`/`unknown`, not zero. Read `cost_known_sessions` and `cost_complete` before comparing cost. A known zero is distinct from missing cost.
- **Model attribution and dates**: Claude/Codex request samples retain per-request models and timestamps, including model switches and month boundaries. Sources without reliable samples use whole-session timestamps; check `session_timestamp_sessions`. A Codex cumulative-counter correction disables request allocation for that session rather than inventing deltas.
- **Read the provenance**: `measurement_kind` distinguishes provider-reported totals, Antigravity's byte-based estimate, and Grok's final context size. Statistics group these separately and do not combine unlike measurements into one total.
- **Atomic generations prevent split state**: transcript and usage publish together. Queries choose one measurement per session and do not sum retained generations.
- **Capture uses one write path**: session hooks and `session sync` publish the same complete bundle. Earlier stores and standalone usage files are outside current queries. Parser 3 remains readable but may overcount Claude streaming blocks; recapture available sources to parser 4 before comparisons.
- **Both harness and agent fields exist**: queries can group by either `harness` or `agent` interchangeably.
- **`sync` fails loud, hooks fail soft**: `dot agent session sync` aborts on an unreadable store rather than reporting `Synced 0`, and creates a new generation when the source or parser changes. Reingestion backfills derivable records without rewriting history.
- **Background hooks fail soft**: hooks spool errors to `~/.agents/hook-failures` so a failure in usage tracking never aborts the agent CLI.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
