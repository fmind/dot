---
name: foundation
description: "Python package layout, dependency choices, uv/Ruff/ty tooling, and project scaffolding."
---

# Python Stack Standard

Shared Python packaging and `uv`/`ruff`/`ty` defaults; preserve existing project conventions and route specialist frameworks to their guides.

## Defaults

- **Interpreter & layout**: `mise` owns Python/ `.python-version` alignment ([tool-versions](../../../mise/references/tool-versions.md#workstation-and-projects)); `uv` owns `.venv` and `uv.lock`. Use `src/<package>/` (`dependencies = []` until earned); qualify min Python via `uv run --isolated --locked --python <min> pytest`.
- **Proven packages**: `pydantic`/`pydantic-settings`, `pyyaml` (`safe_load`), `httpx2` + `stamina` ([api-client](../api-client/GUIDE.md)), `structlog` + OTel ([observability](../observability.md)), Polars, `argparse` or Typer, and `sqlite3` (`PRAGMA foreign_keys=ON; journal_mode=WAL; busy_timeout=5000`).
- **Quality gate**: Ruff, `ty`, `deptry` (`known_first_party = ["<package>"]` on `uv_build` `src/` layouts, `extend_exclude` for non-`tests/` repo tasks, `per_rule_ignores` `DEP002` for CLI/URL/settings packages), `pytest` (`pytest-socket`, `pytest-timeout`, warnings as errors, 85% branch coverage), and `dprint` (`format:dprint`).
- **Docs, templates, migrations**: Zensical API docs (`mkdocstrings` + `api-autonav`, not `pdoc`); explicit Jinja escaping + `StrictUndefined`; rehearse Alembic/Django migrations on a backup copy.

## Workflow

1. **Select specialist & bootstrap**: follow [bootstrap](references/bootstrap.md) for new projects (Django and `agents-cli` keep native layouts); route web to [litestar](../../../python-web/references/litestar/GUIDE.md) (default), [django](../../../python-web/references/django/GUIDE.md), [fastapi](../../../python-web/references/fastapi.md), or [nicegui](../../../python-web/references/nicegui.md)/[gradio](../../../python-web/references/gradio.md); agents to [agent-frameworks](../../../agent-frameworks/SKILL.md); data/ML to [python-mlops](../../../python-mlops/SKILL.md)/[duckdb](../../../duckdb/SKILL.md); standalone scripts to [python-script](../python-script/GUIDE.md); tooling to [mise](../../../mise/SKILL.md), [lefthook](../../../github-actions/references/lefthook.md), [code-review](../../../code-security/references/code-review/GUIDE.md), [agent-project](../../../agent-project/SKILL.md), [upgrade-tools](../../../upgrade-tools/SKILL.md), [python-testing](../python-testing/GUIDE.md), [python-async](../python-async/GUIDE.md), [pydantic](../pydantic.md), [argparse](../argparse/GUIDE.md), [performance](../performance.md), and [scaffolding](../../../project-scaffolding/references/bootstrap.md).
1. **Verify before delivery**: run focused tests, full gates, and a fresh-venv wheel install + import/CLI smoke check outside the repo; finish with [repository-docs](../../../repository-docs/SKILL.md).

## Tooling & gotchas

### uv

- **Add, sync, & verify**: add via `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>` (sdist resolution still runs first; do not export globally), sync via `uv sync --locked`, check `uv lock --check`, commit `uv.lock`, and never pass bare `uv run`/`uv sync` in gates (`--locked` or `--frozen`).
- **Isolated wheel test & env**: export hashed deps (`uv export --locked --no-dev --no-emit-project -o requirements.txt` — skip when `dependencies = []`), `uv pip sync --require-hashes`, `uv pip install --no-deps <wheel>`. Inspect `.venv/` directly (`uv pip show`); unset `UV_*` (`UV_PROJECT`) on sibling repos instead of `--no-config`.
- **Triage `uv audit`**: upgrade first (`uv lock --upgrade-package <pkg>`); document upstream-unfixed CVEs in `[tool.uv.audit] ignore-until-fixed` with dated reason — never pass CLI `--ignore`.

### Ruff

- **Import order & Markdown**: run `uv run ruff check --select I --fix <paths>` before `ruff format` (which skips import sorting), and keep `extend-exclude = ["*.md"]` so `dprint` owns Markdown fences.
- **Suppressions & dead code**: require `# noqa: CODE` (`PGH004`/`RUF100`); check dead code via `vulture src --min-confidence 60 --ignore-decorators '@*_validator'` (`@*.command,@*.callback` on Typer/Click) and verify with `rg`.

### ty

- **Bounds, precedence, & suppressions**: pin `ty>=<latest>,<0.1`; standalone `ty.toml` overrides `[tool.ty]` and `[tool.ty.environment].python-version` overrides `requires-python`. Require `# ty: ignore[rule]` (`blanket-ignore-comment = "error"`, `unused-ignore-comment` errors; never `--exit-zero-on-warning` or `--add-ignore`).
- **Legacy baseline (`0.0.93+`)**: `[tool.ty] baseline = "ty-baseline.json"`, update once (`ty check --update-baseline`), and accept only entry-deleting diffs.

## Foundation resources & Docs

- Shared config: [pyproject.toml.template](templates/pyproject.toml.template), [mise.toml](templates/mise.toml), [lefthook.yml](templates/lefthook.yml), [AGENTS.md](templates/AGENTS.md.template), [gitignore](templates/gitignore), [ignore](templates/ignore).
- Library & docs starters: [init-library.py](templates/init-library.py), [test_library.py](templates/test_library.py), [zensical.toml](templates/zensical.toml), [docs-index.md](templates/docs-index.md).
- Upstream skills & docs: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) ([vendor-skills](../../../agent-project/references/vendor-skills.md)) · [Python](https://docs.python.org/3/) · [uv docs](https://docs.astral.sh/uv/) · [Ruff docs](https://docs.astral.sh/ruff/) · [ty docs](https://docs.astral.sh/ty/).
