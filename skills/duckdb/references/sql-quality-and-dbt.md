---
name: sql-quality-and-dbt
description: "Lint and format SQL with sqruff or sqlfluff and enforce dbt Core contracts and slim CI tests."
---

# SQL Quality (`sqruff` / `sqlfluff`) & `dbt`

Use `sqruff` (globally installed, Rust-fast) for raw ANSI, PostgreSQL, BigQuery, and DuckDB `.sql` files; use project-pinned `sqlfluff` only when Jinja/dbt template compilation is required.

## `sqruff` (`0.44+`, Default for `.sql`)

Configure a project `.sqruff` at repo root and gate in `mise.toml` (`check:sql`, `format:sql`):

```ini
[sqruff]
dialect = postgres
rules = all

[sqruff:indentation]
indent_unit = space
tab_space_size = 4
```

Run `sqruff lint <paths>` (pass `--format json` for structured CI diagnostics) and `sqruff fix <paths>` safely over raw queries, migrations, and SQL files.

## `sqlfluff` & `dbt Core`

- **When Jinja/dbt templating applies**: add project-scoped `sqlfluff` (`sqlfluff-templater-dbt` for `dbt`) via `uv add --dev`, pin exact `.sqlfluff` dialect/templater config, and run `uv run --locked sqlfluff lint`.
- **`dbt-core` warehouse adapters**: install `dbt-bigquery`, `dbt-postgres`, or `dbt-duckdb` in a dedicated project env.
- **Strict gates & data contracts**: enforce `--warn-error` in CI (`dbt build --warn-error`), define model `contracts` (`enforced: true` + column `data_type`) alongside `not_null`, `unique`, and `relationships` schema tests on boundary models, and pass `--state <prod-manifest-dir> --defer` for slim PR builds so unchanged upstream models are not re-materialized.

## Documentation

- [sqruff docs](https://quarylabs.github.io/sqruff/) · [SQLFluff docs](https://docs.sqlfluff.com/) · [dbt Core contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts) · [dbt slim CI](https://docs.getdbt.com/docs/deploy/continuous-integration)
