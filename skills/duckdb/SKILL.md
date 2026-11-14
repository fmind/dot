---
name: duckdb
description: "Query and export CSV, Parquet, JSON, SQLite, and PostgreSQL data with DuckDB and pgcli."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/duckdb
  created: "2026-09-02"
  updated: "2026-11-14"
---

# DuckDB, SQLite, and PostgreSQL

Use DuckDB for local analytics across CSV, Parquet, JSON, and attached SQLite files; keep SQLite for embedded application state.

## Commands

```bash
duckdb -no-init -light-mode -batch -bail -json -c "SELECT count(*) AS n FROM 'events/*.json'"
duckdb -no-init -light-mode -batch -bail -c "ATTACH 'app.sqlite' AS s (TYPE sqlite, READ_ONLY); SELECT count(*) FROM s.users"
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite '.schema'
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly app.sqlite 'PRAGMA integrity_check'
```

## PostgreSQL (`pgcli`)

Use `pgcli` non-interactively with explicit bounds and credentials outside `argv`:

```bash
pgcli --less-chatty -w --row-limit 0 --timeout 10 --single-connection -t -D analytics -c "SELECT id, status FROM events ORDER BY id DESC LIMIT 20"
```

- Pass `--less-chatty -w --row-limit 0 --timeout 10` to suppress banners/prompts cleanly (`-t` for unframed rows; `--single-connection` on pooled PgBouncer/Cloud SQL endpoints); `psycopg[binary]` is bundled via mise (`vi = True` recommended in `~/.config/pgcli/config`).
- Authenticate via `.pgpass`, `PGPASSFILE`, `PGSERVICE`, or alias (`-D`), never inline DSN passwords (`postgresql://user:pass@...`), never pass `--log-file` on sensitive queries, and require explicit user approval before `-y` (`--yes`) or writes.

Always pass `duckdb -no-init -light-mode -batch -bail` and `sqlite3 -init /dev/null -batch -bail` (skipping DuckDB 2.0's 5s OSC 11 terminal probe when `-no-init` bypasses `~/.duckdbrc`). Pass explicit `-json`, `-csv`, `-markdown`, or `-no-agent` when parsing output (`PRAGMA integrity_check` must literally print `ok`).

## Workflow

1. **Inspect, bound, and isolate**: start with `DESCRIBE` / `SUMMARIZE` (pin CSV types cleanly), guard scans with `SET max_execution_time=<ms>`, report `LIMIT` previews as partial, persist derived datasets as Parquet (commit `.sql`, never `.duckdb`; open existing DBs `-readonly`), and match output flags to consumers.

## Gotchas

- **Never attach live-written SQLite files**: query a `.backup` snapshot (plain `cp` misses WAL commits) or `sqlite3 -readonly` directly; first-time `ATTACH ... (TYPE sqlite)` needs network to install `sqlite`.
- **DuckDB 2.0 storage and SQL changes**: files default to `v2.0.0+` (`duckdb_databases()`), unreadable by 1.x—pass `-storage-version v1.5.6` or `ATTACH ... (STORAGE_VERSION 'v1.5.6')` for 1.x readers. In 2.0 SQL, write `lambda x: x + 1` (not `x -> x + 1`), integer `//`/`%` by zero errors, and `~` is a partial regex match ([migration](https://duckdb.org/docs/stable/operations_manual/migration)).
- **Quote globs as strings**: `'events/*.parquet'`, not bare shell globs.
- **Cap memory and spill**: start conservative on shared hosts (`SET memory_limit='256MB'`, `SET threads=1`—`memory_limit` is not a hard process cap) and set a task temp dir + `max_temp_directory_size` to protect disk headroom.

## Task guides

<!-- guides:start -->

- [remote-storage](references/remote-storage.md): Remote object storage (S3, GCS, HTTP, Hugging Face) and extensions: install, load, and credential providers.

<!-- guides:end -->

## Official Skills

Upstream: `duckdb/duckdb-skills`, with separate selections for querying, file formats, attached databases, spatial, S3, and documentation lookup. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) · [agent mode](https://duckdb.org/docs/stable/clients/cli/agent_mode) · [SQLite CLI](https://sqlite.org/cli.html) · [pgcli docs](https://www.pgcli.com/docs)
- Releases: [DuckDB](https://github.com/duckdb/duckdb/releases) · [SQLite changes](https://sqlite.org/changes.html)
- Companion skills: [python-script](../python-stack/references/python-script/GUIDE.md) (a one-file pipeline when SQL is not enough), [python-stack](../python-stack/references/foundation/GUIDE.md) (typed application data access and embedded SQLite).
