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
├── grok/
│   └── <session_id>.json
└── opencode/
    └── <session_id>.json
```

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
  "turn_count": 8,
  "cwd": "~/project"
}
```

## Commands

```bash
dot agent usage stats                                              # summary table of token usage per harness
dot agent usage stats --by-model                                   # break down token usage by harness and model
dot agent usage stats --harness claude                             # filter stats to a specific harness
dot agent usage stats --since 24h --json                           # emit json array for scripting
dot agent usage list -n 20                                         # list recent session records
dot agent usage show claude <session_id>                           # inspect a specific session record
dot agent usage sync                                               # scan raw stores and backfill missing records
duckdb -c "SELECT harness, count(*), sum(total_tokens) FROM read_json_auto('~/.agents/usages/*/*.json', union_by_name=true) GROUP BY harness" # ad-hoc SQL
```
