---
name: agent-usage
description: "Analyze agent token usage, costs, subscriptions, and efficiency with dot and local queries."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-09-23"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Bound the question**: harnesses, time range, sessions, models, and the comparison needed; inspect the existing archive before collecting more data.
1. **Use the owner**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Analyze comparable data**: account for missing sessions, model aliases, cache tokens, provider accounting differences, and time zones before aggregating.
1. **Report**: include period, sources, completeness, units, assumptions, and the query or artifact supporting the result; protect prompt and account data.

Use `dot agent stats --tokens-only` for a quick total with coverage dates and API equivalents. Add `--monthly` for UTC months or `--billing --agent codex` for configured subscription cycles. Terminal reports use wrapped sections per agent, model, project, or period; exact counts and accounting qualifications remain visible. Add `--by-model` or `--json` for detail; omit `--tokens-only` when prompt statistics are also needed. [queries.md](references/queries.md) owns configuration examples and accounting limitations. Reports first sync changed sessions incrementally; sync failures print on stderr and the report still prints.

API equivalents use the offline rate card in `agent.pricing`, independently of recorded cost. Check `priced_measurements`, `pricing_complete`, `legacy_accounting_sessions`, and `unpriced_reasons`. Rates assume standard short context and 5-minute cache writes. Unknown models and unsupported accounting remain unpriced. API-equivalent value divided by the configured USD subscription charge is a usage comparison, not verified savings or a quality score.

## Gotchas

- **Unknown is not free**: Claude can report cost through `cost-state`; absent prices are `null`/`unknown`, not zero. Read `cost_known_sessions` and `cost_complete` before comparing cost. A known zero is distinct from missing cost.
- **Model attribution and dates**: Claude/Codex request samples retain per-request models and timestamps, including model switches and month boundaries. Sources without reliable samples use whole-session timestamps; check `session_timestamp_sessions`. A Codex cumulative-counter correction disables request allocation for that session rather than inventing deltas.
- **Read the provenance**: `measurement_kind` distinguishes provider-reported totals, Antigravity's byte-based estimate, and Grok's final context size. Statistics group these separately and do not combine unlike measurements into one total.
- **One copy per session**: transcript and usage are replaced together, never by a shorter transcript or a failed extraction, so each session counts once.
- **Capture uses one write path**: `session sync` reads each harness's own store; hooks only notify. Bundles migrated from older parsers are flagged as legacy accounting (parser 3 may overcount Claude streaming blocks) until sync recaptures their sources ([contracts](../dot-cli/references/contracts.md)).
- **Both harness and agent fields exist**: queries can group by either `harness` or `agent` interchangeably.
- **`sync` fails loud, reports warn**: `dot agent session sync` records each failed session, continues, and exits 1 at the end; the sync before `stats` and `usage` only warns on stderr. A failed usage extraction keeps the archived measurement.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
