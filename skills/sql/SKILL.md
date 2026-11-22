---
name: sql
description: "Query/export CSV, Parquet, JSON, SQLite, PostgreSQL via DuckDB, sqlite3, psql; SQL/dbt quality."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sql
  created: "2026-09-02"
  updated: "2026-11-22"
---

# SQL, DuckDB, SQLite & PostgreSQL

Use DuckDB for local analytics across CSV, Parquet, JSON, and attached SQLite files; keep SQLite for embedded application state; use [postgres](references/postgres.md) for live PostgreSQL/`pgvector` inspection via `psql`.

## Commands

```bash
duckdb -no-init -light-mode -batch -bail -json -c "SELECT count(*) AS n FROM 'events/*.json'"
duckdb -no-init -light-mode -batch -bail -c "ATTACH 'app.sqlite' AS s (TYPE sqlite, READ_ONLY); SELECT count(*) FROM s.users"
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite '.schema'
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly app.sqlite 'PRAGMA integrity_check'
```

Keep the non-interactive flags above on every call (`-light-mode` skips DuckDB 2.0's 5s OSC 11 probe). Pass `-json`, `-csv`, `-markdown`, or `-no-agent` when parsing output (`PRAGMA integrity_check` must print `ok`).

## Workflow

1. **Inspect, bound, isolate**: run `DESCRIBE`/`SUMMARIZE` (pin CSV types), guard scans with `SET max_execution_time=<ms>`, mark `LIMIT` previews partial, export Parquet (commit `.sql`, not `.duckdb`; open DBs `-readonly`), and match output flags.
1. **Reconcile grain and nulls**: check key uniqueness, pre/post-join counts (`1:N` fan-out), `IS NOT DISTINCT FROM`, and `NaN` vs `NULL` aggregates before reporting; audit SQL/dbt via [quality-and-dbt](references/quality-and-dbt.md) and `fmind-review-data` ([subagent](../subagent/SKILL.md)).

## Gotchas

- **Never attach live-written SQLite files**: query a `.backup` snapshot (plain `cp` misses WAL commits) or `sqlite3 -readonly` directly; first-time `ATTACH ... (TYPE sqlite)` needs network to install `sqlite`.
- **DuckDB 2.0 storage and SQL changes**: files default to `v2.0.0+` (`duckdb_databases()`), unreadable by 1.x—pass `-storage-version v1.5.6` or `ATTACH ... (STORAGE_VERSION 'v1.5.6')` for 1.x readers. In 2.0 SQL, write `lambda x: x + 1` (not `x -> x + 1`), integer `//`/`%` by zero errors, and `~` is a partial regex match ([migration](https://duckdb.org/docs/stable/operations_manual/migration)).
- **Quote globs as strings**: `'events/*.parquet'`, not bare shell globs.
- **Cap memory and spill**: start conservative on shared hosts (`SET memory_limit='256MB'`, `SET threads=1`—`memory_limit` is not a hard process cap) and set a task temp dir + `max_temp_directory_size` to protect disk headroom.

## Task guides

<!-- guides:start -->

- [postgres](references/postgres.md): Inspect PostgreSQL and pgvector safely via psql and Cloud SQL Auth Proxy: read-only timeouts, EXPLAIN plans, locks.
- [quality-and-dbt](references/quality-and-dbt.md): Lint and format SQL with sqruff or sqlfluff and enforce dbt Core contracts and slim CI tests.
- [remote-storage](references/remote-storage.md): Remote object storage (S3, GCS, HTTP, Hugging Face) and extensions: install, load, and credential providers.

<!-- guides:end -->

## Official Skills

Upstream: `duckdb/duckdb-skills`, with separate selections for querying, file formats, attached databases, spatial, S3, and documentation lookup. Follow the shared [vendor-skill policy](../agent-harnesses/references/vendor-skills.md).

## Documentation

- [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) · [agent mode](https://duckdb.org/docs/stable/clients/cli/agent_mode) · [SQLite CLI](https://sqlite.org/cli.html)
- Releases: [DuckDB](https://github.com/duckdb/duckdb/releases) · [SQLite changes](https://sqlite.org/changes.html)
- Companion skills: [gcloud/bigquery](../gcloud/references/bigquery.md) (BigQuery dry-runs and byte caps), [mlops/polars](../mlops/references/polars.md) (Python lazy frames), [python/script](../python/references/script/GUIDE.md) (a one-file pipeline when SQL is not enough), [python/foundation](../python/references/foundation/GUIDE.md) (typed application data access and embedded SQLite).
