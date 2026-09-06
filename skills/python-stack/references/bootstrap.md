# Python Project Bootstrap

## Project Scaffolding Workflow

1. **Information**: define `Slug`, `Description`, `Holder/Year`, and `Package` (`Slug` with underscores) — every import path uses `Package`.
1. **Bootstrap** (agents use [google-adk](../../google-adk/SKILL.md) instead):
   ```bash
   uv init --app --package --build-backend uv --vcs none --description "<description>" <slug>
   cd <slug> && uv python pin <major.minor>  # align .python-version with requires-python
   ```
1. **Manifest**: `pyproject.toml` from [pyproject.toml.template](pyproject.toml.template) with one profile — web keeps the Web block; CLI adds `typer` and drops the Web block and `testcontainers`; library sets `dependencies = []` and drops `[project.scripts]` and `testcontainers`.
1. **Config files**:
   - [mise.toml](mise.toml) (swap `watch` for non-web projects) and [lefthook.yml](lefthook.yml).
   - `dprint.json` per [dprint](../../dprint/SKILL.md); `.env.example` from [env.example](env.example) and, for web projects, copy it to the ignored `.env` before the first import; `.gitignore` from [gitignore](gitignore).
   - `AGENTS.md` from [AGENTS.md](AGENTS.md); `LICENSE` per [project-license](../../project-license/SKILL.md).
1. **Sources**: `src/<package>/__init__.py` from [init.py](init.py) (web), [init-cli.py](init-cli.py) (CLI), or [init-library.py](init-library.py); web and CLI add `__main__.py` from [main.py](main.py).
1. **Tests**: `tests/__init__.py`, then per profile:
   - Web: [test_web.py](test_web.py), [test_integration.py](test_integration.py), and root [conftest.py](conftest.py) (only `test:integration` starts Postgres).
   - CLI: [test_smoke.py](test_smoke.py) and [test_cli.py](test_cli.py). Library: [test_library.py](test_library.py).
1. **Validate**: `git init --initial-branch=main`, then `mise run install`, `mise run format`, `mise run check`, `mise run test`; before the first commit, `check:leaks` scans the working tree.
1. **Finish**: `README.md` per [readme-md](../../readme-md/SKILL.md), then report the verified result; if committing was requested, stage only the intended files and use [conventional-commit](../../conventional-commit/SKILL.md).
