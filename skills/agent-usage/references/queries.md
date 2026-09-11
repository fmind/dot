# Agent Usage Schema and Queries

## Directory layout and schema

New measurements live inside immutable session generations:

```text
~/.agents/sessions/v2/<agent>/<lineage>/<generation>/
  manifest.json
  transcript.jsonl
  usage.json
```

Directories are private (`0o700`), and files are private (`0o600`). `usage.json` has schema `dot.session.usage/v1`, a status (`available` or `unsupported`), and a `record` object when available. `dot agent session sync` captures all five verified adapters. Only the current store is queried; earlier stores and standalone usage files are outside its scope.

Query the CLI's selected projection instead of globbing every generation: otherwise older measurements would be counted repeatedly. `dot agent usage list --limit 0 --json` exports selected session usage records for local analysis. Prefer statistics JSON for monthly/model aggregation: optional `samples` contain per-request measurements and must never be summed together with their parent session totals.

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

`measurement_kind` is `provider-reported` for Claude, Codex, and Copilot, `estimated` for Antigravity's byte-based token approximation, and `context-only` for Grok's final context-window observation. `source_bytes` records the bytes inspected by the usage extractor and is not a token count.

## Commands

```bash
dot agent usage stats                                              # summary table of token usage per harness
dot agent usage stats --by-model                                   # break down token usage by harness and model
dot agent usage stats --project . --by-project --by-model --json    # project selection and grouping
dot agent usage stats --harness claude                             # filter stats to a specific harness
dot agent usage stats --since 24h --json                           # emit json array for scripting
dot agent usage list -n 20                                         # list recent session records
dot agent usage show claude <session_id>                           # inspect a specific session record
dot agent session sync                                            # capture/backfill transcript and usage together
(umask 077; dot agent usage list --limit 0 --json > usage.json)
duckdb -c "SELECT harness, measurement_kind, count(*), sum(total_tokens) FROM read_json_auto('usage.json', union_by_name=true) GROUP BY harness, measurement_kind"
```

Missing costs serialize as `null`. A partial group reports its known subtotal and completeness counts; it does not estimate missing usage. `--since` and inclusive `--until` filter request timestamps when reliable samples exist, otherwise whole-session timestamps. A date alone means midnight UTC, not the end of that day. Provider session cost is reported only when the complete session belongs to one selected group; it cannot be apportioned across dates or models.

Parser 4 deduplicates Claude blocks sharing request/message identity, retaining peak counters within a response. Codex derives increments from cumulative counters, skips repeated snapshots, and treats cached reads as a subset of input and reasoning as a subset of output. A decreasing cumulative counter keeps the provider's final session total but disables request allocation. Copilot uses its session timestamp. Antigravity is an estimate; Grok is final context size, with capture-time fallback. OpenCode and Cursor usage capture is unsupported. Never combine estimated or context-only tokens with provider-reported totals.

Parser 3 remains readable and explicitly flagged through `legacy_accounting_sessions`; its Claude totals can contain duplicate response blocks. Recapture creates parser 4 generations without editing history. Usage chooses one bundle per session, preferring the newest admitted parser. Request samples reconcile to session totals and carry no prompt text. Token queries verify transcript and usage hashes without decoding transcript content; deep doctor still validates normalized record structure.

## Monthly and subscription reports

```bash
dot agent stats --tokens-only                         # total and first/last recorded usage
dot agent stats --tokens-only --monthly                # calendar months in UTC
dot agent usage stats --billing --harness codex        # configured renewal cycles
dot agent usage stats --monthly --by-model --json      # detailed token and pricing fields
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

The example does not infer a real subscription. `renewal_day` accepts 1–31; missing days clamp to month end. `timezone` defaults to UTC and follows IANA daylight-saving rules. `monthly_usd` is optional, positive, and must already be expressed in USD. Configuration precedence is the CLI `--config` flag, `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`; configured mappings merge with defaults. `--billing` requires configuration for each included harness; use `--harness` to select one. `--monthly` and `--billing` are mutually exclusive.

`period_start` is inclusive and `period_end` exclusive. `first_timestamp` and `last_timestamp` describe observed usage, not guaranteed continuous capture or the subscription start date. Sessions spanning periods/models appear in multiple rows, so row session counts are not additive. Empty periods are omitted, not asserted to have zero usage. `session_timestamp_sessions` identifies approximate allocations; `legacy_accounting_sessions` identifies records needing recapture. `priced_measurements` counts priced requests (or session fallbacks), and `priced_sessions` counts sessions whose selected measurements were all priced. API-value ratios are shown only with complete pricing and a configured fee; partial capture can still make them incomplete. Model/project breakdowns omit the ratio to avoid charging the same subscription to each subgroup.

For conversation activity, use `dot agent prompts stats --since 2026-09-01 --by-project --json`; it counts archived user messages and reports lengths, active UTC days, responses, and evidence gaps without printing content. `dot agent session stats --json` reports latest sessions versus retained generations and archive bytes. These are descriptive archive statistics, not efficiency or quality scores.
