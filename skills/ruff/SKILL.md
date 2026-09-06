---
name: ruff
description: Lint and format Python with Ruff and Astral's official skill. Use for Ruff configuration, diagnostics, safe fixes, or Python formatting.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/ruff
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Ruff

Use Ruff for Python linting and formatting; [dprint](../dprint/SKILL.md) owns config and markup formatting.

## Workflow

1. Inspect `ruff.toml` or `[tool.ruff]`, the pinned version, and the project's existing formatter ownership.
1. Use `uv run ruff check <paths>` and `uv run ruff format --check <paths>` to identify the affected changes before writing.
1. Apply fixes only within the authorized files, inspect the diff, then run the canonical project checks.

## Gotchas

- Unsafe fixes can alter behavior; inspect the proposed change and test it instead of adding `--unsafe-fixes` to a routine gate.
- Do not broaden formatting across a dirty repository or weaken lint rules to hide a defect.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select its Ruff linting or formatting guidance.

## Documentation

- [Ruff documentation](https://docs.astral.sh/ruff/) · [Skills CLI](https://skills.sh/docs/cli)
