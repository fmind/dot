---
name: ty
description: Check Python types with ty and Astral's official skill. Use for ty diagnostics, configuration, environment resolution, or language-server setup.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/ty
  created: "2026-09-06"
  updated: "2026-09-10"
---

# ty

Use ty for Python static typing; [python-stack](../python-stack/SKILL.md) owns the common project configuration.

## Workflow

1. Inspect the pinned ty version, Python version, dependency environment, and `[tool.ty]` or `ty.toml` configuration.
1. Add `ty` with `uv add --dev ty` only when missing. Run `uv run ty check` through the project environment; narrow a diagnostic with `uv run ty check <path>` before changing code.
1. For unresolved imports, verify the interpreter, installed dependencies, source roots, and type stubs before changing annotations. Check `uv run ty check --help` for version-supported environment overrides.
1. Fix the annotation, parser, or environment causing the error, then rerun typing and behavior tests for the affected code.

## Gotchas

- `[tool.ty.environment].python-version` takes `major.minor` only. Inspect configuration precedence when both `ty.toml` and `pyproject.toml` exist.
- A latest-branch skill can describe configuration unsupported by the locked tool; check local help and current official docs.
- Standalone skill installation does not install Astral's Claude LSP configuration. Avoid blanket diagnostic suppression.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins), `plugins/astral/skills/ty`, selection `ty`. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and compare this same-name local skill before installation.

## Documentation

- [ty documentation](https://docs.astral.sh/ty/) · [Skills CLI](https://skills.sh/docs/cli)
