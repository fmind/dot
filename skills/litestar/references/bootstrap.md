# Litestar Application Bootstrap

For a new application, create the minimal foundation through [python-stack](../../python-stack/SKILL.md), then apply only the integrations the application needs before final qualification. Existing services retain their framework, server, and database choices.

## Database-backed example

The bundled example uses typed settings, SQLAlchemy async sessions with asyncpg, and Granian. A service without a database should omit its engine, dependency, readiness query, and integration fixtures.

1. Add the runtime dependencies through [uv](../../uv/SKILL.md):
   ```bash
   uv add 'litestar[standard]>=2.24.0' 'granian[reload]>=2.8.1' 'sqlalchemy>=2.0.52' 'asyncpg>=0.31.0' 'alembic>=1.19.1' 'pydantic>=2.13.4' 'pydantic-settings>=2.15.0' 'structlog>=26.1.0'
   uv add --dev 'anyio>=4.14.2' 'testcontainers[postgres]>=4.15.0'
   ```
   These constraints preserve the example baseline; verify selected versions against the lock and installed APIs.
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

- Use SQLAlchemy 2 async sessions injected through `Provide`, with engine cleanup owned by application lifespan. Initialize Alembic with `uv run alembic init --template async alembic` when persisted schema migrations are needed; use `postgresql+asyncpg` URLs.
- Keep `/health` independent of external services. The database example's `/ready` executes `SELECT 1` and handles database and connection failures.
- Use `httpx.AsyncClient` for outbound HTTP through [api-client](../../api-client/SKILL.md).
- Self-host static assets under `/static/` with SHA-256 cache busting and long-lived cache headers; avoid CDN dependencies.
- The example configures Granian with `Interfaces.ASGI`. It renders console logs in development and JSON elsewhere; [observability](../../observability/SKILL.md) owns provider fields and trace correlation.
