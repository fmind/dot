# Litestar Application Bootstrap

For a new application, create the minimal foundation through [python-stack](../../python-stack/SKILL.md), then apply only the integrations the application needs before final qualification. Existing services retain their framework, server, and database choices.

## Database-backed example

The bundled example uses typed settings, SQLAlchemy async sessions with asyncpg, and Granian. A service without a database should omit its engine, dependency, readiness query, and integration fixtures.

1. Add the runtime dependencies through [uv](../../uv/SKILL.md):
   ```bash
   uv add 'litestar>=2.24.0' 'granian[reload,uvloop]>=2.8.1' 'sqlalchemy>=2.0.52' 'asyncpg>=0.31.0' 'pydantic>=2.13.4' 'pydantic-settings>=2.15.0' 'structlog>=26.1.0'
   uv add --dev 'anyio>=4.14.2' 'testcontainers>=4.15.0'
   ```
   These constraints preserve the example baseline; verify selected versions against the lock and installed APIs.
   The base package already ships the CLI, `TestClient`, msgspec, and Polyfactory: add `[jinja]` only when the service renders templates, and avoid `[standard]`, which installs a second ASGI server (uvicorn) next to Granian. Granian selects rloop, then uvloop, then asyncio at startup, so pin `[uvloop]` explicitly instead of inheriting it from another package.
1. Replace the foundation example with [init.py](init.py) at `src/<package>/__init__.py`. Add `src/<package>/__main__.py`:
   ```python
   from . import main

   if __name__ == "__main__":
       main()
   ```
1. Add `[project.scripts]` with `<slug> = "<package>:main"`. Replace placeholders throughout, including the import package used by Granian.
1. Copy [env.example](env.example) to `.env.example` and the ignored `.env` before importing the application. Require `DATABASE_URL`, keep CORS closed unless explicitly configured, and use fake local values for offline qualification. Add `[env]` with `_.file = ".env"` to `mise.toml`; [mise](../../mise/SKILL.md) owns dotenv loading.
1. Set the `watch` task to `uv run granian --interface asgi --reload <package>:app`. Keep the shared `test` task offline and the `test:integration` task opt-in.
1. Replace the library example tests with [test_web.py](test_web.py) and [test_integration.py](test_integration.py); copy [conftest.py](conftest.py) to the project root. Its Postgres fixture starts Docker only when requested by the integration test. Add `"conftest.py" = ["S105"]` to `[tool.ruff.lint.per-file-ignores]` for deliberate fake fixture secrets when needed.
1. Update `AGENTS.md` with the settings, command/module entry points, async session lifecycle, dependency-free `/health`, and database-backed `/ready` returning 503 on failure. Run the shared gate and installed-wheel checks with fake settings; exercise integration tests separately when Docker is available.

## Application conventions

- Use SQLAlchemy 2 async sessions injected through `Provide`, with engine cleanup owned by application lifespan and `postgresql+asyncpg` URLs. Advanced Alchemy (the `litestar[sqlalchemy]` extra) replaces hand-written sessions and repositories once the model layer earns it. When persisted schema migrations are needed, `uv add 'alembic>=1.19.1'` and initialize with `uv run alembic init --template async alembic`.
- Keep `/health` independent of external services. The database example's `/ready` executes `SELECT 1` and handles database and connection failures.
- A handler may be synchronous: declare `sync_to_thread=True` for blocking work or `sync_to_thread=False` when it is guaranteed non-blocking. An undeclared sync handler raises `LitestarWarning`, which `filterwarnings = ["error"]` turns into a test failure.
- Use `httpx.AsyncClient` for outbound HTTP through [api-client](../../api-client/SKILL.md).
- Self-host static assets with `create_static_files_router(path="/static", directories=["static"], cache_control=CacheControlHeader(max_age=31_536_000, immutable=True, public=True))`. `immutable` is only safe when the content hash is in the filename, so emit hashed names. Compile CSS with the mise-pinned standalone `tailwindcss` binary; no Node.js toolchain, no CDN.
- Server-rendered pages cost no extra runtime dependency: `HTMXPlugin` and `HTMXRequest` come from `litestar.plugins.htmx` because `litestar-htmx` is a core Litestar dependency, and `JinjaTemplateEngine` comes from `litestar.plugins.jinja` with the `[jinja]` extra (`litestar.contrib.jinja` is deprecated since 2.22.0 and removed in 3.0). Reject `litestar-vite` and `litestar-inertia`: both require a Node toolchain.
- The example configures Granian with `Interfaces.ASGI` and installs `StructlogPlugin`, so application, framework, and library logs share one format: console on a TTY, JSON otherwise. `log_exceptions="always"` keeps unhandled 500s on the record, and request logging stays off because its defaults capture request and response bodies. [observability](../../observability/SKILL.md) owns provider fields and trace correlation.
