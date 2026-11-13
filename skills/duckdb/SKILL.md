---
name: duckdb
description: "Query and export CSV, Parquet, JSON, SQLite, and PostgreSQL data with DuckDB and pgcli."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/duckdb
  created: "2026-09-02"
  updated: "2026-11-13"
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
pgcli --less-chatty -w --row-limit 0 --timeout 10 -D analytics --ping
pgcli --less-chatty -w --row-limit 0 --timeout 10 -t -D analytics -c "SELECT id, status FROM events ORDER BY id DESC LIMIT 20"
```

- Pass `--less-chatty -w --row-limit 0 --timeout 10` so `pgcli` skips banners, never stalls on password/row prompts, and fails fast; use `-t` for unframed machine output.
- Authenticate via `.pgpass`, `PGPASSFILE`, `PGSERVICE`, or configured alias (`-D`), never inline DSN passwords (`postgresql://user:pass@...`) in commands.
- Require explicit user approval before `-y` (`--yes`) or write statements.

Always suppress rc files (`duckdb -no-init -light-mode`, `sqlite3 -init /dev/null`; `-light-mode` skips DuckDB 2.0's 5s OSC 11 terminal background probe when `-no-init` bypasses `~/.duckdbrc`) and fail fast (`-batch -bail`). DuckDB 2.0 auto-enables compact agent Markdown previews (capped rows + count + hash + JSON errors); pass explicit `-json`, `-csv`, `-markdown`, or `-no-agent` for machine parsing. Verify `PRAGMA integrity_check` outputs `ok` (exit 0 alone does not prove integrity).

## Workflow

1. **Inspect schema first**: run `DESCRIBE FROM '<file>'` and `SUMMARIZE`; override bad inferences via `read_csv('<file>', types={'id': 'BIGINT'})`.
1. **Bound output and runtime**: project, filter, and aggregate before printing; mark `LIMIT` previews as partial, compute totals on the full filter, `COPY` large outputs to disk, and guard exploratory scans with `SET max_execution_time=<ms>`.
1. **Commit `.sql`, not `.duckdb`**: run `duckdb -no-init -light-mode -batch -bail -f analysis.sql`, persist derived datasets as Parquet, gitignore rebuildable `.duckdb` files, and inspect existing DBs with `-readonly`.
1. **Match export format to consumer**: `-markdown` for prose, `-json` for tools, `COPY ... TO 'out.csv' (HEADER)` for spreadsheets (ad-hoc queries do not prove schema migration safety).

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

- [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) · [agent mode](https://duckdb.org/docs/stable/clients/cli/agent_mode) · [SQLite CLI](https://sqlite.org/cli.html)
- Releases: [DuckDB](https://github.com/duckdb/duckdb/releases) · [SQLite changes](https://sqlite.org/changes.html)
- Companion skills: [python-script](../python-stack/references/python-script/GUIDE.md) (a one-file pipeline when SQL is not enough), [python-stack](../python-stack/references/foundation/GUIDE.md) (typed application data access and embedded SQLite).
