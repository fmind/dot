# Python Project Profiles

## Project Profiles

- **CLI**: a Typer app in `__init__.py` ([init-cli.py](init-cli.py)) exposed through `[project.scripts]`; flags, streams, and exit codes follow [cli-contracts](../../cli-contracts/SKILL.md).
- **Library**: no runtime dependencies by default; omit `__main__.py` and `[project.scripts]`.
- **Data, ML, notebooks**: extension profiles on the library profile — `uv add` only the workload boundary (Polars or DuckDB, scikit-learn or a hardware-specific PyTorch/JAX, JupyterLab or Marimo) in a dependency group.
- **Scripts**: single-file tools with PEP 723 metadata go through [python-script](../../python-script/SKILL.md).

## Web Stack (Litestar)

- **Framework and data**: Litestar with `asyncpg` + SQLAlchemy 2 async sessions injected through `Provide`; Alembic migrations (`uv run alembic init --template async alembic`, `postgresql+asyncpg` URL).
- **Health**: `/health` is dependency-free liveness; `/ready` runs `SELECT 1` and returns 503 on `SQLAlchemyError`.
- **HTTP client**: `httpx.AsyncClient`.
- **Static assets**: self-hosted under `/static/` with SHA-256 cache busting and long-lived cache headers; no CDNs.
- **Server**: `granian` with `uvloop`, passing `Interfaces.ASGI` (the enum, so `ty` stays clean).
- **Logging**: the starter emits console logs in development and JSON elsewhere. Add provider-specific fields and trace correlation per [observability](../../observability/SKILL.md) when deploying.

## ADK Agents (Python API)

The generated agent lifecycle, CLI commands, and deployment live in [agents-cli](../../agents-cli/SKILL.md); [google-adk](../../google-adk/SKILL.md) owns SDK code. This section keeps the Python profile specifics.

- **Layout**: `app/agent.py` defines `root_agent` and its tools — plain typed functions whose signature and docstring become the JSON schema; business logic stays in modules the tools call.
- **Interpreter**: the pinned `agents-cli` 1.5.0 scaffold requires Python `>=3.11,<3.14`; pin Python 3.13 for this profile, independently of the dot CLI.
- **Normalize the scaffold**: keep the generator's Python range, replace its dummy unit test, remove blanket `[tool.ty.rules]` suppressions, and fix each diagnostic at the source.
- **Offline tests**: import `root_agent`, assert its wiring (name, model, tools), and call tool functions directly; the generated `tests/integration` hits the provider and is approval-gated.

ADK 2.8.0 currently emits an internal `BaseAgentConfig` deprecation warning on import; its generated GCP telemetry extras also resolve alpha packages. Treat these as upstream qualification gaps, keep them visible, and recheck the selected release before claiming a warning-free or entirely stable dependency graph.
