---
name: context
description: "Measure discovery and instruction budgets in source or installed skill catalogs."
---

# Context Budgets

## Context budget

`dot agent context --project <root>` shows a token-first table: AGENTS.md, skill discovery, total, remaining budget, and status for global/local scopes, plus an informational combined total. Numbers use thousands separators and are explicitly estimates. Use `--details` for source paths, on-demand SKILL.md costs, and full coverage; `--json` retains character measurements alongside token estimates for tooling. It reads only `<root>/AGENTS.md`, `<root>/.agents/skills/`, and the shared global `~/.agents/` root. Use `--source <dot-checkout>` for authored global files (`dot_agents/AGENTS.md` and `skills/`) or `--global-root <directory>` for another shared installation; these options are mutually exclusive. The project defaults to the current directory, so pass its root when running below it.

Each scope’s AGENTS.md plus discovery must independently be below 5,000 estimated tokens. Exactly the limit fails. `--check` exits 1 if either scope fails; combined discovery and startup totals are informational. The `dot.agent.context/v4` JSON report removes v3’s `budgets.discovery`; `budgets.global` and `budgets.local` retain `limit_exclusive`, `estimated_tokens`, `remaining`, and `passed`. Discovery measurements remain under `totals`. Consumers should check the schema version and overall `passed`.

The estimator recursively counts discovered `SKILL.md` files, including nested files in linked packages. First-party packages prohibit nested skill entrypoints; use ordinary on-demand guides instead. Identical resolved files count once in combined totals; distinct same-name skills both count and are reported as collisions. Broken links, recursive symlink cycles, and invalid metadata fail with recovery guidance.

This is an offline `ceil(characters / 4)` estimate, not model tokenization or billing. Combined startup totals are informational. Host/plugin catalogs, ancestor/nested instruction files, guide/resource loads, and runtime output remain outside the report. `mise run report:skills` in the dot checkout adds category counts and parent-plus-guide load estimates. Verify the actual harness prompt separately before claiming complete request coverage.
