---
name: python-stack
description: Define shared Python project defaults and scaffold a minimal typed package. Use when choosing or aligning a Python stack, layout, or quality baseline.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-09-11"
---

# Python Stack Standard

Own the shared Python foundation and select the specialist for the task. Preserve existing project conventions. Load only the relevant owner; specialist skills can use these defaults without restarting the bootstrap workflow.

## Defaults

- **Toolchain**: stable Python managed by uv; commit `uv.lock`, align `.python-version` with `requires-python`, and check a library's minimum interpreter with `uv run --isolated --python <min> pytest` (`--isolated` leaves the project `.venv` untouched).
- **Foundation**: a `src/<package>/` layout and no runtime dependencies until the application uses them. Distribution slugs may contain hyphens; import names use underscores.
- **Quality**: Ruff for Python formatting/lint, ty for types, pytest for behavior, and dprint for markup/config. Keep checks warning-free; use deterministic offline tests and an initial 85% branch-coverage target adapted to the project.
- **Boundaries**: use Pydantic/settings when external input or application configuration needs typed validation, and structlog when structured logging is required. Respect ecosystem-native formats; otherwise use YAML for human-maintained configuration and JSON for program-owned data, with explicit defaults and override precedence.

For application templates, set output-appropriate escaping explicitly and prefer `StrictUndefined` in new Jinja templates when missing data is an error; review compatibility before changing existing undefined behavior. Template generation and tracked updates use [cookiecutter](../cookiecutter/SKILL.md).

## Workflow

1. **Choose the owner** from [profiles](references/profiles.md) and the table below. For an existing application's feature or diagnostic, go directly to its specialist.
1. **Create the foundation only when needed** using [bootstrap](references/bootstrap.md), the shared manifest and tasks below, and the minimal library example. Add the selected specialist's scaffold before final qualification; generated agent and Django projects retain their native layouts.
1. **Verify the result** through focused behavior tests and the project's canonical gate. Build a new package, install its wheel in a fresh environment, and exercise its public import or command outside the source tree; an editable install alone does not qualify packaging.
1. **Finish** through [repository-docs](../repository-docs/SKILL.md). [new-project](../new-project/SKILL.md) owns repository-wide setup, CI, licensing, and authorized publication.

## Task owners

| Need                                                | Owner                                                                                                                                                                                                                                               |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dependencies, environments, Python versions, builds | [uv](../uv/SKILL.md)                                                                                                                                                                                                                                |
| Python lint/format or type diagnostics              | [ruff](../ruff/SKILL.md), [ty](../ty/SKILL.md)                                                                                                                                                                                                      |
| Task definitions, hooks, markup/config formatting   | [mise](../mise/SKILL.md), [lefthook](../lefthook/SKILL.md), [dprint](../dprint/SKILL.md)                                                                                                                                                            |
| CLI scaffold and command behavior                   | [typer](../typer/SKILL.md), [cli-contracts](../cli-contracts/SKILL.md)                                                                                                                                                                              |
| Web application                                     | [django](../django/SKILL.md) for ORM, admin, auth, and server-rendered pages; [litestar](../litestar/SKILL.md) for typed ASGI APIs and services; [fastapi](../fastapi/SKILL.md) for an existing or generated scaffold                               |
| Async tasks, cancellation, deadlines, shutdown      | [python-async](../python-async/SKILL.md)                                                                                                                                                                                                            |
| Persisted schema or data changes                    | [data-migration](../data-migration/SKILL.md), including Alembic; use installed database/framework documentation for query APIs.                                                                                                                     |
| Agent, LLM, and MCP application code                | [agents-cli](../agents-cli/SKILL.md) and [google-adk](../google-adk/SKILL.md) for Google agents; [langchain](../langchain/SKILL.md) or [langgraph](../langgraph/SKILL.md) for framework code; [mcp-server](../mcp-server/SKILL.md) for tool servers |
| Single-file utility or reactive notebook            | [python-script](../python-script/SKILL.md), [marimo](../marimo/SKILL.md)                                                                                                                                                                            |
| Local data queries and exports                      | [duckdb](../duckdb/SKILL.md); use the project's dataframe and plotting libraries through their installed source and official docs.                                                                                                                  |
| Input validation, logging, external HTTP            | [pydantic](../pydantic/SKILL.md), [observability](../observability/SKILL.md), [api-client](../api-client/SKILL.md)                                                                                                                                  |
| Python tests and Hypothesis integration             | [test-driven-development](../test-driven-development/SKILL.md), including pytest mechanics and property-testing references.                                                                                                                         |
| Broader test campaigns                              | [quality-assurance](../quality-assurance/SKILL.md)                                                                                                                                                                                                  |
| CPU and allocation profiling                        | [systematic-debugging](../systematic-debugging/SKILL.md), including its Python profiler recipes.                                                                                                                                                    |
| Security scans and dependency upgrades              | [secure](../secure/SKILL.md), [upgrade-tools](../upgrade-tools/SKILL.md)                                                                                                                                                                            |

## Foundation resources

- [pyproject.toml.template](references/pyproject.toml.template), [mise.toml](references/mise.toml), and [lefthook.yml](references/lefthook.yml) define the shared baseline; their version constraints are a floor, not a latest-release claim, so preserve a project's supported range and lock policy.
- [AGENTS.md](references/AGENTS.md) and [gitignore](references/gitignore) supply project conventions.
- [init-library.py](references/init-library.py) and [test_library.py](references/test_library.py) supply the minimal library example; application code and tests live with the selected specialist.

## Documentation

- [Python](https://docs.python.org/3/) · [Python packaging](https://packaging.python.org/)
- [agent-project](../agent-project/SKILL.md) owns vendor skill discovery and the dated official-source audit; selecting a stack does not install every vendor bundle.
