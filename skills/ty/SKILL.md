---
name: ty
description: Check Python types with ty and Astral's official skill. Use for ty diagnostics, configuration, environment resolution, or language-server setup.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/ty
  created: "2026-09-06"
  updated: "2026-09-06"
---

# ty

Use ty for Python static typing; [python-stack](../python-stack/SKILL.md) owns the common project configuration.

## Workflow

1. Inspect the pinned ty version, Python version, dependency environment, and `[tool.ty]` or `ty.toml` configuration.
1. Run `uv run ty check` through the project environment; narrow a diagnostic to the relevant typed boundary before changing code.
1. Fix the annotation, parser, or environment causing the error, then rerun typing and behavior tests for the affected code.

## Gotchas

- A latest-branch skill can describe configuration unsupported by the locked pre-1.0 tool; check local help and current official docs.
- Standalone skill installation does not install Astral's Claude LSP configuration. Avoid blanket diagnostic suppression.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select its ty type-checking guidance.

## Documentation

- [ty documentation](https://docs.astral.sh/ty/) · [Skills CLI](https://skills.sh/docs/cli)
