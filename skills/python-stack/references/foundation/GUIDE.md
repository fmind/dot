---
name: foundation
description: "Python package layout, dependency choices, uv/Ruff/ty tooling, and project scaffolding."
---

# Python Stack Standard

Own the shared Python foundation and `uv`/`ruff`/`ty` defaults, routing application work to the matching specialist while preserving existing project conventions.

## Defaults

- **Interpreter & env**: `mise` owns Python, `.python-version`, and `requires-python` alignment ([tool-versions](../../../mise/references/tool-versions.md#workstation-and-projects)); `uv` owns `.venv` and `uv.lock`. Test minimum Python bounds via `uv run --isolated --locked --python <min> pytest`.
- **Layout**: `src/<package>/` with `dependencies = []` until earned (hyphenated distribution slugs, underscored import names).
- **Stdlib for plumbing, proven packages at boundaries**: use `argparse`, `pathlib`, `tomllib`, `json`, `sqlite3` (enable `PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000` per connection), `datetime`/`zoneinfo`, `logging`, `asyncio`, `concurrent.futures`, `dataclasses`, `subprocess`, `tempfile`, `hashlib`, `secrets`, and `urllib.request` (single simple requests without auth/redirect hazards). Use `pydantic`/`pydantic-settings` for validation/settings, `pyyaml` (`safe_load`) for YAML, `httpx2` (`httpx` if already locked) + `stamina` for HTTP/retries, `structlog` + OpenTelemetry for telemetry, Polars for dataframes, and the chosen web/agent/ML framework.
- **Quality gate**: Ruff (format/lint), `ty` (types), `deptry` (`known_first_party = ["<package>"]` on `uv_build` `src/` layouts, `extend_exclude` for tests or repo-only task packages outside top-level `tests/`, and `per_rule_ignores` `DEP002` for URL/CLI/settings-only packages), `pytest` (`pytest-socket` offline default, `pytest-timeout`, warnings as errors, 85% initial branch coverage; `mise run report:coverage` inspects the last run), and `dprint` (markup/config).
- **Docs & templates**: `build:docs` generates API docs via Zensical (`mkdocstrings` + `api-autonav`, never `pdoc`; [documentation-site](../../../documentation-site/SKILL.md)). Set explicit template escaping + `StrictUndefined` on new Jinja templates. [project-scaffolding](../../../project-scaffolding/SKILL.md) owns Copier and Cookiecutter/Cruft templates.

## Workflow

1. **Select the owner** from [profiles and owners](#profiles-and-owners) (go straight to the specialist for existing apps).
1. **Bootstrap when new** via [bootstrap](references/bootstrap.md) + the specialist profile before final qualification (Django and `agents-cli` keep their native layouts).
1. **Verify** with focused tests, the project gate, and a fresh-venv wheel install + import/CLI check outside the source tree.
1. **Finish** via [repository-docs](../../../repository-docs/SKILL.md) and [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).

## Profiles and owners

- **Library**: shared foundation, zero runtime deps, no `[project.scripts]`.
- **CLI**: foundation + [argparse](../argparse/GUIDE.md) (zero runtime deps).
- **Web**: [litestar](../../../python-web/references/litestar/GUIDE.md) (typed ASGI default), [django](../../../python-web/references/django/GUIDE.md) (ORM/admin/auth/SSR), [fastapi](../../../python-web/references/fastapi.md) (existing/`agents-cli` scaffolds), [nicegui](../../../python-web/references/nicegui.md) / [gradio](../../../python-web/references/gradio.md) (Python UIs/demos).
- **Agent, LLM, MCP**: Google ADK first via [agents-cli](../../../agent-frameworks/references/agents-cli/GUIDE.md) + [google-adk](../../../agent-frameworks/references/google-adk.md); else [langgraph](../../../agent-frameworks/references/langgraph.md) / [langchain](../../../agent-frameworks/references/langchain.md) ([agent-frameworks](../../../agent-frameworks/SKILL.md)); tool servers via [MCP](../../../agent-protocols/references/mcp/GUIDE.md).
- **Data, ML, notebooks**: [polars](../../../python-mlops/references/polars.md), [python-mlops](../../../python-mlops/SKILL.md), [duckdb](../../../duckdb/SKILL.md), [marimo](../../../python-mlops/references/marimo.md).
- **Single-file script**: [python-script](../python-script/GUIDE.md) (PEP 723).

I/O-bound agent/LLM/MCP/web profiles default to `asyncio` ([python-async](../python-async/GUIDE.md)). Cross-cutting owners: [pydantic](../pydantic.md), [mise](../../../mise/SKILL.md), [lefthook](../../../github-actions/references/lefthook.md), [dprint](../../../mise/references/dprint.md), [observability](../observability.md), [api-client](../api-client/GUIDE.md), [python-testing](../python-testing/GUIDE.md), [performance](../performance.md), [code-security](../../../code-security/references/code-review/GUIDE.md), [upgrade-tools](../../../upgrade-tools/SKILL.md), and [agent-project](../../../agent-project/SKILL.md) (vendor skills). Rehearse DB migrations (Alembic, Django) on a copy with a restorable backup.

## Tooling & gotchas

### uv

- **Add, sync, & lock**: add packages via `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>` (blocks published OSV malware advisories pre-install, though sdist resolution runs first; do not export globally), sync via `uv sync --locked`, and verify with `uv lock --check`. Commit `uv.lock` (libraries included), bound `uv_build` within `uv`'s [backend contract](https://docs.astral.sh/uv/concepts/build-backend/), and never run bare `uv run` or `uv sync` in gates (use `--locked` or `--frozen`).
- **Wheel qualification & env isolation**: export hashed deps (`uv export --locked --no-dev --no-emit-project -o requirements.txt` — skip when `dependencies = []`, as `uv` warns on empty files), then `uv venv`, `uv pip sync --require-hashes requirements.txt`, and `uv pip install --no-deps <wheel>` (clean temp venvs/exports in `finally`, keep project `.venv`). Inspect packages via `uv pip show <dist>` and `.venv/` reads rather than importing; unset inherited `UV_*` (`UV_PROJECT`) when testing nested/separate repos instead of `--no-config` (which drops `[tool.uv]`; misspelled `[tool.uv]` keys only warn).
- **Triage `uv audit`**: upgrade first (`uv lock --upgrade-package <pkg>`); if unfixed upstream, record in `[tool.uv.audit] ignore-until-fixed` with a dated reason (or `ignore` only when proven non-applicable, per [audit settings](https://docs.astral.sh/uv/reference/settings/#audit)) — never pass CLI `--ignore` or drop `check:vuln`.

### Ruff

- **Order & Markdown**: run `uv run ruff check --select I --fix <paths>` before `uv run ruff format <paths>` (`ruff format` never reorders imports), scoped to owned paths; inspect any `--unsafe-fixes` manually. Exclude `*.md` (`extend-exclude = ["*.md"]` or `.py` paths) where `dprint` owns Markdown (`ruff format` rewrites Markdown Python fences).
- **Suppressions & dead code**: use narrow `# noqa: CODE` only (`PGH004` rejects bare `# noqa`, `RUF100` flags stale ones; never `--add-noqa`/`--add-ignore`). Sweep dead code in reviews via `vulture src --min-confidence 60 --ignore-decorators '@*_validator'` (`@*.command,@*.callback` on Typer/Click) and verify hits with `rg`.

### ty

- **Bounds, precedence, & suppressions**: pin pre-1.0 range `ty>=<latest>,<0.1`; on `unresolved-import`, check Python version, `.venv`, `src/` roots, and PEP 561 stubs first (`[tool.ty.environment].python-version` > `requires-python`; standalone `ty.toml` overrides `[tool.ty]`). Use rule-scoped `# ty: ignore[rule-name]` only (`blanket-ignore-comment = "error"` rejects bare `# type: ignore`, mypy codes do nothing, and `unused-ignore-comment` fails `ty check` — never pass `--exit-zero-on-warning` or `--add-ignore`).
- **Legacy baseline (`0.0.93+`)**: set `[tool.ty] baseline = "ty-baseline.json"`, run `ty check --update-baseline` once, and commit (entries match column spans, so rerun after fixes and accept only entry-deleting diffs).

## Foundation resources & Docs

- Shared config: [pyproject.toml.template](templates/pyproject.toml.template), [mise.toml](templates/mise.toml), [lefthook.yml](templates/lefthook.yml), [AGENTS.md](templates/AGENTS.md.template), [gitignore](templates/gitignore), [ignore](templates/ignore).
- Library & docs starters: [init-library.py](templates/init-library.py), [test_library.py](templates/test_library.py), [zensical.toml](templates/zensical.toml), [docs-index.md](templates/docs-index.md).
- Upstream skills & docs: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) (`uv`, `ruff`, `ty`, per [vendor-skills](../../../agent-project/references/vendor-skills.md)) · [Python](https://docs.python.org/3/) · [Packaging](https://packaging.python.org/) · [uv docs](https://docs.astral.sh/uv/) · [Ruff docs](https://docs.astral.sh/ruff/) · [ty docs](https://docs.astral.sh/ty/).
