---
name: uv
description: Resolve and sync Python dependency graphs with uv; manage pyproject.toml, uv.lock, scripts, tools, and package builds. Use for uv CLI work.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/uv
  created: "2026-09-06"
  updated: "2026-09-06"
---

# uv

Use uv for Python dependency and environment operations; [python-stack](../python-stack/SKILL.md) owns project defaults and [python-script](../python-script/SKILL.md) owns PEP 723 scripts.

## Workflow

1. Inspect `pyproject.toml`, `uv.lock`, Python constraints, and the current uv help before choosing project, script, or tool mode.
1. Use `uv add` for project dependencies and `uv sync --locked` to reproduce the existing graph; keep tool installations separate from application dependencies.
1. Validate lock consistency with `uv lock --check`, then run the project's normal checks after any dependency change.

## Gotchas

- `uv run` may synchronize the environment. Use the project's locked or frozen policy in automation, and review lockfile diffs.
- The Astral plugin also provides a ty LSP; installing its standalone skills does not configure that language server.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select its uv guidance.

## Documentation

- [uv documentation](https://docs.astral.sh/uv/) · [Skills CLI](https://skills.sh/docs/cli)
