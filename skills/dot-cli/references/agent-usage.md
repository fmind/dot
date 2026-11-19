---
name: agent-usage
description: "Report agent token usage, costs, and API equivalents from session archives or DuckDB."
---

# Agent Usage

Analyze archived session usage with `dot stats` and DuckDB, keeping recorded tokens, offline rate-card API equivalents, and provider bills distinct (never expose prompt text or account IDs).

## Gotchas

- **Unknown is not free**: missing prices serialize as `null`/`unknown`; check `cost_known_sessions` and `pricing_complete`.
- **Keep `measurement_kind` separate**: never sum `provider-reported`, `estimated` (byte-estimated older Antigravity transcripts), and `context-only` (Grok window fallbacks) tokens together.
- **Exclude sidechains from session counts**: `sidechain: true` subagents roll tokens into their parent session without adding sessions or recorded cost.

## Archive and records

Each private bundle (`~/.agents/sessions/v3/<agent>/<session_id>.jsonl`, `0600` inside `0700` dirs) stores line 1 manifest, line 2 `dot.agent.usage/v3` record (or `null`), and line 3+ transcript records (never read by token queries). [Daily workflows](daily-workflows.md#sessions-and-statistics) owns sync/date windows; [contracts](contracts.md#session-archive) owns retention.

Key fields on line 2 (`dot.agent.usage/v3`) of each bundle: `timestamp`, `harness`/`agent`, `session_id`, `model`, `input_tokens`, `output_tokens`, `cached_tokens`, `cache_write_tokens` (including `cache_write_1h_tokens`), `reasoning_tokens`, `total_tokens`, `cost_usd`, `cost_known`, `turn_count`, `cwd`, `measurement_kind`, optional `sidechain`/`parent_session_id`, `source_bytes` (input bytes, not tokens), and optional per-request `samples` (never sum `samples` with session totals).

## Commands

```bash
dot stats --by-model                                         # token summary by harness and model
dot stats --project . --by-project --by-model --json         # project selection and JSON output
dot stats --since 2026-11-01 --until 2026-11-30 -m --json    # UTC date window ([since, until])
dot stats --no-sync                                          # query stored archive without syncing first
(umask 077; for f in ~/.agents/sessions/v3/*/*.jsonl; do sed -n '2p' "$f"; done | jq -cs 'map(select(. != null) | del(.samples) | .sidechain //= false)[]' > usage.jsonl)
duckdb -no-init -light-mode -batch -bail -json -c "SELECT harness, measurement_kind, count(*) FILTER (WHERE NOT sidechain) AS sessions, sum(total_tokens) AS tokens FROM read_json_auto('usage.jsonl') GROUP BY ALL"
```

Partial groups report known subtotals and completeness counts without estimating gaps. Provider session cost appears only when an entire session (with sidechains) falls in one group; multi-model sessions repeat across `--by-model` rows (use ungrouped output for total session counts).

## Provider measurement

- **Claude**: deduplicates blocks by request/message ID (peak counters), marks `hasUnknownModelCost` unknown, and prices 1h vs 5m cache writes separately.
- **Pi**: samples assistant, cache-warming, summary, and nested-model entries (counting only assistant turns as requests); input excludes cache reads/writes, output includes reasoning, and `cost.total` is recorded.
- **Antigravity**: reads response/compaction counters (input excludes cache reads → `cached_tokens`) or estimates ~4 bytes/token; `model` is `unknown` and unpriced.
- **Copilot**: samples request rows from SQLite (resolving uncached input via token details or cache-inclusive OpenAI/Gemini/Grok prompt subtraction) and propagates turn models.
- **OpenCode**: samples 2.x and 1.x SQLite assistant steps, rolling reasoning into output, recording provider cost, and pricing listed models while skipping pre-fork history.
- **Retired (Codex, Grok)**: archived bundles stay queryable via `dot stats` while incremental sync captures agy, Claude, Copilot, OpenCode, and Pi. Codex includes cache in input and reasoning in output; Grok uses turn ledgers or `context-only` fallbacks. See [session compatibility](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/references/session-compatibility.md).

## Documentation

- [DuckDB JSON functions](https://duckdb.org/docs/data/json/overview) · companion skill: [duckdb](../../duckdb/SKILL.md).
