# Alembic Migrations

Use this guide for Alembic mechanics; [data-migration](../SKILL.md) owns compatibility, backfills, execution authority, and recovery. Inspect the installed Alembic/SQLAlchemy versions, dialect, migration configuration, and revision history before editing.

1. Reuse the repository's migration task and configuration. If Alembic is missing, add it with `uv add alembic` when the deployed migration command needs it, or to the project's development group for development-only use. Initialize only a new migration directory; list the shipped layouts with `uv run alembic list_templates` and pass `-t`, matching an async template to an async driver.
1. Wire `target_metadata` in `env.py` to the application's metadata after importing all model modules. Avoid imports that start the application or contact external services. Retain established constraint naming conventions and schema/table filters; omitted models or unrelated tables can produce unintended drops.
1. Obtain the database connection through the project's secret-safe settings. Inspect the resolved target without printing credentials. Async drivers use the generated async environment and synchronous migration callback through `connection.run_sync`; the ordinary CLI still runs with `uv run alembic`.
1. Inspect local revision heads/history, then query `current` only against an explicitly selected database. Rehearse on a disposable database containing the prior schema and representative data; bring it to the intended parent revision before autogenerating.
1. Generate a candidate revision and read every operation. Autogeneration can express table/column renames as drop/add pairs and cannot infer data backfills; correct these manually and check constraints, defaults, nullability, dialect behavior, and destructive operations.
1. Resolve divergent heads deliberately. Preserve applied revision files; a merge revision reconciles ancestry, but conflicting schema operations still need review. Do not rewrite `down_revision` or use `stamp` to disguise an unapplied change.
1. Upgrade the disposable prior-version database to the intended revision and read preserved data through the application. Run `alembic check` for remaining detectable model/schema differences. Also build a fresh database through the migration chain; rehearse downgrade only when promised and data-safe, with restore as the separate recovery proof.

After configuring an isolated fixture, adapt these commands to the project's config path and intended revision:

```bash
uv run alembic heads
uv run alembic history
uv run alembic current
uv run alembic revision --autogenerate -m "add report status"
```

Review the generated file before applying it. For an intentionally single-head fixture:

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

`revision --autogenerate`, `current`, and `check` can connect to the database. `upgrade` mutates it. Keep these commands bound to the selected fixture during development; a local shell or a read-like command name does not establish a safe database target.

`alembic check` shares autogeneration's detection limits; it does not prove data preservation, locking behavior, or absence of all drift. SQLite rehearsal does not qualify PostgreSQL DDL or concurrency. `stamp` records a revision without executing migrations, and a downgrade cannot restore dropped data.

Sources: [Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [autogeneration and check](https://alembic.sqlalchemy.org/en/latest/autogenerate.html), [branches](https://alembic.sqlalchemy.org/en/latest/branches.html), and [asyncio integration](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic).
