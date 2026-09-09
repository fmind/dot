# Python Tooling Details

- **Python**: target latest stable; use modern syntax (pattern matching, PEP 695 generics, `typing.Annotated`).
- **Dependencies**: `uv` exclusively — `uv add`, `uv run`, no manual venvs; commit `uv.lock` in every profile so installs and audits stay reproducible.
- **Tasks and hooks**: [mise.toml](mise.toml) exposes the canonical vocabulary per [mise](../../mise/SKILL.md); [lefthook.yml](lefthook.yml) wires pre-commit and pre-push per [lefthook](../../lefthook/SKILL.md).
- **Linting and formatting**: Ruff (`ruff check --fix`, `ruff format`) with zero warnings and no `print` (`T201`); dprint for config and markup per [dprint](../../dprint/SKILL.md).
- **Types**: `ty check` strict; `ty` is pre-1.0, so pin a compatible range and keep suppressions narrow and evidenced.
- **Testing**: `pytest` in `tests/` with `anyio` and an 85% branch-coverage gate; the default suite is offline, and web integration tests opt into a disposable Postgres via [conftest.py](conftest.py).
- **Security**: `uv audit` scans dependencies as `check:vuln`, `gitleaks` is `check:leaks`, and Trivy owns repository and configuration scanning.
- **Validation and config**: use Pydantic v2 and `pydantic-settings` `BaseSettings` for typed validation in `config.py`. Respect ecosystem-native formats; otherwise prefer YAML for human-maintained configuration and JSON for program-owned data. Document defaults and override precedence.
- **Logging**: `structlog` — `ConsoleRenderer` locally, `JSONRenderer` in production, stdlib loggers routed through it.

## Gotchas

- **Read installed source, never import to inspect**: `uv pip show <dist>` gives version and location, then `rg -n '^(class|def) <Symbol>\b' .venv/lib/python*/site-packages/<module>` finds the definition.
- **Python pin**: align the selected development interpreter with `requires-python`; `.python-version` chooses one interpreter, while `requires-python` declares the supported package range. A library may support several older minors; test the minimum supported version too.
- **`Slug` vs `Package`**: hyphenated slugs stay for the distribution, directory, image tag, and command; imports, `[project.scripts]` targets, and `python -m` use underscores.
- **`uv_build` compatibility**: use a bounded backend range supported by the selected uv release; uv uses its bundled backend when compatible and otherwise installs the requested backend. Do not widen the range just to suppress diagnostics; verify the resulting wheel and sdist. See the [uv backend contract](https://docs.astral.sh/uv/concepts/build-backend/).
- **`ty` version key**: `[tool.ty.environment].python-version` takes `major.minor` only.
- **Mise dotenv**: `[env]` with `_.file = ".env"` in `mise.toml` loads the environment for every task; `_.source` expects a shell script and silently loads nothing from a plain dotenv.
