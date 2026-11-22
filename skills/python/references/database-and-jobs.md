---
name: database-and-jobs
description: "Configure async Postgres/SQLite pools, Alembic, obstore, pgqueuer, and Cloud Tasks."
---

# Databases, Migrations, & Background Jobs

Durable persistence, object storage, and async jobs on PostgreSQL (`sqlalchemy[postgresql-asyncpg]` or `sqlalchemy[postgresql-psycopg]`), SQLite, and Cloud Run ([litestar](litestar/GUIDE.md) and [containerize](../../containers/references/containerize/GUIDE.md) own framework and container wiring).

## PostgreSQL Pools & Local Dev

- **Driver choice**: default to `sqlalchemy[postgresql-asyncpg]` for pure async ASGI, or `psycopg[binary,pool]>=3.3.9` (`postgresql+psycopg`, `prepare_threshold=None`) when sharing sync/async models or behind PgBouncer transaction pooling.
- **Pool bounds**: set `pool_pre_ping=True, pool_size=5, max_overflow=10` (plus `pool_recycle=1800` behind Cloud SQL / PgBouncer) on `create_async_engine`; keep `replicas * (pool_size + max_overflow)` under DB `max_connections`.
- **Statement timeouts (driver-specific)**: pass `connect_args={"server_settings": {"statement_timeout": "10000"}}` on `asyncpg`, or `connect_args={"options": "-c statement_timeout=10000"}` on `psycopg`, so stalled queries cannot exhaust the pool.
- **SQLAlchemy 2 async traps & test isolation**: set `lazy="raise"` on ORM relationships and eager-load explicitly (`selectinload`/`joinedload`) to prevent `MissingGreenlet` crashes; keep `expire_on_commit=False` and explicit `async with session.begin():` write transactions. Against session-scoped `PostgresContainer` fixtures, run `alembic upgrade head` once per session and wrap each test in a rolled-back outer transaction / savepoint.
- **Local container**: copy [compose.yaml](../../containers/references/containerize/templates/compose.yaml) (`127.0.0.1:5432:5432` Postgres/pgvector + `pg_isready` + named volume); guard live tests behind `-m integration`.

## Async Alembic Migrations

1. **Bootstrap**: `UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'alembic>=1.20.1' && uv run alembic init --template async alembic`.
1. **Explicit constraint names**: bind `MetaData(naming_convention={"ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"})` on `Base.metadata` so autogenerate downgrades stay deterministic.
1. **Safe rollouts**: inspect every `alembic revision --autogenerate` diff, use expand-and-contract for drops/non-nullables, rehearse upgrade + downgrade on a backup copy, and run migrations in a release job rather than web worker startup.

## SQLite Concurrency

Use `aiosqlite>=0.22.1` (`sqlite+aiosqlite:///...`) and apply pragmas on every connection (`@event.listens_for(engine.sync_engine, "connect")` or a `sqlite3.connect` helper):

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

Serialize concurrent writers through one worker/queue or `BEGIN IMMEDIATE`.

## Background Jobs & Outbox

- **Transactional Postgres jobs (`pgqueuer`)**: add `'pgqueuer'` when Postgres already runs and jobs need transactional enqueueing with business state; enqueue in the same DB transaction and drain under a bounded semaphore on SIGTERM.
- **GCP serverless push (`Cloud Tasks`)**: enqueue via `google-cloud-tasks` with bounded retries and verify `POST /tasks/<job>` via [Cloud Tasks OIDC](security-and-auth.md); make handlers idempotent on `X-CloudTasks-TaskName`, cap retry deadlines, and route terminal failures to alerts or a DLQ.

## Object Storage I/O

- **Async blob & Arrow streaming**: read/write GCS, S3, or R2 via `obstore>=0.12.1` under Workload Identity/ADC instead of buffering on container disks.
- **Bucket admin & signed URLs**: add `google-cloud-storage>=3.17.1` for V4 signed URLs or GCS lifecycle/IAM.

## Documentation

- [Alembic async cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) · [SQLAlchemy naming conventions](https://docs.sqlalchemy.org/en/20/core/constraints.html#configuring-constraint-naming-conventions) · [Psycopg 3](https://www.psycopg.org/psycopg3/docs/) · [aiosqlite](https://aiosqlite.omnilib.dev/en/stable/) · [obstore](https://developmentseed.org/obstore/latest/) · [Cloud Storage Python](https://cloud.google.com/python/docs/reference/storage/latest) · [pgqueuer](https://janbjorge.github.io/pgqueuer/) · [Cloud Tasks HTTP targets](https://cloud.google.com/tasks/docs/creating-http-target-tasks)
