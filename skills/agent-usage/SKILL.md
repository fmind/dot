---
name: agent-usage
description: "Analyze agent token usage, costs, and subscriptions with dot and DuckDB queries."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-usage
  created: "2026-09-03"
  updated: "2026-10-09"
---

# Agent Usage

Analyze the shared usage archive with dot and DuckDB. Preserve the difference between recorded token usage, estimated cost, and the provider's actual bill.

## Workflow

1. **Let dot own sync and schemas**: dot owns source synchronization and archive schemas; read [queries.md](references/queries.md) for layout, fields, DuckDB queries, and exports.
1. **Report completeness, protect data**: state period, sources, and completeness; protect prompt and account data.

Quick total: `dot agent stats --tokens-only` (coverage dates and API equivalents). [queries.md](references/queries.md) owns flags, pricing fields, and billing configuration. API equivalents are offline rate-card estimates, never the bill or verified savings.

## Gotchas

- **Unknown is not free**: absent prices are `null`/`unknown`, not zero; read `cost_known_sessions` and `cost_complete` before comparing cost.
- **Never add unlike measurements**: `measurement_kind` separates provider-reported, estimated (Antigravity), and context-only (Grok) tokens; statistics group them separately.
- **Subagents are sidechains**: exclude `sidechain` records when counting sessions; their tokens join the parent.
- **Check accounting completeness**: `legacy_accounting_sessions` and `session_timestamp_sessions` flag records needing recapture or approximate allocation; [queries.md](references/queries.md) owns parser and per-harness details.
- **`sync` fails loud, reports warn**: `dot agent session sync` records each failed session, continues, and exits 1 at the end; the sync before `stats` and `usage` only warns on stderr.

## Documentation

- [DuckDB JSON Functions](https://duckdb.org/docs/data/json/overview)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (every `dot` command), [duckdb](../duckdb/SKILL.md) (file-based SQL analysis).
