---
name: agent-usage
description: "Report agent token usage, costs, and API equivalents from session archives or DuckDB."
---

# Agent Usage

Analyze archived session usage with `dot agent stats` and DuckDB. Keep recorded tokens, offline API-equivalent estimates, and provider bills distinct.

## Workflow

1. **Query through `dot agent stats`**: it syncs first and validates schemas; read JSONL bundles directly only when the CLI lacks a field.
1. **Report completeness and protect privacy**: state the window, sources, and completeness flags; never expose prompt text or account IDs.

Quick check: `dot agent stats --tokens-only` prints coverage dates and offline rate-card API equivalents (never verified bills or savings).

## Gotchas

- **Unknown is not free**: missing prices serialize as `null`/`unknown`; check `cost_known_sessions` and `cost_complete` before comparing costs.
- **Keep `measurement_kind` separate**: never sum `provider-reported`, `estimated` (counterless Antigravity transcripts), and `context-only` (Grok fallback) tokens together.
- **Exclude sidechains from session counts**: `sidechain: true` subagent records roll tokens into their parent session.
- **Check accounting flags**: `legacy_accounting_sessions` and `session_timestamp_sessions` mark records needing recapture or session-level date fallback; see [provider measurement](#provider-measurement).

## Archive and records

Each session stores one private bundle (`0o700` dirs, `0o600` files):

```text
~/.agents/sessions/v3/<agent>/<session_id>.jsonl
  line 1: manifest (schema_version 4) with usage span, never usage counters
  line 2: usage record (null when unavailable)
  line 3+: normalized transcript records
```

[Daily workflows](daily-workflows.md#sessions-and-statistics) owns sync sources and `--since`/`--until` boundaries; [contracts](contracts.md#session-archive) owns retention and statuses. `dot agent stats --sessions --limit 0 --json` emits `{ "schema": "dot.agent.stats.sessions/v1", "records": [...] }` filtered by last activity; never sum optional per-request `samples` with parent session totals. Aggregated `dot.agent.stats/v4` exposes `.usage[]` (`requests` is `null` when agy or Grok contributes), `.pricing`, `.time_basis`, and `.prompts`.

Example session record (absent optional keys are omitted):

```json
{
  "timestamp": "2026-09-03T18:00:00Z",
  "harness": "claude",
  "agent": "claude",
  "session_id": "abc-123",
  "model": "claude-opus-5",
  "input_tokens": 12500,
  "output_tokens": 3400,
  "cached_tokens": 82000,
  "cache_write_tokens": 1200,
  "cache_write_1h_tokens": 800,
  "reasoning_tokens": 0,
  "total_tokens": 99100,
  "cost_usd": 0.1425,
  "cost_known": true,
  "turn_count": 8,
  "cwd": "/home/user/project",
  "schema_version": "dot.agent.usage/v3",
  "extractor_version": "2",
  "measurement_kind": "provider-reported",
  "source_bytes": 428000
}
```

Inspect `measurement_kind` per record (`provider-reported` for complete Claude, Codex, Copilot, Grok, OpenCode, Pi, and counter-bearing Antigravity runs; `estimated` for byte-estimated older Antigravity transcripts; `context-only` for Grok window fallbacks; omitted / reported `unknown` on cost-only records). `harness` equals `agent` (CLI filter: `--agent`); `cwd` is the resolved project path; `cache_write_1h_tokens` is a subset of `cache_write_tokens`; `sidechain: true` (with optional `parent_session_id`) marks subagents; `source_bytes` is extractor input size, not tokens.

## Commands

```bash
dot agent stats --tokens-only                                              # summary table of token usage per harness
dot agent stats --tokens-only --by-model                                   # break down token usage by harness and model
dot agent stats --tokens-only --project . --by-project --by-model --json   # project selection and grouping
dot agent stats --tokens-only --agent claude                               # filter stats to a specific harness
dot agent stats --tokens-only --since 24h --json                           # emit a versioned JSON object for scripting
dot agent stats --sessions -n 20                                           # list recent session records
# One record per line, without per-request samples (most of the bytes; never summed with session totals); sidechain defaults to false so filtered exports still bind.
(umask 077; dot agent stats --sessions --limit 0 --json | jq -c '.records[] | del(.samples) | .sidechain //= false' > usage.jsonl)
duckdb -no-init -light-mode -batch -bail -json -c "SELECT harness, measurement_kind, count(*) FILTER (WHERE NOT sidechain) AS sessions, sum(total_tokens) AS tokens FROM read_json_auto('usage.jsonl') GROUP BY ALL"
```

Partial groups report known subtotals and completeness counts without estimating gaps. Provider session cost appears only when the entire session (with sidechains) falls in one group; sidechain tokens join parent session/project rows without adding sessions or recorded cost.

## Provider measurement

- **Claude**: deduplicates blocks sharing request/message IDs (keeping peak counters); parser 10+ marks `cost-state.hasUnknownModelCost` unknown and prices 1h cache writes separately (earlier captures used the 5m rate until resynced).
- **Pi**: samples assistant messages, cache-warming `usage` entries, compaction/branch summaries, and nested-model tool results; counts only assistant messages as requests; records `cost.total`; input excludes cache reads/writes and output includes reasoning.
- **Codex**: 0.153+ samples per response ID (including compaction, omitted before parser 10 and frozen since Codex is retired), falling back to thread totals without request allocation on mismatch or decreasing cumulative counters; older rollouts diff cumulative snapshots; cached reads/writes are inside input and reasoning inside output.
- **Copilot**: dated by latest turn, then session creation.
- **Antigravity**: reads response/compaction counters (input excludes cache reads → `cached_tokens`) or estimates ~4 bytes/token; `model` is `unknown` and unpriced.
- **Grok**: reads turn ledgers or `context-only` signal fallbacks; incomplete ledgers are unavailable usage ([retention rules](contracts.md#session-archive) keep prior measurements).
- **OpenCode**: per assistant step (reasoning in output) with computed cost; unpriced in API equivalents.

Parsers 3–6 (and 7 for Grok) count in `legacy_accounting_sessions`; legacy zeros stay unpriced because they conflated missing counters with zero. Request samples reconcile to session totals without prompt text; token queries never read transcript lines. See the [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md) for parser history.

## Monthly reports and pricing

```bash
dot agent stats --tokens-only --monthly                   # calendar months in UTC
dot agent stats --tokens-only --monthly --by-model --json # detailed token and pricing fields
dot agent stats --tokens-only --no-sync                   # report the archive as stored, without syncing first
```

Pass `--no-sync` for reproducible reruns; omit `--tokens-only` or pass `--prompts-only --since 2026-09-01 --by-project --json` when descriptive prompt activity (counts, lengths, active UTC days, responses, gaps) is needed.

API equivalents apply `agent.pricing` at standard short-context rates (1h vs default 5m cache-write rate for Claude; `<model>` fallback for `<model>-build` Grok turns). Check `priced_measurements` (priced requests/fallbacks), `priced_sessions` (fully priced sessions), `pricing_complete`, `legacy_accounting_sessions`, and `unpriced_reasons`. Monthly UTC rows use `[period_start, period_end)`, omit empty months, and repeat multi-period/multi-model sessions across rows (human `--by-model` tables omit combined session totals; use ungrouped output for total sessions).

## Documentation

- [DuckDB JSON functions](https://duckdb.org/docs/data/json/overview) · companion skill: [duckdb](../../duckdb/SKILL.md).
