---
name: context
description: "Measure instruction, skill, and subagent discovery budgets in source or installed catalogs."
---

# Context Budgets

`dot context --project <root>` prints estimated token budgets (`AGENTS.md`, skill discovery, context subtotal/left, subagent discovery/left, startup total, status) for global and local scopes plus an informational combined total (`--project` defaults to `.`, so pass the repo root from subdirectories). It reads `<root>/AGENTS.md`, `<root>/.agents/skills/`, `<root>/.agents/supagents/`, and `~/.agents/{AGENTS.md,skills,supagents}` (or `--source <dot-checkout>` for `dot_agents/{AGENTS.md,supagents}` and `skills/`). `--details` adds paths and on-demand `SKILL.md` / subagent file costs; `--json` (`dot.context/v6`) adds character counts, `budgets.{global,local}` and `subagent_budgets.{global,local}` (`limit_exclusive`, `estimated_tokens`, `remaining`, `passed`), `totals` (excluding host-synced dirs like Claude's `synced/` and `_*.md` supagent partials), `duplicates`, `duplicate_subagents`, and overall `passed`.

Per scope, `AGENTS.md` plus skill discovery must stay strictly below `5,000` `ceil(characters / 4)` tokens (`5000` fails) and subagent discovery (`- <name>: <description>`) strictly below `2,000` (`2000` fails). `--check` prints a one-line `PASS` summary (add `--details` for the table) or the full failing report and exits `1` when any scope budget fails or `duplicates` / `duplicate_subagents` is non-empty. `-q`/`--quiet` prints that one-line `PASS` or failing errors (`--quiet --json` keeps only `schema`, `passed`, `budgets`, `subagent_budgets`, `duplicates`, `duplicate_subagents`; `--quiet` + `--details` exits `2`).

The estimator recursively scans `SKILL.md` and non-`_` `supagents/*.md` files (first-party packages forbid nested `SKILL.md` files; use `references/`). Symlinked roots resolving to the same file (`.claude/skills -> .agents/skills`) count once, while distinct files sharing a skill or subagent `name` both count and fail `--check` (hosts resolve collisions inconsistently and may shadow built-in commands). Broken symlinks, cycles, and invalid metadata fail fast. Offline estimates exclude host/plugin catalogs, ancestor/nested `AGENTS.md` files, guide loads, and runtime output.
