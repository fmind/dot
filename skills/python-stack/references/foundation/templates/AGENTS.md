# AGENTS.md (Project)

Context and rules for AI agents working in this repository. Humans should start with `README.md`.

## Project overview

- **Name**: <slug>
- **Description**: <1-2 sentences on what this project does.>
- **Language**: Python <major.minor>+ (`pyproject.toml`), managed with `uv`.

## Setup & core commands

All work goes through `mise` (see `mise.toml`); git hooks and CI call the same tasks.

- Install: `mise run install` — sync the virtualenv (`uv sync --locked`) and install git hooks.
- Format: `mise run format` — `ruff` (import sort + format) and `dprint`.
- Check: `mise run check` — `ruff` lint, `ty` types, `deptry` dependencies, `uv audit`, `dprint check`, `gitleaks`, `pyproject` validation.
- Test: `mise run test` — offline `pytest` suite with an 85% branch-coverage gate.
- Build: `mise run build` — `uv build` (wheel + sdist).
- Docs: `mise run build:docs` — strict Zensical build with the generated API reference; `mise run serve:docs` previews it.
- Watch: `mise run watch` — re-run offline tests on source changes; application profiles may supply their development command.

## Definition of done

A change is complete only when, locally, `mise run format` is clean, `mise run check` reports no findings, `mise run test` is green, `mise run build` succeeds, and new or changed behavior has a test. Fix root causes — never weaken an assertion, add a skip/`xfail`, loosen a type, or suppress a lint error to force a green result.

## Conventions & idioms

- **Never swallow errors**: raise specific exceptions and chain with `raise ... from err`; never use a bare `except` or silently swallow errors.
- **Validate and document configuration**: add typed validation when the application needs it; document defaults and override precedence, and never commit secrets.
- **Use modern type annotations**: `list[str]`, `X | Y`, `typing.Annotated`; keep `ty check` clean and validate external input at boundaries.
- **Add only dependencies in use**: framework, database, and logging choices belong to the selected application profile.
- **Use Conventional Commits without attribution**: `feat:`, `fix:`, `refactor:`, `chore:`; no attribution in commit messages.

## Repository layout

- `src/<package>/__init__.py` — package exports and `__version__`; business logic lives in cohesive modules.
- `tests/` — deterministic offline behavior tests; add integration fixtures only when the project needs them.
- `pyproject.toml` — dependencies and Ruff/ty/pytest configuration; `mise.toml` — tasks and pinned tools; `lefthook.yml` — hooks; `dprint.json` — markup/config formatting.
- Application profiles add their own entry points, configuration, and project-specific instructions.
