# Python Tooling Details

- **Python**: target latest stable; use modern syntax (pattern matching, PEP 695 generics, `typing.Annotated`).
- **Dependencies**: `uv` exclusively — `uv add`, `uv run`, no manual venvs; commit `uv.lock` in every profile so installs and audits stay reproducible.
- **Tasks and hooks**: [mise.toml](references/mise.toml) exposes the canonical vocabulary per [mise](../mise/SKILL.md); [lefthook.yml](references/lefthook.yml) wires pre-commit and pre-push per [lefthook](../lefthook/SKILL.md).
- **Linting and formatting**: Ruff (`ruff check --fix`, `ruff format`) with zero warnings and no `print` (`T201`); dprint for config and markup per [dprint](../dprint/SKILL.md).
- **Types**: `ty check` strict; `ty` is pre-1.0, so pin a compatible range and keep suppressions narrow and evidenced.
- **Testing**: `pytest` in `tests/` with `anyio` and an 85% branch-coverage gate; the default suite is offline, and web integration tests opt into a disposable Postgres via [conftest.py](references/conftest.py).
- **Security**: `uv audit` scans dependencies as `check:vuln` and `gitleaks` is `check:leaks`; SAST is opt-in per [opengrep](../opengrep/SKILL.md).
- **Validation and config**: Pydantic v2 and `pydantic-settings` `BaseSettings`; typed `config.py`, YAML only for cross-language needs.
- **Logging**: `structlog` — `ConsoleRenderer` locally, `JSONRenderer` in production, stdlib loggers routed through it.

## Gotchas

- **Read installed source, never import to inspect**: `uv pip show <dist>` gives version and location, then `rg -n '^(class|def) <Symbol>\b' .venv/lib/python*/site-packages/<module>` finds the definition.
- **`uv init` Python pin**: it writes `.python-version` for whatever interpreter it resolves; run `uv python pin <major.minor>` or `uv sync` breaks.
- **`Slug` vs `Package`**: hyphenated slugs stay for the distribution, directory, image tag, and command; imports, `[project.scripts]` targets, and `python -m` use underscores.
- **`uv_build` upper bound**: keep `[build-system].requires` at least one minor ahead of the pinned `uv`, or `uv build` warns.
- **`ty` version key**: `[tool.ty.environment].python-version` takes `major.minor` only.
- **Mise dotenv**: `[env]` with `_.file = ".env"` in `mise.toml` loads the environment for every task; `_.source` expects a shell script and silently loads nothing from a plain dotenv.
