---
name: ty
description: "Type diagnostics and environment resolution."
---

# ty

Use ty for Python static typing; [foundation](foundation/GUIDE.md) owns the common project configuration.

## Workflow

1. **Add ty only when missing**: use `uv add --dev "ty>=<latest>,<0.1"` to keep the foundation's pre-1.0 range; plain `uv add` writes an unbounded floor. Run `uv run ty check` through the project environment; narrow a diagnostic with `uv run ty check <path>` before changing code.
1. **Check the environment before annotations**: for unresolved imports, verify the interpreter, installed dependencies, source roots, and type stubs before changing annotations.
1. **Adopt ty on legacy code with a baseline**: when an existing project starts gating on ty with many diagnostics, propose a preview baseline (ty 0.0.93+): set `[tool.ty] baseline = "ty-baseline.json"`, run `ty check --update-baseline` once, and commit the file. Entries match by file, rule, and column span, not line, so a new diagnostic shaped like a fixed one can pass: rerun `--update-baseline` after each fix and accept only diffs that delete entries.

## Gotchas

- **Know ty's configuration precedence**: ty takes the Python version from `[tool.ty.environment].python-version` (`major.minor` only), else the minimum of `project.requires-python`; a `ty.toml` replaces the whole `[tool.ty]` section.
- **Suppress with `# ty: ignore[rule-name]` on the offending line**: the foundation sets `blanket-ignore-comment = "error"`, a bare `# type: ignore` hides every ty diagnostic on its line, and mypy codes such as `[assignment]` hide nothing. Warnings, including `unused-ignore-comment`, fail `ty check`; never pass `--exit-zero-on-warning`. Never clear a gate with `--add-ignore` (it writes ignores, then prints `All checks passed!`) or with an `--update-baseline` that adds entries.
- **Standalone installs skip the LSP configuration**: standalone skill installation does not install Astral's Claude LSP configuration.

## Official Skills

Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins), `plugins/astral/skills/ty`, selection `ty`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) and compare this local guide before installation.

## Documentation

- [ty documentation](https://docs.astral.sh/ty/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [ty](https://github.com/astral-sh/ty/releases)
