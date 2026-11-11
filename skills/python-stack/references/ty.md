---
name: ty
description: "Type diagnostics and environment resolution."
---

# ty

Python static type checking with Astral `ty`; [foundation](foundation/GUIDE.md) owns baseline `[tool.ty]` config.

## Workflow

1. **Install bounded pre-1.0 range**: `uv add --dev "ty>=<latest>,<0.1"`, then run `uv run ty check [<path>]`.
1. **Verify env before editing types**: on `unresolved-import`, check Python version, `.venv` packages, `src/` roots, and PEP 561 stubs first.
1. **Legacy baseline (`0.0.93+`)**: set `[tool.ty] baseline = "ty-baseline.json"`, run `ty check --update-baseline` once, and commit. Baseline entries match file + rule + column span (not line), so rerun `--update-baseline` after fixes and accept only entry-deleting diffs.

## Gotchas & Upstream Skill

- **Config precedence**: `[tool.ty.environment].python-version` (`major.minor`) > `project.requires-python` floor; standalone `ty.toml` overrides the entire `[tool.ty]` table.
- **Rule-scoped suppressions only**: use `# ty: ignore[rule-name]` (`blanket-ignore-comment = "error"` rejects bare `# type: ignore`, and mypy codes like `[assignment]` do nothing). Warnings (`unused-ignore-comment`) fail `ty check` — never pass `--exit-zero-on-warning` or `--add-ignore`.
- Upstream: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) (`ty`, per [vendor-skills](../../agent-project/references/vendor-skills.md) · [Skills CLI](https://skills.sh/docs/cli); excludes Claude LSP config) · [ty docs](https://docs.astral.sh/ty/) · [Releases](https://github.com/astral-sh/ty/releases).
