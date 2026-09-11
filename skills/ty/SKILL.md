---
name: ty
description: Check Python types with ty and Astral's official skill. Use for ty diagnostics, configuration, environment resolution, or language-server setup.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/ty
  created: "2026-09-06"
  updated: "2026-09-11"
---

# ty

Use ty for Python static typing; [python-stack](../python-stack/SKILL.md) owns the common project configuration.

## Workflow

1. Inspect the pinned ty version, Python version, dependency environment, and `[tool.ty]` or `ty.toml` configuration.
1. Add `ty` with `uv add --dev ty` only when missing. Run `uv run ty check` through the project environment; narrow a diagnostic with `uv run ty check <path>` before changing code.
1. For unresolved imports, verify the interpreter, installed dependencies, source roots, and type stubs before changing annotations.
1. Fix the annotation, parser, or environment causing the error, then rerun typing and behavior tests for the affected code.

## Gotchas

- ty takes the Python version from `[tool.ty.environment].python-version` (`major.minor` only), else the minimum of `project.requires-python`; a `ty.toml` replaces the whole `[tool.ty]` section.
- A latest-branch skill can describe configuration unsupported by the locked tool; check local help and current official docs.
- Suppress with `# ty: ignore[rule-name]` on the offending line; never clear a gate with `ty check --add-ignore`, which writes those comments and then prints `All checks passed!`.
- Standalone skill installation does not install Astral's Claude LSP configuration.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins), `plugins/astral/skills/ty`, selection `ty`. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and compare this same-name local skill before installation.

## Documentation

- [ty documentation](https://docs.astral.sh/ty/) · [Skills CLI](https://skills.sh/docs/cli)
