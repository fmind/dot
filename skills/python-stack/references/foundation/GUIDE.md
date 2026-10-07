---
name: foundation
description: "Python package layout, dependency choices, defaults, and project scaffolding."
---

# Python Stack Standard

Own the shared Python foundation and select the specialist for the task. Preserve existing project conventions. Load only the relevant owner; specialist skills can use these defaults without restarting the bootstrap workflow.

## Defaults

- **Pin Python through mise**: mise owns the interpreter per the [tool version rules](../../../mise/references/tool-versions.md); uv owns package environments and `uv.lock`. Projects pin Python exactly like other tools and upgrade it on their own schedule. Align `.python-version` with the selected pin within `requires-python`; check a library's minimum interpreter with `uv run --isolated --python <min> pytest` (`--isolated` leaves the project `.venv` untouched).
- **Start minimal with a `src/` layout**: a `src/<package>/` layout and no runtime dependencies until the application uses them. Distribution slugs may contain hyphens; import names use underscores.
- **Use Ruff, ty, deptry, pytest, and dprint**: Ruff for Python formatting/lint, ty for types, deptry for dependency declarations (missing, unused, transitive, or dev-only imports in shipped code; it treats test code outside a top-level `tests/` as shipped, so extend `[tool.deptry] extend_exclude`, and list packages loaded only by URL, command, or settings string under `per_rule_ignores` `DEP002`), pytest for behavior, and dprint for markup/config. Keep checks warning-free; use deterministic offline tests and an initial 85% branch-coverage target adapted to the project. The task template keeps test counts and coverage totals visible; `mise run report:coverage` reads per-file detail from the last run without rerunning tests. Rerun tests when saved coverage is stale.
- **Document APIs with Zensical**: the starter's `build:docs` renders an API reference from docstrings through mkdocstrings and `api-autonav`, never pdoc; [documentation-site](../../../documentation-site/SKILL.md) grows it into a full site.
- **Validate external input with Pydantic**: use Pydantic/settings when external input or application configuration needs typed validation, and structlog when structured logging is required. Respect ecosystem-native formats; otherwise use YAML for human-maintained configuration and JSON for program-owned data, with explicit defaults and override precedence.

For application templates, set output-appropriate escaping explicitly and prefer `StrictUndefined` in new Jinja templates when missing data is an error; review compatibility before changing existing undefined behavior. [Project-scaffolding](../../../project-scaffolding/SKILL.md) owns project templates and tracked updates: Copier for new templates, with existing Cookiecutter/Cruft workflows preserved.

## Workflow

1. **Choose the owner** from [profiles and owners](#profiles-and-owners). For an existing application's feature or diagnostic, go directly to its specialist.
1. **Create the foundation only when needed** using [bootstrap](references/bootstrap.md), the shared manifest and tasks below, and the minimal library example. Add the selected specialist's scaffold before final qualification; generated agent and Django projects retain their native layouts.
1. **Verify the result** through focused behavior tests and the project's canonical gate. Build a new package, install its wheel in a fresh environment, and exercise its public import or command outside the source tree; an editable install alone does not qualify packaging.
1. **Finish** through [repository-docs](../../../repository-docs/SKILL.md). [project-scaffolding](../../../project-scaffolding/references/bootstrap.md) owns repository-wide setup, CI, licensing, and authorized publication.

## Profiles and owners

Choose the smallest profile that fits the project; its owner supplies application procedures and examples.

- **Library**: the shared package foundation, no runtime dependencies by default, and no console entry point.
- **CLI**: extend the foundation through [typer](../../../cli-development/references/typer/GUIDE.md); [cli-contracts](../../../cli-development/references/cli-contracts.md) owns flags, streams, and exit codes.
- **Web**: [litestar](../../../python-web/references/litestar/GUIDE.md) extends the foundation for typed ASGI APIs and services; [django](../../../python-web/references/django/GUIDE.md) owns ORM, admin, auth, and server-rendered pages through its own bootstrap; [fastapi](../../../python-web/references/fastapi.md) covers an existing or generated scaffold. Use [nicegui](../../../python-web/references/nicegui.md) or [gradio](../../../python-web/references/gradio.md) for a single-user tool or model demo instead of a service.
- **Agent, LLM, MCP**: for Google agents, start with [agents-cli](../../../agent-frameworks/references/agents-cli/GUIDE.md) and use [google-adk](../../../agent-frameworks/references/google-adk.md) for SDK code, retaining the generator's layout and supported Python range; [langchain](../../../agent-frameworks/references/langchain.md) or [langgraph](../../../agent-frameworks/references/langgraph.md) for framework code; [MCP implementation](../../../agent-protocols/references/mcp/GUIDE.md) for tool servers.
- **Data, ML, notebooks**: [polars](../../../python-mlops/references/polars.md) for dataframes; [python-mlops](../../../python-mlops/SKILL.md) for training, experiments, registry, model delivery, and monitoring; [duckdb](../../../duckdb/SKILL.md) for local queries and exports; [marimo](../../../python-mlops/references/marimo.md) for reactive notebooks. Retain project-selected workload dependencies, keep runtime dependencies separate from development tools, and consult installed source and official docs for dataframe, schema, and chart APIs.
- **Single-file utility**: [python-script](../python-script/GUIDE.md) for PEP 723 metadata and execution.

Default to synchronous code. Choose async only for I/O-bound concurrency — many simultaneous network calls, streaming responses, or long-lived connections — and keep CPU-bound work, blocking drivers, and scripts synchronous; [python-async](../python-async/GUIDE.md) owns task lifetime, cancellation, deadlines, and shutdown once async is chosen.

Cross-cutting owners:

- **This skill**: [uv](../uv.md) for dependencies, environments, Python versions, and builds; [ruff](../ruff.md) and [ty](../ty.md) for lint/format and type diagnostics; [pydantic](../pydantic.md) for input validation.
- **Tasks, hooks, markup/config formatting**: [mise](../../../mise/SKILL.md), [lefthook](../../../github-actions/references/lefthook.md), [dprint](../../../dprint/SKILL.md).
- **Persisted schema or data changes**: [data-migration](../../../data-migration/SKILL.md), including Alembic; use installed database/framework documentation for query APIs.
- **Logging and external HTTP**: [observability](../../../observability/SKILL.md), [api-client](../../../api-client/SKILL.md).
- **Tests**: [python-testing](../../../python-testing/SKILL.md) for pytest mechanics and Hypothesis property tests; [quality-assurance](../../../quality-assurance/SKILL.md) for broader campaigns.
- **CPU and allocation profiling**: [systematic-debugging](../../../systematic-debugging/SKILL.md), including its Python profiler recipes.
- **Security scans and dependency upgrades**: [code-security](../../../code-security/references/code-review/GUIDE.md), [upgrade-tools](../../../upgrade-tools/SKILL.md).

## Foundation resources

- [pyproject.toml.template](templates/pyproject.toml.template), [mise.toml](templates/mise.toml), and [lefthook.yml](templates/lefthook.yml) define the shared foundation. Preserve supported package ranges; resolve scaffold tool selectors to exact baseline pins before installation.
- [AGENTS.md](templates/AGENTS.md), [gitignore](templates/gitignore), and [ignore](templates/ignore) supply project conventions.
- [init-library.py](templates/init-library.py) and [test_library.py](templates/test_library.py) supply the minimal library example; application code and tests live with the selected specialist.

## Documentation

- [Python](https://docs.python.org/3/) · [Python packaging](https://packaging.python.org/)
- [agent-project](../../../agent-project/SKILL.md) owns vendor skill discovery and the dated official-source audit; selecting a stack does not install every vendor bundle.
- Releases: [Python versions](https://devguide.python.org/versions/) · [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html)
