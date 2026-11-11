---
name: foundation
description: "Python package layout, dependency choices, defaults, and project scaffolding."
---

# Python Stack Standard

Own the shared Python foundation and route to the right specialist while preserving existing project conventions.

## Defaults

- **Interpreter & env**: `mise` owns Python, `.python-version`, and `requires-python` alignment ([tool-versions](../../../mise/references/tool-versions.md#workstation-and-projects)); `uv` owns `.venv` and `uv.lock`. Test minimum Python bounds via `uv run --isolated --locked --python <min> pytest`.
- **Layout**: `src/<package>/` with `dependencies = []` until earned (hyphenated distribution slugs, underscored import names).
- **Stdlib for plumbing, proven packages at boundaries**: use `argparse`, `pathlib`, `tomllib`, `json`, `sqlite3`, `datetime`/`zoneinfo`, `logging`, `asyncio`, `concurrent.futures`, `dataclasses`, `subprocess`, `tempfile`, `hashlib`, `secrets`, and `urllib.request` (single simple requests without auth/redirect hazards). Use `pydantic`/`pydantic-settings` for validation/settings, `pyyaml` (`safe_load`) for YAML, `httpx2` (`httpx` if already locked) + `stamina` for HTTP/retries, `structlog` + OpenTelemetry for telemetry, Polars for dataframes, and the chosen web/agent/ML framework.
- **Quality gate**: Ruff (format/lint), `ty` (types), `deptry` (`known_first_party = ["<package>"]` on `uv_build` `src/` layouts, `extend_exclude` for tests or repo-only task packages outside top-level `tests/`, and `per_rule_ignores` `DEP002` for URL/CLI/settings-only packages), `pytest` (`pytest-socket` offline default, `pytest-timeout`, warnings as errors, 85% initial branch coverage; `mise run report:coverage` inspects the last run), and `dprint` (markup/config).
- **Docs & templates**: `build:docs` generates API docs via Zensical (`mkdocstrings` + `api-autonav`, never `pdoc`; [documentation-site](../../../documentation-site/SKILL.md)). Set explicit template escaping + `StrictUndefined` on new Jinja templates. [project-scaffolding](../../../project-scaffolding/SKILL.md) owns Copier and Cookiecutter/Cruft templates.

## Workflow

1. **Select the owner** from [profiles and owners](#profiles-and-owners) (go straight to the specialist for existing apps).
1. **Bootstrap when new** via [bootstrap](references/bootstrap.md) + the specialist profile before final qualification (Django and `agents-cli` keep their native layouts).
1. **Verify** with focused tests, the project gate, and a fresh-venv wheel install + import/CLI check outside the source tree.
1. **Finish** via [repository-docs](../../../repository-docs/SKILL.md) and [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).

## Profiles and owners

- **Library**: shared foundation, zero runtime deps, no `[project.scripts]`.
- **CLI**: foundation + [argparse](../argparse/GUIDE.md) (zero runtime deps) + [cli-contracts](../cli-contracts.md).
- **Web**: [litestar](../../../python-web/references/litestar/GUIDE.md) (typed ASGI default), [django](../../../python-web/references/django/GUIDE.md) (ORM/admin/auth/SSR), [fastapi](../../../python-web/references/fastapi.md) (existing/`agents-cli` scaffolds), [nicegui](../../../python-web/references/nicegui.md) / [gradio](../../../python-web/references/gradio.md) (Python UIs/demos).
- **Agent, LLM, MCP**: Google ADK first via [agents-cli](../../../agent-frameworks/references/agents-cli/GUIDE.md) + [google-adk](../../../agent-frameworks/references/google-adk.md); else [langgraph](../../../agent-frameworks/references/langgraph.md) / [langchain](../../../agent-frameworks/references/langchain.md) ([agent-frameworks](../../../agent-frameworks/SKILL.md)); tool servers via [MCP](../../../agent-protocols/references/mcp/GUIDE.md).
- **Data, ML, notebooks**: [polars](../../../python-mlops/references/polars.md), [python-mlops](../../../python-mlops/SKILL.md), [duckdb](../../../duckdb/SKILL.md), [marimo](../../../python-mlops/references/marimo.md).
- **Single-file script**: [python-script](../python-script/GUIDE.md) (PEP 723).

I/O-bound agent/LLM/MCP/web profiles default to `asyncio` ([python-async](../python-async/GUIDE.md)). Cross-cutting owners: [uv](../uv.md), [ruff](../ruff.md), [ty](../ty.md), [pydantic](../pydantic.md), [mise](../../../mise/SKILL.md), [lefthook](../../../github-actions/references/lefthook.md), [dprint](../../../mise/references/dprint.md), [observability](../observability.md), [api-client](../api-client/GUIDE.md), [python-testing](../python-testing/GUIDE.md), [performance](../performance.md), [code-security](../../../code-security/references/code-review/GUIDE.md), [upgrade-tools](../../../upgrade-tools/SKILL.md), and [agent-project](../../../agent-project/SKILL.md) (vendor skills). Rehearse DB migrations (Alembic, Django) on a copy with a restorable backup.

## Foundation resources & Docs

- Shared config: [pyproject.toml.template](templates/pyproject.toml.template), [mise.toml](templates/mise.toml), [lefthook.yml](templates/lefthook.yml), [AGENTS.md](templates/AGENTS.md.template), [gitignore](templates/gitignore), [ignore](templates/ignore).
- Library & docs starters: [init-library.py](templates/init-library.py), [test_library.py](templates/test_library.py), [zensical.toml](templates/zensical.toml), [docs-index.md](templates/docs-index.md).
- Docs: [Python](https://docs.python.org/3/) · [Packaging](https://packaging.python.org/) · [Supported versions](https://devguide.python.org/versions/) · [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html).
