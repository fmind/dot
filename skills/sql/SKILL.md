---
name: sql
description: "Query/export CSV, Parquet, JSON, SQLite, PostgreSQL via DuckDB, sqlite3, psql; SQL/dbt quality."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sql
  created: "2026-09-02"
  updated: "2026-11-24"
---

# SQL, DuckDB, SQLite & PostgreSQL

Use DuckDB for local analytics across CSV, Parquet, JSON, and attached SQLite files; keep SQLite for embedded application state; use [postgres](references/postgres.md) for live PostgreSQL/`pgvector` inspection via `psql`.

## Commands

```bash
duckdb -no-init -light-mode -batch -bail -json -c "SELECT count(*) AS n FROM 'events/*.json'"
duckdb -no-init -light-mode -batch -bail -no-agent -c "ATTACH 'app.sqlite' AS s (TYPE sqlite, READ_ONLY); SELECT count(*) FROM s.users"
sqlite3 -noinit -batch -bail -readonly -ifexists app.sqlite '.schema'
sqlite3 -noinit -batch -bail -noheader -list -readonly -ifexists app.sqlite 'PRAGMA integrity_check'
```

Keep these flags on every call: `-light-mode` skips DuckDB 2.0's 5s interactive/PTY OSC 11 probe; `-ifexists` prevents SQLite typos from creating empty DBs (`PRAGMA integrity_check` prints `ok`); `-safe` guards untrusted `.sql` files in both CLIs. DuckDB 2.0 agent mode auto-enables on non-TTY agent runs and silently truncates at 1,000 rows / 10 KB / 500 chars—pass `-no-agent` (overrides `DUCKDB_AGENT_MODE=1`) or `-json`/`-csv`/`-markdown`.

## Workflow

1. **Inspect, bound, isolate**: `DESCRIBE`/`SUMMARIZE` (pin CSV types), `SET max_execution_time=<ms>`, mark `LIMIT` previews partial, export Parquet (commit `.sql`, not `.duckdb`; open `-readonly`).
1. **Reconcile grain, nulls, bounds, & money**: check key uniqueness and pre/post-join counts (`1:N` fan-out), use `NOT EXISTS` over `NOT IN (nullable)`, `IS NOT DISTINCT FROM`, `NaN` vs `NULL`, UTC `[start, end)` (never `BETWEEN` on timestamps), `DECIMAL`/minor ints for money, and `NULLIF(denom, 0)`. Audit via [quality-and-dbt](references/quality-and-dbt.md) and `fmind-review-data` (`fmind-review-analytics` on KPI/stats; [subagent](../subagent/SKILL.md)).

## Gotchas

- **Live-written SQLite**: query a `.backup` snapshot (plain `cp` misses WAL commits) or `sqlite3 -readonly`; first `ATTACH ... (TYPE sqlite)` needs network for `sqlite`.
- **DuckDB 2.0 changes**: defaults to `v2.0.0+` (`-storage-version v1.5.6` / `STORAGE_VERSION 'v1.5.6'` for 1.x readers); use `lambda x: x + 1`, `//`/`%` by zero errors, `~` is partial regex ([migration](https://duckdb.org/docs/stable/operations_manual/migration)).
- **Quote globs & cap spill**: quote `'events/*.parquet'`; cap shared hosts via `SET memory_limit='256MB'`, `SET threads=1`, `SET temp_directory='...'`, and `SET max_temp_directory_size='...'`.

## Task guides

<!-- guides:start -->

- [postgres](references/postgres.md): Inspect PostgreSQL and pgvector safely via psql and Cloud SQL Auth Proxy: read-only timeouts, EXPLAIN plans, locks.
- [quality-and-dbt](references/quality-and-dbt.md): Lint and format SQL with sqruff or sqlfluff and enforce dbt Core contracts and slim CI tests.
- [remote-storage](references/remote-storage.md): Remote object storage (S3, GCS, HTTP, Hugging Face) and extensions: install, load, and credential providers.

<!-- guides:end -->

## Official Skills

Upstream: `duckdb/duckdb-skills` (querying, formats, attached DBs, spatial, S3, docs) per [vendor-skill policy](../agent-harnesses/references/vendor-skills.md).

## Documentation

- [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) · [agent mode](https://duckdb.org/docs/stable/clients/cli/agent_mode) · [SQLite CLI](https://sqlite.org/cli.html) · Releases: [DuckDB](https://github.com/duckdb/duckdb/releases) · [SQLite](https://sqlite.org/changes.html)
- Companions: [gcloud/bigquery](../gcloud/references/bigquery.md), [mlops/analytics](../mlops/references/analytics.md), [mlops/polars](../mlops/references/polars.md), [python/script](../python/references/script/GUIDE.md), [python/foundation](../python/references/foundation/GUIDE.md).
