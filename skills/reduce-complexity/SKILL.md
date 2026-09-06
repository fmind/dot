---
name: reduce-complexity
description: "Remove technical debt and accidental complexity: dead code, duplicated logic, over-abstraction, stale config, oversized files, tests kept green. Use to simplify a project."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/reduce-complexity
  created: "2026-09-02"
  updated: "2026-09-05"
---

# Reduce Complexity

A repeatable pass that removes accidental complexity from a codebase: measure, delete, flatten, verify. [repository-review](../repository-review/SKILL.md) produces the candidate list read-only, [project-health](../project-health/SKILL.md) is the full refresh this pass belongs to, and [update-docs](../update-docs/SKILL.md) is the same pass for documentation.

## Workflow

1. **Measure**: largest files (`wc -l` over tracked sources), duplicated blocks (`rg` for repeated signatures), unused dependencies and exports, and config files nothing reads.
1. **Use the language linters**: `golangci-lint` (`unused`, `gocyclo`), `ruff` (`F401`, `C901`), `knip` for TypeScript, and `mise tasks` for orphan tasks.
1. **Sort by payoff**: rank candidates by lines removed per risk; start with dead code and unused dependencies (zero behavior change), then duplication, then abstractions with a single implementation.
1. **Delete before abstracting**: remove dead branches and pass-through wrappers; retain helpers and interfaces that hide a meaningful decision or enable a useful test seam.
1. **Flatten**: simplify nesting and package boundaries where it improves comprehension; introduce configuration only for a real variation the project supports.
1. **Verify each step**: `mise run check` and `mise run test` after every logical removal, so a regression is attributable to one change.
1. **Report**: before and after counts (files, lines, dependencies, tasks), what was removed and why, and anything intentionally kept.

## Gotchas

- **Behavior is the contract**: public APIs, CLI flags, and on-disk formats change only with the user's agreement.
- **Tests are not debt**: never delete a failing test to simplify; fix or replace it per [test-driven-development](../test-driven-development/SKILL.md).
- **One theme per commit**: when asked to commit, group by removal theme (`refactor:` or `chore:`) so each commit reverts cleanly.

## Documentation

- [golangci-lint](https://golangci-lint.run) · [Ruff rules](https://docs.astral.sh/ruff/rules/) · [knip](https://knip.dev)
- Companion skills: [project-health](../project-health/SKILL.md) (full refresh), [repository-review](../repository-review/SKILL.md) (candidate list), [update-docs](../update-docs/SKILL.md) (documentation pass), [conventional-commit](../conventional-commit/SKILL.md) (commit messages).
