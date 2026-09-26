---
name: duckdb
description: "Query, transform, and export files or databases with DuckDB and SQLite."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/duckdb
  created: "2026-09-02"
  updated: "2026-09-26"
---

# DuckDB and SQLite

DuckDB is the default engine for local analysis: it reads CSV, Parquet, and JSON directly, attaches SQLite files, and writes any of them back. SQLite stays the embedded store for applications; DuckDB is the tool you point at data.

## Commands

```bash
duckdb -init /dev/null -batch -bail -c "SELECT name, score FROM 'people.csv' WHERE score > 80 ORDER BY score DESC, name LIMIT 20"
duckdb -init /dev/null -batch -bail -json -c "SELECT count(*) AS event_count FROM 'events/*.json'" # aggregate before displaying
duckdb -init /dev/null -batch -bail lab.duckdb -c "CREATE OR REPLACE TABLE people AS FROM 'people.csv'"
duckdb -init /dev/null -batch -bail -c "COPY (FROM 'people.csv') TO 'people.parquet'"        # durable derived data
duckdb -init /dev/null -batch -bail -c "ATTACH 'app.sqlite' AS s (TYPE sqlite, READ_ONLY); SELECT count(*) FROM s.users"
duckdb -init /dev/null -batch -bail -c "SUMMARIZE FROM 'people.parquet'"                   # column statistics
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite '.schema'
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly app.sqlite 'PRAGMA integrity_check'
```

Both interactive and batch invocations can load `~/.duckdbrc` or `~/.sqliterc`, including executable SQL and dot commands. For reproducible scripts, skip those files with `-init /dev/null`, stop on errors with `-batch -bail`, and select output explicitly with `-json`, `-csv`, or `-markdown`; an output-mode flag alone does not suppress initialization. SQLite integrity checks return rows: require `ok`, because a successful process exit alone does not establish integrity.

## Workflow

1. **Look before querying**: `DESCRIBE FROM '<file>'` and `SUMMARIZE` reveal types, nulls, and ranges; fix a wrong inference with `read_csv('<file>', types={'id': 'BIGINT'})`.
1. **Bound displayed results**: project needed columns, filter rows, and aggregate before returning data. Use an ordered `LIMIT` for a preview and label it as partial; calculate totals over the full filtered set. Export complete results with `COPY` when needed instead of printing every row.
1. **Keep queries in files**: `duckdb -init /dev/null -batch -bail -f analysis.sql` for anything longer than one line, committed next to the data description.
1. **Persist derived data as Parquet**: keep rebuildable `.duckdb` files out of Git and commit the SQL that produces them; use `-readonly` for inspection of an existing database.
1. **Check results**: row counts before and after joins, `count(*) FILTER (WHERE x IS NULL)` on keys, and a spot check against the source.
1. **Export for the reader**: `-markdown` for a report, `-json` for another tool, `COPY ... TO 'out.csv' (HEADER)` for a spreadsheet.

Use [data-migration](../data-migration/SKILL.md) when changing an application schema or persisted format; analysis and export alone do not establish migration or recovery safety.

## Gotchas

- **Do not open a live SQLite database with DuckDB while the app writes to it**: use a consistent SQLite backup or `sqlite3 -readonly` directly. A plain copy of the main file can omit committed WAL data; use SQLite's backup API or `.backup` for a snapshot.
- **Glob paths quote as strings**: `'events/*.parquet'` works, unquoted paths do not.
- **Memory and spill space**: size the budget from available RAM and disk; start conservatively on a shared machine, for example `SET memory_limit='256MB'` and `SET threads=1`, then measure. Many operators spill to disk, but `memory_limit` is not a process-wide hard limit and some allocations or operators can still exhaust memory. Set a task-owned temporary directory and `max_temp_directory_size` when spill volume matters; preserve the workstation's required disk headroom.
- **Extensions load on demand**: `httpfs`, `spatial`, `postgres` install once with `INSTALL <ext>; LOAD <ext>;` and need network the first time.
- **Secrets**: use the selected extension's credential provider, never literal credentials in SQL. Core `httpfs` accesses GCS through the S3 API and needs HMAC credentials; its `credential_chain` does not consume Google ADC. ADC requires a separately reviewed compatible extension, such as the community [gcs extension](https://duckdb.org/community_extensions/extensions/gcs), or downloading through an authorized Google client first.

## Official Skills

Upstream: `duckdb/duckdb-skills`, with separate selections for querying, file formats, attached databases, spatial, S3, and documentation lookup. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [DuckDB CLI](https://duckdb.org/docs/stable/clients/cli/overview) · [SQLite CLI](https://sqlite.org/cli.html)
- Releases: [DuckDB](https://github.com/duckdb/duckdb/releases) · [SQLite changes](https://sqlite.org/changes.html)
- Companion skills: [python-script](../python-stack/references/python-script/GUIDE.md) (a one-file pipeline when SQL is not enough), [python-stack](../python-stack/references/foundation/GUIDE.md) (typed application data access and embedded SQLite).
