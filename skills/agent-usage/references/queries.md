# Agent Usage Schema and Queries

## Directory layout and schema

Every session record is stored atomically with permissions `0o600`:

```text
~/.agents/usages/
├── agy/
│   └── <session_id>.json
├── claude/
│   └── <session_id>.json
├── codex/
│   └── <session_id>.json
├── copilot/
│   └── <session_id>.json
└── grok/
    └── <session_id>.json
```

The active synchronization `dot agent usage sync` writes the five verified harnesses above.

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
dot agent usage sync                                               # scan raw stores and backfill missing records
duckdb -c "SELECT harness, measurement_kind, count(*), sum(total_tokens) FROM read_json_auto('~/.agents/usages/*/*.json', union_by_name=true) GROUP BY harness, measurement_kind" # comparable groups only
```

Prefer CLI statistics when archives contain old extractor records: they label historical model attribution unknown rather than trusting the last model string. Missing costs serialize as `null`. A partial group reports its known subtotal plus completeness counts; it is not an estimate of the missing bill. `--since`/`--until` include whole sessions at their recorded timestamps, never prorated interval usage.

For conversation activity, use `dot agent prompts stats --since 2026-09-01 --by-project --json`; it counts archived user messages and reports lengths, active UTC days, responses, and evidence gaps without printing content. `dot agent session stats --json` reports latest sessions versus retained generations and archive bytes. These are descriptive archive statistics, not efficiency or quality scores.
