# Python Project Profiles

## 3. Project Profiles

- **CLI**: a Typer app in `__init__.py` ([init-cli.py](references/init-cli.py)) exposed through `[project.scripts]`; flags, streams, and exit codes follow [cli-contracts](../cli-contracts/SKILL.md).
- **Library**: no runtime dependencies by default; omit `__main__.py` and `[project.scripts]`.
- **Data, ML, notebooks**: extension profiles on the library profile — `uv add` only the workload boundary (Polars or DuckDB, scikit-learn or a hardware-specific PyTorch/JAX, JupyterLab or Marimo) in a dependency group.
- **Scripts**: single-file tools with PEP 723 metadata go through [python-script](../python-script/SKILL.md).

## 4. Web Stack (Litestar)

- **Framework and data**: Litestar with `asyncpg` + SQLAlchemy 2 async sessions injected through `Provide`; Alembic migrations (`uv run alembic init --template async alembic`, `postgresql+asyncpg` URL).
- **Health**: `/health` is dependency-free liveness; `/ready` runs `SELECT 1` and returns 503 on `SQLAlchemyError`.
- **HTTP client**: `httpx.AsyncClient`.
- **Static assets**: self-hosted under `/static/` with SHA-256 cache busting and long-lived cache headers; no CDNs.
- **Server**: `granian` with `uvloop`, passing `Interfaces.ASGI` (the enum, so `ty` stays clean).
- **Cloud logging**: `structlog` JSON with GCP keys (`severity`, `time`, `message`, `stack_trace`), `x-cloud-trace-context` correlation, silent `/health`.

## 5. ADK Agents (Python API)

The agent workflow, `agents-cli` commands, model-pin rationale, and deployment live in [google-adk](../google-adk/SKILL.md); this section keeps the Python specifics.

- **Layout**: `app/agent.py` defines `root_agent` and its tools — plain typed functions whose signature and docstring become the JSON schema; business logic stays in modules the tools call.
- **Normalize the scaffold**: keep the generator's Python range, replace its dummy unit test, remove blanket `[tool.ty.rules]` suppressions, and fix each diagnostic at the source.
- **Offline tests**: import `root_agent`, assert its wiring (name, model, tools), and call tool functions directly; the generated `tests/integration` hits the provider and is approval-gated.
