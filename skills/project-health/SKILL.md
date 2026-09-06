---
name: project-health
description: Make an existing project up to date, consistent, simple, and working. Use when a project health review includes fixing issues and verifying the result.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/project-health
  created: "2026-09-02"
  updated: "2026-09-06"
---

# Project Health

The recurring pass that makes an existing repository current, consistent, simple, and working; it fixes in place and proves the result with the gate. [repository-review](../repository-review/SKILL.md) owns the read-only audit with ranked findings; deployments, registries, and external services stay out of scope.

## Workflow

1. **Baseline**: record `git status --short`, then `mise run check` and `mise run test`; distinguish existing failures from regressions and preserve unrelated user work.
1. **Toolchain and dependencies**: bump one ecosystem at a time and validate between each per [upgrade-tools](../upgrade-tools/SKILL.md).
1. **Stack fit**: use the stack skills to resolve gaps; preserve established project choices unless changing them fixes an observed problem or fulfills the request.
1. **Tasks and hooks**: `mise.toml` exposes the canonical task vocabulary per [mise](../mise/SKILL.md); hooks and CI call those tasks per [lefthook](../lefthook/SKILL.md) and [github-actions](../github-actions/SKILL.md).
1. **Complexity**: remove dead code, duplicated logic, stale config, unused dependencies, and abstractions that do not earn their maintenance cost.
1. **Security**: run the scans the repository has adopted; use [secure](../secure/SKILL.md) for broader security work when the requested scope calls for it.
1. **Docs**: sync `README.md` and `AGENTS.md` per [update-docs](../update-docs/SKILL.md); trim wider docs per [update-docs](../update-docs/SKILL.md).
1. **Agent files**: promote repeated instructions into `.agents/skills/` per [skillify](../skillify/SKILL.md).
1. **Final gate**: Run the full gate (`mise run all`); if the tree carries unrelated changes and the gate write-formats, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)).
1. **Report**: what changed per area (the tree holds only intended changes), what was left alone and why, and the highest proven rung of the [proof ladder](../production-readiness/SKILL.md).

## Documentation

- [mise tasks](https://mise.jdx.dev/tasks/) — the gate vocabulary this pass proves.
- Companion skills: [repository-review](../repository-review/SKILL.md) (audit only), [new-project](../new-project/SKILL.md) (bootstrap layer), [git-add-commit-push](../git-add-commit-push/SKILL.md) (commit on request).
