---
name: foundation
description: "Configure Python package layout, PyPI metadata, uv/Ruff/ty tooling, workspaces, and project scaffolding."
---

# Python Stack Standard

Shared Python packaging and `uv`/`ruff`/`ty` defaults; keep existing conventions and route specialists to their guides.

## Defaults

- **Interpreter & layout**: `mise` owns Python/`.python-version` (`3.14` default; `3.15` for pure-Python packages; [tool-versions](../../../mise/references/tool-versions.md#workstation-and-projects)); `uv` owns `.venv` and `uv.lock`. Use `src/<package>/` (`dependencies = []` initially); qualify min Python via `uv run --isolated --locked --python <min> pytest` and published library floors via `uv run --isolated --resolution lowest-direct`.
- **Proven packages & gates**: `pydantic`, `pyyaml` (`safe_load`), `httpx2` + `stamina` ([api-client](../api-client/GUIDE.md)), `structlog` + OTel ([observability](../observability.md), [telemetry.py](templates/telemetry.py)), Polars, `argparse`/Cyclopts, and `sqlite3` (`WAL` + `busy_timeout=5000`). Gates: Ruff, `ty`, `deptry`, `pytest` (`pytest-socket`, `pytest-timeout`, warnings as errors, 85% branch coverage), `jactionlint`, and `dprint` (`format:dprint`; see [pyproject.toml.template](templates/pyproject.toml.template)).
- **Docs, templates, migrations**: opt-in Zensical API docs (`mkdocstrings-python` + `api-autonav`, not `pdoc`); Jinja `autoescape=True` + `StrictUndefined`; rehearse Alembic/Django migrations on a backup copy.

## Workflow

1. **Select specialist & bootstrap**: follow [bootstrap](references/bootstrap.md) for new packages (Django and `agents-cli` keep native layouts); route specialists via [python](../../SKILL.md), [mlops](../../../mlops/SKILL.md), or [agent-frameworks](../../../agent-frameworks/SKILL.md).
1. **Verify before delivery**: run focused tests, full gates, and a fresh-venv wheel install + import/CLI smoke check outside the repo; finish with [docs/repository](../../../docs/references/repository/GUIDE.md) and [PyPI publishing](references/pypi.md) when releasing.

## Tooling & gotchas

### uv

- **Add, sync, & verify**: add via `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>` (do not export globally), sync via `uv sync --locked`, check `uv lock --check`, commit `uv.lock`, and never pass bare `uv run`/`uv sync` in gates (`--locked` or `--frozen`).
- **Isolated wheel test & env**: inspect `.venv/` directly (`uv pip show`); unset `UV_*` (`UV_PROJECT`) on sibling repos instead of `--no-config`. See [PyPI publishing](references/pypi.md) for hashed `uv export` + isolated wheel checks.
- **Triage `uv audit`**: upgrade first (`uv lock --upgrade-package <pkg>`); record upstream-unfixed CVEs in `[tool.uv.audit] ignore-until-fixed` with dated reason—never CLI `--ignore`.
- **Workspaces & private indexes**: share one root `uv.lock` across `[tool.uv.workspace]` members (`workspace = true` in `[tool.uv.sources]`, scoping commands with `--package <member>` and running `deptry`/`ty` per member). Declare internal registries via `[[tool.uv.index]]` + `keyring-provider = "subprocess"` (Artifact Registry / GitHub Packages), never embedding tokens in `pyproject.toml`.

### Ruff

- **Import order & Markdown**: run `uv run ruff check --select I --fix <paths>` before `ruff format`; keep `extend-exclude = ["*.md"]` so `dprint` owns Markdown fences.
- **Suppressions & dead code**: require `# noqa: CODE` (`PGH004`/`RUF100`); check dead code via `uvx vulture src tests --min-confidence 60 --exclude '*/.venv/*' --ignore-decorators '@*_validator,@*.command,@*.callback'` and verify with `rg`.

### ty

- **Bounds, precedence, & suppressions**: pin `ty>=<latest>,<0.1`; `ty.toml` overrides `[tool.ty]` and `[tool.ty.environment].python-version` overrides `requires-python`. Require `# ty: ignore[rule]` (`blanket-ignore-comment = "error"`, `unused-ignore-comment` errors; never `--exit-zero-on-warning` or `--add-ignore`).
- **Legacy baseline (`0.0.93+`)**: `[tool.ty] baseline = "ty-baseline.json"`, update once (`ty check --update-baseline`), and accept only entry-deleting diffs.

## Documentation

- Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) ([vendor-skills](../../../agent-harnesses/references/vendor-skills.md)) · [Python](https://docs.python.org/3/) · [uv](https://docs.astral.sh/uv/) ([releases](https://github.com/astral-sh/uv/releases)) · [Ruff](https://docs.astral.sh/ruff/) ([releases](https://github.com/astral-sh/ruff/releases)) · [ty](https://docs.astral.sh/ty/) ([releases](https://github.com/astral-sh/ty/releases)) · Companions: [language](../language.md), [testing](../testing/GUIDE.md).
