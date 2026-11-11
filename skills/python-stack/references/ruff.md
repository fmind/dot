---
name: ruff
description: "Python linting, formatting, imports, and safe fixes."
---

# Ruff

Python linting, import sorting, and formatting; [dprint](../../mise/references/dprint.md) owns config and markup.

## Workflow

1. **Check first**: run `uv run ruff check <paths>` and `uv run ruff format --check <paths>`.
1. **Sort imports before formatting**: run `uv run ruff check --select I --fix <paths>` then `uv run ruff format <paths>` (`ruff format` never reorders imports), scoped strictly to owned paths.

## Gotchas

- **No routine `--unsafe-fixes`**: inspect and test any unsafe fix manually.
- **Exclude `*.md`**: `ruff format` rewrites Python blocks inside Markdown by default — pass `.py` paths or set `extend-exclude = ["*.md"]` where dprint owns Markdown.
- **Narrow `# noqa: CODE` only**: bare `# noqa` fails `PGH004`, stale ones fail `RUF100`, and `--add-noqa`/`--add-ignore` never belong in fixes.
- **Dead-code sweeps via `vulture`**: Ruff misses unused functions/classes or test-only code; run `vulture src --min-confidence 60 --ignore-decorators '@*_validator'` (`@*.command,@*.callback` on Typer/Click; use `uv run vulture` when project-pinned, workstation `mise` `vulture` ad hoc, or `uvx --from 'vulture==<version>' vulture` off-workstation) during reviews and verify hits with `rg` (watch hooks, `getattr`, Pydantic fields).
- **Upstream & Docs**: [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) (`ruff`, per [vendor-skills](../../agent-project/references/vendor-skills.md) · [Skills CLI](https://skills.sh/docs/cli)) · [Ruff docs](https://docs.astral.sh/ruff/) · [Releases](https://github.com/astral-sh/ruff/releases) ([changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md)).
