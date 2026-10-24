# Agent Usage Schema and Queries

## Directory layout and schema

Each session keeps one bundle with its latest measurement:

```text
~/.agents/sessions/v3/<agent>/<session_id>.jsonl
  line 1: manifest (schema_version 4) with the usage span, never the usage itself
  line 2: the usage record (null when unsupported)
  line 3+: normalized transcript records
```

Directories are private (`0o700`), and files are private (`0o600`). `dot agent session sync` captures all six adapters; reports sync first. Only the current store is queried; earlier stores and standalone usage files are outside its scope.

Prefer the CLI projection to reading bundles directly: it validates each record. `dot agent stats --sessions --limit 0 --json` exports selected session usage records for local analysis (`--agent`, `--project`, `--since`, and `--until` filter by each session's last activity). Prefer statistics JSON for monthly/model aggregation: optional `samples` contain per-request measurements and must never be summed together with their parent session totals.

Session output wraps records in `{ "schema": "dot.agent.stats.sessions/v1", "records": [...] }`. Statistics use the `usage` array of `dot.agent.stats/v4` (its `requests` is `null` for agy and Grok rows), with the rate card in the top-level `pricing` object and `time_basis`; prompt-only statistics use its `prompts` object. Schema 3 bundles, which sync upgrades in place, kept usage inside the manifest line.

Each record contains:

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

`measurement_kind` is `provider-reported` for Claude, Codex, Copilot, Grok, and OpenCode sessions with complete turn usage; `estimated` for Antigravity's byte-based token approximation; `context-only` for Grok's final context-window fallback; and empty, reported as `unknown` in statistics, for a cost-only record whose provider reported a cost without token counters. Inspect the field on each record, not just its harness. `harness` and `agent` hold the same value, so group by either; the CLI filter is `--agent`. `cwd` is the resolved absolute project path. `cache_write_1h_tokens` is the Claude 1-hour subset of `cache_write_tokens`. Subagent records add `sidechain: true` and, when known, `parent_session_id`; exclude them when counting sessions. `source_bytes` records the bytes inspected by the usage extractor and is not a token count.

## Commands

```bash
dot agent stats --tokens-only                                              # summary table of token usage per harness
dot agent stats --tokens-only --by-model                                   # break down token usage by harness and model
dot agent stats --tokens-only --project . --by-project --by-model --json    # project selection and grouping
dot agent stats --tokens-only --agent claude                             # filter stats to a specific harness
dot agent stats --tokens-only --since 24h --json                           # emit a versioned JSON object for scripting
dot agent stats --sessions -n 20                                   # list recent session records
dot agent session sync                                            # capture/backfill transcript and usage together
# One record per line: the full archive exceeds DuckDB's 16 MiB maximum_object_size as a single JSON object.
(umask 077; dot agent stats --sessions --limit 0 --json | jq -c '.records[]' > usage.jsonl)
duckdb -no-init -batch -bail -json -c "SELECT harness, measurement_kind, count(*), sum(total_tokens) FROM read_json_auto('usage.jsonl') GROUP BY ALL"
```

Missing costs serialize as `null`. A partial group reports its known subtotal and completeness counts; it does not estimate missing usage. `--since` and inclusive `--until` filter request timestamps when reliable samples exist, otherwise whole-session timestamps. A date-only `--since` begins at midnight UTC; a date-only `--until` includes the whole UTC day. Explicit timestamps remain exact. Provider session cost is reported only when the complete session, including its sidechains, belongs to one selected group; it cannot be apportioned across dates or models.

Since parser 4, Claude blocks sharing request/message identity are deduplicated, retaining peak counters within a response. Codex 0.153+ rollouts record each response, including compaction requests that cumulative snapshots omit: parser 10 samples one request per response ID and, when the records disagree with the provider's thread total, keeps that total without request allocation. Older rollouts derive increments from cumulative counters and skip repeated snapshots. Codex cached reads and cache writes are subsets of input, and reasoning is a subset of output. A decreasing cumulative counter keeps the provider's final session total but disables request allocation. Parser 12 dates Copilot session usage by its latest turn, then the session creation time. Antigravity is an estimate; since parser 13 its model is `unknown` because the transcript does not identify it. Grok turn ledgers retain per-request/model consumption and recorded cost when available; signals-only captures retain final context size. An explicitly incomplete ledger is unavailable usage, neither an extraction failure nor complete usage; the [archive retention rules](../../dot-cli/references/contracts.md#session-archive) keep any archived measurement. Undated usage uses the latest valid transcript timestamp, then the newest source-file modification time; capture time is never used. Parser 11 captures OpenCode usage per assistant step (reasoning counted inside output) with its computed cost; OpenCode stays unpriced in API equivalents. Never combine estimated or context-only tokens with provider-reported totals.

Usage statistics add [sidechain](../../dot-cli/references/contracts.md#session-archive) tokens to the parent's session and project rows without counting another session or recorded cost; prompt statistics count only top-level sessions and report `sidechain_sessions`.

[Contracts](../../dot-cli/references/contracts.md#session-archive) owns the readable parsers and legacy accounting versions; reports count sessions needing recapture in `legacy_accounting_sessions`. Measurements captured before parser 10 price Claude 1-hour cache writes at the 5-minute rate and omit Codex compaction requests until sync recaptures their sources. Request samples reconcile to session totals and carry no prompt text. Token queries read only manifest and usage lines, never transcript content.

## Monthly reports

```bash
dot agent stats --tokens-only                         # total and first/last recorded usage
dot agent stats --tokens-only --monthly                # calendar months in UTC
dot agent stats --tokens-only --monthly --by-model --json # detailed token and pricing fields
dot agent stats --tokens-only --no-sync                # report the archive as stored, without syncing first
```

Reports first sync changed sessions incrementally; sync failures print on stderr and the report still prints. Use `--no-sync` for a reproducible rerun over an unchanged archive. Terminal reports use wrapped sections per agent, model, project, or period; exact counts and accounting qualifications remain visible. Add `--by-model` or `--json` for detail; omit `--tokens-only` when prompt statistics are also needed.

API equivalents use the offline rate card in `agent.pricing`, independently of recorded cost. Check `priced_measurements`, `pricing_complete`, `legacy_accounting_sessions`, and `unpriced_reasons`. Rates assume standard short context; Claude 1-hour cache writes use their own rate, other cache writes the model's default rate (5-minute for Claude). Grok Build's `<model>-build` turns use the `<model>` rate unless the card lists the suffixed name. Unknown models and unsupported accounting remain unpriced. Compare API-equivalent value with a subscription fee by hand: the ratio is a usage comparison, not verified savings or a quality score.

Monthly periods are UTC calendar months: `period_start` is inclusive and `period_end` exclusive. `first_timestamp` and `last_timestamp` describe observed usage, not guaranteed continuous capture. Sessions spanning periods/models appear in multiple rows, so row session counts are not additive. Human model breakdowns omit the combined total; use an ungrouped report for total sessions. Empty periods are omitted, not asserted to have zero usage. `session_timestamp_sessions` identifies approximate allocations; `legacy_accounting_sessions` identifies records needing recapture. `priced_measurements` counts priced requests (or session fallbacks), and `priced_sessions` counts sessions whose selected measurements were all priced.

For conversation activity, use `dot agent stats --prompts-only --since 2026-09-01 --by-project --json`; it counts archived user messages and reports lengths, active UTC days, responses, and evidence gaps without printing content. These are descriptive archive statistics, not efficiency or quality scores.
