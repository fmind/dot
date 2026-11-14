---
name: agent-usage
description: "Report agent token usage, costs, and API equivalents from session archives or DuckDB."
---

# Agent Usage

Analyze archived session usage with `dot agent stats` and DuckDB, keeping recorded tokens, offline rate-card API equivalents, and provider bills distinct (never expose prompt text or account IDs).

## Gotchas

- **Unknown is not free**: missing prices serialize as `null`/`unknown`; check `cost_known_sessions`, `cost_complete`, `pricing_complete`, and `unpriced_reasons`.
- **Keep `measurement_kind` separate**: never sum `provider-reported`, `estimated` (byte-estimated older Antigravity transcripts), and `context-only` (Grok window fallbacks) tokens together.
- **Exclude sidechains from session counts**: `sidechain: true` subagents roll tokens into their parent session without adding sessions or recorded cost.

## Archive and records

Each private bundle (`~/.agents/sessions/v3/<agent>/<session_id>.jsonl`, `0600` inside `0700` dirs) stores line 1 manifest, line 2 `dot.agent.usage/v3` record (or `null`), and line 3+ transcript records (never read by token queries). [Daily workflows](daily-workflows.md#sessions-and-statistics) owns sync/date windows; [contracts](contracts.md#session-archive) owns retention.

Key fields on `dot agent stats --sessions --limit 0 --json` (`dot.agent.stats.sessions/v1` `.records[]`): `timestamp`, `harness`/`agent`, `session_id`, `model`, `input_tokens`, `output_tokens`, `cached_tokens`, `cache_write_tokens` (including `cache_write_1h_tokens`), `reasoning_tokens`, `total_tokens`, `cost_usd`, `cost_known`, `turn_count`, `cwd`, `measurement_kind`, optional `sidechain`/`parent_session_id`, `source_bytes` (input bytes, not tokens), and optional per-request `samples` (never sum `samples` with session totals).

## Commands

```bash
dot agent stats --tokens-only --by-model                                   # token summary by harness and model
dot agent stats --tokens-only --project . --by-project --by-model --json   # project selection and JSON output
dot agent stats --tokens-only --monthly --by-model --json                  # UTC calendar months ([period_start, period_end))
dot agent stats --tokens-only --no-sync                                    # query stored archive without syncing first
dot agent stats --prompts-only --since 2026-09-01 --by-project --json      # prompt counts, lengths, active UTC days
(umask 077; dot agent stats --sessions --limit 0 --json | jq -c '.records[] | del(.samples) | .sidechain //= false' > usage.jsonl)
duckdb -no-init -light-mode -batch -bail -json -c "SELECT harness, measurement_kind, count(*) FILTER (WHERE NOT sidechain) AS sessions, sum(total_tokens) AS tokens FROM read_json_auto('usage.jsonl') GROUP BY ALL"
```

Partial groups report known subtotals and completeness counts without estimating gaps. Provider session cost appears only when an entire session (with sidechains) falls in one group; multi-period/multi-model sessions repeat across `--monthly`/`--by-model` rows (use ungrouped output for total session counts).

## Provider measurement

- **Claude**: deduplicates blocks by request/message ID (peak counters), marks `hasUnknownModelCost` unknown, and prices 1h vs 5m cache writes separately.
- **Pi**: samples assistant, cache-warming, summary, and nested-model entries (counting only assistant turns as requests); input excludes cache reads/writes, output includes reasoning, and `cost.total` is recorded.
- **Antigravity**: reads response/compaction counters (input excludes cache reads → `cached_tokens`) or estimates ~4 bytes/token; `model` is `unknown` and unpriced.
- **Copilot & OpenCode**: Copilot dates by latest turn then creation (including `<db>-wal` in `source_bytes`). Live OpenCode sync accepts only an empty SQLite store and fails closed if `session_v2` (2.x) or `session` (1.x) holds rows; archived 1.x bundles remain queryable (per-step tokens, reasoning in output, recorded cost unpriced in API equivalents).
- **Retired (`codex`, `grok`)**: queryable from archived bundles; Codex includes cache in input and reasoning in output, and Grok uses turn ledgers or `context-only` fallbacks (`<model>-build` priced at `<model>`). Legacy parsers 3–6 (and 7 for Grok) report in `legacy_accounting_sessions` and stay unpriced; see [session compatibility](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/references/session-compatibility.md).

## Documentation

- [DuckDB JSON functions](https://duckdb.org/docs/data/json/overview) · companion skill: [duckdb](../../duckdb/SKILL.md).
