---
name: duckdb
description: "Query and export CSV, Parquet, JSON, or SQLite data with DuckDB."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/duckdb
  created: "2026-09-02"
  updated: "2026-10-31"
---

# DuckDB and SQLite

DuckDB is the default engine for local analysis: it reads CSV, Parquet, and JSON directly, attaches SQLite files, and writes any of them back. SQLite stays the embedded store for applications; DuckDB is the tool you point at data.

## Commands

```bash
duckdb -no-init -batch -bail -c "SELECT name, score FROM 'people.csv' WHERE score > 80 ORDER BY score DESC, name LIMIT 20"
duckdb -no-init -batch -bail -json -c "SELECT count(*) AS event_count FROM 'events/*.json'" # aggregate before displaying
duckdb -no-init -batch -bail lab.duckdb -c "CREATE OR REPLACE TABLE people AS FROM 'people.csv'"
duckdb -no-init -batch -bail -c "COPY (FROM 'people.csv') TO 'people.parquet'"        # durable derived data
duckdb -no-init -batch -bail -c "ATTACH 'app.sqlite' AS s (TYPE sqlite, READ_ONLY); SELECT count(*) FROM s.users"
duckdb -no-init -batch -bail -c "SUMMARIZE FROM 'people.parquet'"                   # column statistics
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite '.schema'
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly app.sqlite 'PRAGMA integrity_check'
```

Both interactive and batch invocations can load `~/.duckdbrc` or `~/.sqliterc`, including executable SQL and dot commands; this workstation ships neither, but other machines may. For reproducible scripts, skip those files (`duckdb -no-init`, `sqlite3 -init /dev/null`), stop on errors with `-batch -bail`, and select output explicitly with `-json`, `-csv`, or `-markdown`; an output-mode flag alone does not suppress initialization. Without an output mode, DuckDB 2.0 detects an agent's environment and renders compact Markdown with a row cap, row count, and result hash, plus JSON errors; keep that for previews and pass an explicit mode (or `-no-agent`) for machine output. SQLite integrity checks return rows: require `ok`, because a successful process exit alone does not establish integrity.

## Workflow

1. **Look before querying**: `DESCRIBE FROM '<file>'` and `SUMMARIZE` reveal types, nulls, and ranges; fix a wrong inference with `read_csv('<file>', types={'id': 'BIGINT'})`.
1. **Bound displayed results**: project needed columns, filter rows, and aggregate before returning data. Use an ordered `LIMIT` for a preview and label it as partial; calculate totals over the full filtered set. Export complete results with `COPY` when needed instead of printing every row. Cap exploratory queries over large data with `SET max_execution_time=<ms>`.
1. **Keep queries in files**: `duckdb -no-init -batch -bail -f analysis.sql` for anything longer than one line, committed next to the data description.
1. **Persist derived data as Parquet**: keep rebuildable `.duckdb` files out of Git and commit the SQL that produces them; use `-readonly` for inspection of an existing database.
1. **Export for the reader**: `-markdown` for a report, `-json` for another tool, `COPY ... TO 'out.csv' (HEADER)` for a spreadsheet.

Analysis and export alone do not establish migration or recovery safety for an application schema or persisted format.

## Gotchas

- **Keep DuckDB off live SQLite databases**: do not open one while the app writes to it; use a consistent SQLite backup or `sqlite3 -readonly` directly. A plain copy of the main file can omit committed WAL data; use SQLite's backup API or `.backup` for a snapshot. `ATTACH ... (TYPE sqlite)` autoinstalls the `sqlite` extension, which needs network the first time.
- **Pin storage for 1.x readers**: DuckDB 2.0 writes the v2.0.0 storage format by default (`duckdb_databases()` tags it `storage_version=v2.0.0+`), which 1.x cannot open; create the file with `-storage-version v1.5.6` (or `ATTACH ... (STORAGE_VERSION 'v1.5.6')`) when a 1.x process such as an older Python `duckdb` must read it.
- **Glob paths quote as strings**: `'events/*.parquet'` works, unquoted paths do not.
- **Port 1.x SQL deliberately**: DuckDB 2.0 rejects `x -> x + 1` lambdas (write `lambda x: x + 1`), raises on integer `//` and `%` by zero, and makes `~` a partial regex match; check the [migration guide](https://duckdb.org/docs/stable/operations_manual/migration) when reusing 1.x SQL.
- **Size memory and spill conservatively**: size the budget from available RAM and disk; start conservatively on a shared machine, for example `SET memory_limit='256MB'` and `SET threads=1`, then measure. Many operators spill to disk, but `memory_limit` is not a process-wide hard limit and some allocations or operators can still exhaust memory. Set a task-owned temporary directory and `max_temp_directory_size` when spill volume matters; preserve the workstation's required disk headroom.

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
