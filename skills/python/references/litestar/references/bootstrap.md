# Litestar Application Bootstrap

Start from [foundation](../../foundation/GUIDE.md), adding only needed integrations; existing services keep their framework, server, and database.

## Base dependencies & entry points

1. **Install shared packages** via [uv](../../foundation/GUIDE.md#uv) (skip `[standard]` to avoid `uvicorn`; pin `[uvloop]` explicitly since Granian picks `rloop` -> `uvloop` -> `asyncio`):
   ```bash
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'litestar>=2.25.0' 'granian[reload,uvloop]>=2.8.8' 'pydantic>=2.14.3' 'pydantic-settings>=2.16.3' 'structlog>=26.1.0' 'opentelemetry-api>=1.45.2' 'opentelemetry-sdk>=1.45.2' 'opentelemetry-exporter-otlp-proto-http>=1.45.2'
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev 'anyio>=4.16.0'
   ```
   Base `litestar` includes CLI, `TestClient`, `msgspec`, and `polyfactory`; add `[jinja]` only for templates.
1. **Shared files & script**: place [telemetry.py](../../foundation/templates/telemetry.py) at `src/<package>/telemetry.py` and [main.py](../../argparse/templates/main.py) at `src/<package>/__main__.py`, add `[project.scripts]` `<slug> = "<package>:main"`, replace `<slug>`/`<package>`/`<description>`, and add `[tasks.dev]` (`uv run --locked granian --interface asgi --factory --reload <package>:create_default_app`).

## Profiles

- **Stateless API** (webhooks, AI, Cloud Run microservices without a DB): place [init-api.py](../templates/init-api.py) at `src/<package>/__init__.py` and [test_api.py](../templates/test_api.py) at `tests/test_api.py`; add `[tasks."test:integration"]` only if integration tests are added.
- **Database-backed**: add `'sqlalchemy[postgresql-asyncpg]>=2.1.8'` (`asyncpg` + `greenlet`, or `sqlalchemy[postgresql-psycopg]` with `psycopg[binary,pool]>=3.3.9` behind PgBouncer) and `--dev 'testcontainers>=4.15.0'`. Place [init.py](../templates/init.py) at `src/<package>/__init__.py`, [env.example](../templates/env.example) at `.env.example` + ignored `.env` (`DATABASE_URL` required on `Settings()`, CORS closed by default; `--help`/`--version` stay side-effect-free), and [compose.yaml](../../../../containers/references/containerize/templates/compose.yaml) for local Postgres/pgvector. Keep `test` offline, add `test:integration` (`uv run --locked pytest -q -m integration --force-enable-socket --timeout=600`), and copy [test_web.py](../templates/test_web.py), [test_integration.py](../templates/test_integration.py), and [conftest.py](../templates/conftest.py) under `tests/` (root `conftest.py` triggers deptry). Document settings, entry points, session lifecycle, `/health`, and `/ready` (`503`) in `AGENTS.md`.

## Application conventions

- **DI, pools, & auth**: inject SQLAlchemy 2 async sessions via `Provide` with lifespan disposal and bounded pools (`pool_pre_ping=True, pool_size=5, max_overflow=10, pool_recycle=1800` + driver `statement_timeout`); wire Alembic/SQLite WAL/pgqueuer/Cloud Tasks per [database-and-jobs](../../database-and-jobs.md) and OIDC/JWT/HMAC/CSRF/headers per [security-and-auth](../../security-and-auth.md).
- **Health vs readiness**: `/health` has zero external dependencies; `/ready` bounds pool + connect + `SELECT 1` under one deadline (`5s` in template), returns `503` on failure, and preserves cancellation. Use a non-listening loopback port in offline tests.
- **`sync_to_thread` & HTTP client**: set `sync_to_thread=True` or `False` explicitly on sync handlers (else `LitestarWarning` fails strict warnings); share one `httpx2.AsyncClient` (`httpx.AsyncClient` if locked) per [api-client](../../api-client/GUIDE.md).
- **Logs, headers, & OTel**: return RFC 9457 `application/problem+json` and redact unhandled `500`s (`error=type(exc).__name__`, `path=request.url.path`), attach baseline security headers via `ASGIMiddleware`, pass `logging_config=None` with [telemetry.py](../../foundation/templates/telemetry.py), isolate/offload OTel provider shutdown on lifespan exit, and propagate `_granian` in `log_dictconfig` ([observability](../../observability.md)).
