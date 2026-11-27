---
name: context
description: "Measure instruction, skill, and subagent discovery budgets in source or installed catalogs."
---

# Context Budgets

Measure global and local startup discovery costs for `AGENTS.md`, skills, and subagents (`ceil(characters / 4)` tokens).

## Commands & flags

| Flag / option             | Effect                                                                                                                                                                                                                                                |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--project <root>`        | Measure `<root>/AGENTS.md`, `<root>/.agents/{skills,supagents}` alongside global scope, plus repo-local `.agents/agents/`, `.github/agents/`, and `.agents/agents.json` for global-subagent shadowing (defaults to `.`; pass repo root from subdirs). |
| `--source <dot-checkout>` | Measure source `dot_agents/{AGENTS.md,supagents}` and `skills/` instead of installed `~/.agents/{AGENTS.md,skills,supagents}`.                                                                                                                        |
| `--details`               | Add file paths and on-demand `SKILL.md` / subagent file token costs.                                                                                                                                                                                  |
| `--json`                  | Emit `dot.context/v6` with char counts, `budgets.{global,local}`, `subagent_budgets.{global,local}`, `totals`, `duplicates`, `duplicate_subagents`, `passed`.                                                                                         |
| `--check`                 | Print one-line `PASS` (or full failing report) and exit `1` if any scope budget fails or `duplicates`/`duplicate_subagents` is non-empty.                                                                                                             |
| `-q` / `--quiet`          | Print only the one-line `PASS` or errors (`--quiet --json` trims to verdict/budgets/duplicates; `--quiet --details` exits `2`).                                                                                                                       |

## Budget limits & rules

- **Per-scope limits (strictly exclusive)**: `AGENTS.md` + skill discovery must stay `< 5,000` tokens (`5000` fails); subagent discovery (`- <name>: <description>`) must stay `< 2,000` tokens (`2000` fails). Combined totals are informational.
- **Recursive scanning & shadowing**: discovers `SKILL.md` and non-`_` `supagents/*.md` files (excluding host-synced dirs like Claude's `synced/` and `_*.md` partials; first-party packages forbid nested `SKILL.md`, using `references/` instead). Also inspects repo-local `.agents/agents/`, `.github/agents/`, and `.agents/agents.json` for names shadowing global subagents, failing closed (exit `1`) on symlinked, malformed, duplicate-key, unsupported-key, or repo-escaping `.agents/agents.json` manifests.
- **Symlinks & collisions**: symlinked roots resolving to the same file (`.claude/skills -> .agents/skills`) count once; distinct files sharing a skill or subagent `name` both count and fail `--check`. Broken symlinks, cycles, and invalid metadata fail fast.
- **Offline scope**: estimates exclude host/plugin catalogs, ancestor/nested `AGENTS.md` files, guide loads, and runtime output.
