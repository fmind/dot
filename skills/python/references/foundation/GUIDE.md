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

- **Add, sync, & lock**: add via `UV_MALWARE_CHECK=1 uv add --preview-features malware-check <pkg>` (never export globally), sync via `uv sync --locked`, check `uv lock --check`, commit `uv.lock`, and enforce `--locked` + pinned CI tools (`UV_LOCKED: "1"`, no bare `uvx`) per [ci-cd](../../../github/references/ci-cd/GUIDE.md#principles).
- **Supply-chain hardening (opt-in)**: on wheel-only projects set `[tool.uv] no-build = true` (`no-binary-package = ["<pkg>"]` allowlist) to block sdist build-backend execution; on team/production repos outside personal `0d` defaults set `[tool.uv] exclude-newer = "3d"` (`exclude-newer-package = { "<pkg>" = false }` or ISO date override) to buffer fresh releases ahead of malware reports.
- **Wheel check, audit, & workspaces**: inspect `.venv/` (`uv pip show`); unset `UV_*` (`UV_PROJECT`) on sibling repos instead of `--no-config`; see [PyPI publishing](references/pypi.md) for hashed `uv export` wheel checks. Triage `uv audit` by upgrading first (`uv lock --upgrade-package <pkg>`) or recording dated `[tool.uv.audit] ignore-until-fixed` (never CLI `--ignore`). Share one root `uv.lock` across `[tool.uv.workspace]` members (`workspace = true` in `[tool.uv.sources]`, `--package <member>`, per-member `deptry`/`ty`); declare internal registries via `[[tool.uv.index]]` + `keyring-provider = "subprocess"`, never tokens in `pyproject.toml`.

### Ruff

- **Import order & Markdown**: run `uv run ruff check --select I --fix <paths>` before `ruff format`; keep `extend-exclude = ["*.md"]` so `dprint` owns Markdown fences.
- **Suppressions & dead code**: require `# noqa: CODE` (`PGH004`/`RUF100`); check dead code via `uvx vulture src tests --min-confidence 60 --exclude '*/.venv/*' --ignore-decorators '@*_validator,@*.command,@*.callback'` and verify with `rg`.

### ty

- **Bounds, precedence, & suppressions**: pin `ty>=<latest>,<0.1`; `ty.toml` overrides `[tool.ty]` and `[tool.ty.environment].python-version` overrides `requires-python`. Require `# ty: ignore[rule]` (`blanket-ignore-comment = "error"`, `unused-ignore-comment` errors; never `--exit-zero-on-warning` or `--add-ignore`).
- **Legacy baseline (`0.0.93+`)**: `[tool.ty] baseline = "ty-baseline.json"`, update once (`ty check --update-baseline`), and accept only entry-deleting diffs.

### Architecture & structural gates (opt-in)

Prefer mechanical rules over `AGENTS.md` prose once layers or recurring invariants grow:

- **Module boundaries (`import-linter`)**: add `--dev import-linter` with `UV_MALWARE_CHECK=1 --preview-features malware-check`, configure `[tool.importlinter]` (`root_package`) + `[[tool.importlinter.contracts]]` (`layers`/`forbidden`/`acyclic_siblings`), and wire `uv run --locked lint-imports --no-logo` into `check:local` (prefer over unmaintained `tach`).
- **Custom AST invariants (`ast-grep`)**: pin `ast-grep` in `mise.toml` (re-lock), add `sgconfig.yml` (`ruleDirs: [.ast-grep/rules]`, `testDirs: [.ast-grep/tests]`) with `severity: error` rules and remediation `message:`, wire `ast-grep scan` into `check:local`, run `ast-grep test`, and keep `--custom-languages` at `ignore`.

## Documentation

- Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) ([vendor-skills](../../../agent-harnesses/references/vendor-skills.md)) · [Python](https://docs.python.org/3/) · [uv](https://docs.astral.sh/uv/) ([releases](https://github.com/astral-sh/uv/releases)) · [Ruff](https://docs.astral.sh/ruff/) ([releases](https://github.com/astral-sh/ruff/releases)) · [ty](https://docs.astral.sh/ty/) ([releases](https://github.com/astral-sh/ty/releases)) · [import-linter](https://import-linter.readthedocs.io/) · [ast-grep](https://ast-grep.github.io/) · Companions: [language](../language.md), [testing](../testing/GUIDE.md).
