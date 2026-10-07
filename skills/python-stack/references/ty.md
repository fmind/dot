---
name: ty
description: "Type diagnostics and environment resolution."
---

# ty

Use ty for Python static typing; [foundation](foundation/GUIDE.md) owns the common project configuration.

## Workflow

1. **Add ty only when missing**: use `uv add --dev ty`. Run `uv run ty check` through the project environment; narrow a diagnostic with `uv run ty check <path>` before changing code.
1. **Check the environment before annotations**: for unresolved imports, verify the interpreter, installed dependencies, source roots, and type stubs before changing annotations.

## Gotchas

- **Know ty's configuration precedence**: ty takes the Python version from `[tool.ty.environment].python-version` (`major.minor` only), else the minimum of `project.requires-python`; a `ty.toml` replaces the whole `[tool.ty]` section.
- **Suppress with `# ty: ignore[rule-name]`**: place it on the offending line; never clear a gate with `ty check --add-ignore`, which writes those comments and then prints `All checks passed!`.
- **Standalone skill installation does not install Astral's Claude LSP configuration.**

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins), `plugins/astral/skills/ty`, selection `ty`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) and compare this local guide before installation.

## Documentation

- [ty documentation](https://docs.astral.sh/ty/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [ty](https://github.com/astral-sh/ty/releases)
