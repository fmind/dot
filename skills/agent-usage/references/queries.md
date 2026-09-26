# Agent Usage Schema and Queries

## Directory layout and schema

Each session keeps one bundle with its latest measurement:

```text
~/.agents/sessions/v3/<agent>/<session_id>.jsonl
  line 1: manifest (schema_version 3), with the usage record in `usage` (null when unsupported)
  line 2+: normalized transcript records
```

Directories are private (`0o700`), and files are private (`0o600`). `dot agent session sync` captures all five verified adapters; reports sync first. Only the current store is queried; earlier stores and standalone usage files are outside its scope.

Prefer the CLI projection to reading bundles directly: it validates each record. `dot agent usage list --limit 0 --json` exports selected session usage records for local analysis. Prefer statistics JSON for monthly/model aggregation: optional `samples` contain per-request measurements and must never be summed together with their parent session totals.

CLI list output wraps records in `{ "schema": "dot.agent.usage.list/v1", "records": [...] }`. Statistics use the `usage` array of `dot.agent.stats/v2`; prompt-only statistics use its `prompts` object.

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
  "reasoning_tokens": 0,
  "total_tokens": 99100,
  "cost_usd": 0.1425,
  "cost_known": true,
  "turn_count": 8,
  "cwd": "~/project",
  "schema_version": "dot.agent.usage/v3",
  "extractor_version": "2",
  "measurement_kind": "provider-reported",
  "source_bytes": 428000
}
```

`measurement_kind` is `provider-reported` for Claude, Codex, Copilot, and Grok sessions with complete turn usage; `estimated` for Antigravity's byte-based token approximation; and `context-only` for Grok's final context-window fallback. Inspect the field on each record, not just its harness. `source_bytes` records the bytes inspected by the usage extractor and is not a token count.

## Commands

```bash
dot agent stats --tokens-only                                              # summary table of token usage per harness
dot agent stats --tokens-only --by-model                                   # break down token usage by harness and model
dot agent stats --tokens-only --project . --by-project --by-model --json    # project selection and grouping
dot agent stats --tokens-only --agent claude                             # filter stats to a specific harness
dot agent stats --tokens-only --since 24h --json                           # emit a versioned JSON object for scripting
dot agent usage list -n 20                                         # list recent session records
dot agent usage show claude <session_id>                           # inspect a specific session record
dot agent session sync                                            # capture/backfill transcript and usage together
(umask 077; dot agent usage list --limit 0 --json > usage.json)
duckdb -init /dev/null -batch -bail -json -c "SELECT record.harness, record.measurement_kind, count(*), sum(record.total_tokens) FROM (SELECT unnest(records) AS record FROM read_json_auto('usage.json')) GROUP BY record.harness, record.measurement_kind"
```

Missing costs serialize as `null`. A partial group reports its known subtotal and completeness counts; it does not estimate missing usage. `--since` and inclusive `--until` filter request timestamps when reliable samples exist, otherwise whole-session timestamps. A date-only `--since` begins at midnight UTC; a date-only `--until` includes the whole UTC day. Explicit timestamps remain exact. Provider session cost is reported only when the complete session belongs to one selected group; it cannot be apportioned across dates or models.

Since parser 4, Claude blocks sharing request/message identity are deduplicated, retaining peak counters within a response. Codex derives increments from cumulative counters, skips repeated snapshots, and treats cached reads as a subset of input and reasoning as a subset of output. A decreasing cumulative counter keeps the provider's final session total but disables request allocation. Copilot uses its session timestamp. Antigravity is an estimate. Grok turn ledgers retain per-request/model consumption and recorded cost when available; signals-only captures retain final context size. Explicitly incomplete ledgers fail extraction and preserve the prior archive rather than being reclassified as complete usage. Undated usage uses the latest valid transcript timestamp, then the newest source-file modification time; capture time is never used. OpenCode usage capture is unsupported. Never combine estimated or context-only tokens with provider-reported totals.

Bundles from older admitted parsers remain readable; accounting versions requiring recapture are flagged through `legacy_accounting_sessions`; parser 3 Claude totals can contain duplicate response blocks. Sync recaptures available sources with the current parser; [contracts](../../dot-cli/references/contracts.md) owns the current and readable parser versions. Request samples reconcile to session totals and carry no prompt text. Token queries read only manifest lines, never transcript content.

## Monthly and subscription reports

```bash
dot agent stats --tokens-only                         # total and first/last recorded usage
dot agent stats --tokens-only --monthly                # calendar months in UTC
dot agent stats --tokens-only --billing --agent codex        # configured renewal cycles
dot agent stats --tokens-only --monthly --by-model --json      # detailed token and pricing fields
```

Subscription configuration lives under `agent.subscriptions` in the selected Dot YAML file:

```yaml
# Docs: https://github.com/fmind/dot
agent:
  subscriptions:
    codex:
      renewal_day: 15
      timezone: Europe/Paris
      monthly_usd: 20
```

The example does not infer a real subscription. `renewal_day` accepts 1–31; missing days clamp to month end. `timezone` defaults to UTC and follows IANA daylight-saving rules. `monthly_usd` is optional, positive, and must already be expressed in USD. Configuration precedence is the CLI `--config` flag, `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`; configured mappings merge with defaults. `--billing` requires configuration for each included harness; use `--agent` to select one. `--monthly` and `--billing` are mutually exclusive.

Billing cycles start at local midnight on the renewal day and end exclusively at the next renewal. Missing subscription settings remain unknown. `period_start` is inclusive and `period_end` exclusive. `first_timestamp` and `last_timestamp` describe observed usage, not guaranteed continuous capture or the subscription start date. Sessions spanning periods/models appear in multiple rows, so row session counts are not additive. Human model breakdowns omit the combined total; use an ungrouped report for total sessions. Empty periods are omitted, not asserted to have zero usage. `session_timestamp_sessions` identifies approximate allocations; `legacy_accounting_sessions` identifies records needing recapture. `priced_measurements` counts priced requests (or session fallbacks), and `priced_sessions` counts sessions whose selected measurements were all priced. API-value ratios are shown only with complete pricing and a configured fee; partial capture can still make them incomplete. Model/project breakdowns omit the ratio to avoid charging the same subscription to each subgroup.

For conversation activity, use `dot agent stats --prompts-only --since 2026-09-01 --by-project --json`; it counts archived user messages and reports lengths, active UTC days, responses, and evidence gaps without printing content. `dot agent session stats --json` reports archived sessions, records, and archive bytes. These are descriptive archive statistics, not efficiency or quality scores.
