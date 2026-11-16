---
name: database-and-jobs
description: "Configure async Alembic migrations, connection pools, SQLite WAL, pgqueuer, and Cloud Tasks workers."
---

# Databases, Migrations, & Background Jobs

Patterns for durable persistence and async background execution on PostgreSQL (`sqlalchemy[postgresql-asyncpg]`), SQLite, and GCP Cloud Run ([litestar](litestar/GUIDE.md) and [containerize](../../docker/references/containerize/GUIDE.md) own framework and local container wiring).

## PostgreSQL Pools & Local Dev

- **Pool bounds**: pass `pool_pre_ping=True, pool_size=5, max_overflow=10` (plus `pool_recycle=1800` behind Cloud SQL / PgBouncer) on `create_async_engine`; size `pool_size` so `(replicas * (pool_size + max_overflow))` stays below database `max_connections`.
- **Statement timeouts**: configure `connect_args={"server_settings": {"statement_timeout": "10000"}}` for request-path engines so runaway queries cannot exhaust the pool.
- **Local container**: copy [compose.yaml](../../docker/references/containerize/templates/compose.yaml) (loopback-bound `127.0.0.1:5432:5432` Postgres/pgvector with `pg_isready` healthcheck and named volume). Never connect live tests without `-m integration`.

## Async Alembic Migrations

1. **Bootstrap**: `UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'alembic>=1.20.1' && uv run alembic init --template async alembic`.
1. **Explicit constraint names**: bind one shared `MetaData(naming_convention={"ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"})` on declarative `Base.metadata` so Postgres autogenerate downgrades never break on server-assigned names.
1. **Safe rollouts**: review every `alembic revision --autogenerate` diff, prefer expand-and-contract steps for non-nullable or column drops, rehearse upgrade + downgrade against a backed-up copy, and run migrations as a dedicated release job rather than on web worker startup.

## SQLite Concurrency

Apply connection pragmas on every opened connection (via SQLAlchemy `@event.listens_for(engine.sync_engine, "connect")` or `sqlite3.connect` helper):

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

Serialize writes through one worker/queue or `BEGIN IMMEDIATE` transaction when concurrent asyncio/thread writers share a single file.

## Background Jobs & Outbox

- **Transactional Postgres jobs (`pgqueuer`)**: add `'pgqueuer'` when Postgres already runs and jobs require transactional enqueueing with business state (avoids Redis ops overhead). Enqueue inside the same DB transaction (`INSERT` outbox/job + domain row) and run the worker process under a bounded semaphore with SIGTERM drain.
- **GCP serverless push (`Cloud Tasks`)**: enqueue via `google-cloud-tasks` inside bounded retry wrappers and expose an internal `POST /tasks/<job>` handler on Cloud Run verified by [Cloud Tasks OIDC authentication](security-and-auth.md). Design every handler idempotently on `X-CloudTasks-TaskName` + execution state table, enforce bounded retry deadlines, and route terminal failures to logging/alerts or a dead-letter state.

## Documentation

- [Alembic async cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) · [SQLAlchemy naming conventions](https://docs.sqlalchemy.org/en/20/core/constraints.html#configuring-constraint-naming-conventions) · [pgqueuer](https://pgqueuer.readthedocs.io/) · [Cloud Tasks HTTP targets](https://cloud.google.com/tasks/docs/creating-http-target-tasks)
