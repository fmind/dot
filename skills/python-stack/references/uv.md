---
name: uv
description: "Dependency resolution, environments, packaging, and lockfiles."
---

# uv

Use uv for Python dependency and environment operations; [python-stack](foundation/GUIDE.md) owns project defaults and [python-script](python-script/GUIDE.md) owns PEP 723 scripts.

## Workflow

1. Inspect `pyproject.toml`, `uv.lock`, Python constraints, and the current uv help before choosing project, script, or tool mode.
1. Use `uv add` for project dependencies and `uv sync --locked` to reproduce the existing graph; keep tool installations separate from application dependencies.
1. Validate lock consistency with `uv lock --check`, then run the project's normal checks after any dependency change.
1. Qualify a build outside the source tree with `uv export --locked --no-dev --no-emit-project -o requirements.txt`, which emits hashes, then `uv venv`, `uv pip sync --require-hashes requirements.txt`, and `uv pip install <wheel>`.

## Gotchas

- **Disk reuse**: use the compatible mise-selected Python rather than downloading another interpreter; align runtime pins through `mise` and `upgrade-tools`. Keep project environments separate for dependency isolation, but reuse uv's shared cache on the same filesystem so its normal clone/hardlink strategy can share package storage. Do not force copies or create per-task cache roots without an isolation requirement.
- **Temporary environments**: remove task-created qualification environments and exports after their last check, including failure paths; retain project `.venv` directories and requested build artifacts. Use native `uv cache prune` for authorized periodic maintenance, not blanket cache deletion after every task. Never edit uv's cache by hand or use symlink link mode with a disposable cache; summed directory sizes can overcount shared storage. See [caching](https://docs.astral.sh/uv/concepts/cache/).
- Inspect distribution versions and source with `uv pip show <dist>`, then read the reported files; importing a module merely to inspect it can execute code.
- `.python-version` selects one development interpreter; `requires-python` declares the supported range. Keep them compatible and test a library's minimum supported version.
- Keep `uv_build` in a bounded range supported by the selected uv release. uv uses its bundled backend when compatible and otherwise installs the requested backend; verify wheel and sdist instead of widening constraints to hide diagnostics. See the [backend contract](https://docs.astral.sh/uv/concepts/build-backend/).
- Commit `uv.lock`, libraries included: it pins your development environment, not your consumers' installs. Build environments with `uv sync --locked`, run tasks with `uv run --frozen`, and use `uv run --locked` when a task may be the first uv call; a bare `uv run` or `uv sync` re-locks and rewrites `uv.lock`, so it never belongs in a gate. `UV_LOCKED` and `UV_FROZEN` apply the same policy once from `[env]`.
- `UV_PROJECT` and other `UV_*` variables redirect project discovery, so a command run elsewhere silently operates on the exported project; `VIRTUAL_ENV` is ignored by project commands but selects the target of `uv pip`. Clear them, and pass `--no-config` to ignore a user-level `uv.toml`, when scaffolding or verifying a separate project.
- An unknown `[tool.uv]` key only warns during settings discovery, so a misspelled setting silently does nothing; `required-version` is enforced and fails the run.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins), `plugins/astral/skills/uv`, selection `uv`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) and compare this local guide before installation.

## Documentation

- [uv documentation](https://docs.astral.sh/uv/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [uv](https://github.com/astral-sh/uv/releases) · [changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
