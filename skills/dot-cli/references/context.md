---
name: context
description: "Measure discovery and instruction budgets in source or installed skill catalogs."
---

# Context Budgets

`dot agent context --project <root>` prints estimated token budgets (`AGENTS.md`, skill discovery, total, remaining, status) for global and local scopes plus an informational combined total (`--project` defaults to `.`, so pass the repo root from subdirectories). It reads `<root>/AGENTS.md`, `<root>/.agents/skills/`, and `~/.agents/` (or `--source <dot-checkout>` for `dot_agents/AGENTS.md` and `skills/`). `--details` adds paths and on-demand `SKILL.md` costs; `--json` (`dot.agent.context/v5`) adds character counts, `budgets.{global,local}` (`limit_exclusive`, `estimated_tokens`, `remaining`, `passed`), `totals` (excluding host-synced dirs like Claude's `synced/`), `duplicates`, and overall `passed`.

Each scope's `AGENTS.md` plus discovery must stay strictly below 5,000 `ceil(characters / 4)` tokens (`5000` fails). `--check` prints `PASS` (add `--details` for the table) or the full failing report and exits 1 when either scope exceeds 5,000 or `duplicates` is non-empty.

The estimator recursively counts `SKILL.md` files (first-party packages forbid nested `SKILL.md` files; use `references/`). Symlinked roots resolving to the same file (`.claude/skills -> .agents/skills`) count once, while distinct files sharing a `name` both count and fail `duplicates` (hosts resolve collisions inconsistently and may shadow built-in commands). Broken symlinks, cycles, and invalid metadata fail fast. Offline estimates exclude host/plugin catalogs, ancestor/nested `AGENTS.md` files, guide loads, and runtime output.
