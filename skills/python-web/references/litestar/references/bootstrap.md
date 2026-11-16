# Litestar Application Bootstrap

Start from [python-stack](../../../../python-stack/references/foundation/GUIDE.md), adding only needed integrations; existing services keep their framework, server, and database.

## Stateless API example

For stateless webhook, AI, or Cloud Run microservices without a database:

```bash
UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'litestar>=2.25.0' 'granian[reload,uvloop]>=2.8.8' 'pydantic>=2.14.3' 'pydantic-settings>=2.16.3' 'structlog>=26.1.0' 'opentelemetry-api>=1.45.2' 'opentelemetry-sdk>=1.45.2' 'opentelemetry-exporter-otlp-proto-http>=1.45.2'
UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev 'anyio>=4.16.0'
```

Place [init-api.py](../templates/init-api.py) at `src/<package>/__init__.py`, [telemetry.py](../../../../python-stack/references/foundation/templates/telemetry.py) at `src/<package>/telemetry.py`, [main.py](../../../../python-stack/references/argparse/templates/main.py) at `src/<package>/__main__.py`, and [test_api.py](../templates/test_api.py) at `tests/test_api.py`; drop `test:integration` from `mise.toml` unless integration tests are added.

## Database-backed example

1. **Install dependencies** via [uv](../../../../python-stack/references/foundation/GUIDE.md#uv):
   ```bash
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check 'litestar>=2.25.0' 'granian[reload,uvloop]>=2.8.8' 'sqlalchemy[postgresql-asyncpg]>=2.1.8' 'pydantic>=2.14.3' 'pydantic-settings>=2.16.3' 'structlog>=26.1.0'
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev 'anyio>=4.16.0' 'testcontainers>=4.15.0'
   ```
   Base `litestar` already includes CLI, `TestClient`, `msgspec`, and `polyfactory`: add `[jinja]` only for templates, skip `[standard]` (avoids installing `uvicorn` beside Granian), pin `[uvloop]` explicitly (Granian picks `rloop` -> `uvloop` -> `asyncio`), and use `sqlalchemy[postgresql-asyncpg]` (`asyncpg` + `greenlet`, no deptry ignore needed).
1. **Entry points & script**: place [init.py](../templates/init.py) at `src/<package>/__init__.py`, [main.py](../../../../python-stack/references/argparse/templates/main.py) at `src/<package>/__main__.py`, add `[project.scripts]` `<slug> = "<package>:main"`, and replace all placeholders.
1. **Settings**: copy [env.example](../templates/env.example) to `.env.example` and ignored `.env` for local runs (`DATABASE_URL` required when instantiating `Settings()`, CORS closed by default; importing `<package>` or running `--help`/`--version` stays side-effect-free without `.env`).
1. **Tasks & tests**: set `watch` to `uv run granian --interface asgi --factory --reload <package>:create_default_app`, keep `test` offline and `test:integration` opt-in, replace library tests with [test_web.py](../templates/test_web.py), [test_integration.py](../templates/test_integration.py), and `tests/conftest.py` from [conftest.py](../templates/conftest.py) (putting `conftest.py` at repo root triggers deptry on test imports).
1. **Qualify**: document settings, entry points, session lifecycle, `/health`, and `/ready` (`503` on failure) in `AGENTS.md`; run the offline gate + wheel check, and run `test:integration` when Docker is available.

## Application conventions

- **DI & migrations**: inject SQLAlchemy 2 async sessions via `Provide` with lifespan engine disposal (`postgresql+asyncpg://`); adopt `litestar[sqlalchemy]` (Advanced Alchemy) only when earned, and run migrations via `uv add 'alembic>=1.20.1'` + `uv run alembic init --template async alembic`.
- **Health vs readiness**: `/health` has zero external dependencies; `/ready` bounds pool + connect + `SELECT 1` under one deadline (5s in template), returns `503` on failure, and preserves cancellation. Use a non-listening loopback port in offline tests.
- **`sync_to_thread` on sync handlers**: set `sync_to_thread=True` (blocking) or `False` (non-blocking) explicitly, or `LitestarWarning` fails strict warnings.
- **Outbound HTTP**: share one `httpx2.AsyncClient` (`httpx.AsyncClient` if already locked) per [api-client](../../../../python-stack/references/api-client/GUIDE.md).
- **Static & SSR**: serve content-hashed files via `create_static_files_router(..., cache_control=CacheControlHeader(max_age=31_536_000, immutable=True, public=True))` + standalone [tailwind](../../../../web-frontend/references/tailwind.md) (no CDN). Import `HTMXPlugin`/`HTMXRequest` from `litestar.plugins.htmx` and `JinjaTemplateEngine` from `litestar.plugins.jinja` (`litestar.contrib.jinja` is removed in `3.0`); skip Node-bound `litestar-vite` and `litestar-inertia`.
- **Logs**: disable `StructLoggingConfig(log_exceptions="never")` and handle `500`s with a redacted handler (`error=type(exc).__name__`, `path=request.url.path`), leave middleware request logging off (captures bodies by default), and propagate `_granian` in `log_dictconfig`. Wire [telemetry.py](../../../../python-stack/references/foundation/templates/telemetry.py) per [observability](../../../../python-stack/references/observability.md).
