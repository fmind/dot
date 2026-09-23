---
name: repository-maintenance
description: "Run a repository upkeep pass: fix tools, checks, dead code, stale config, and documentation consistency."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-maintenance
  created: "2026-09-02"
  updated: "2026-09-23"
---

# Repository Maintenance

The recurring pass that makes an existing repository current, consistent, simple, and working; it fixes in place and proves the result with the gate. [repository-review](../repository-review/SKILL.md) owns the read-only audit with ranked findings; deployments, registries, and external services stay out of scope.

## Workflow

1. **Baseline**: record `git status --short`; reuse passing evidence for unchanged inputs and run missing checks through the repository tasks. Distinguish existing failures from regressions and preserve unrelated user work.
1. **Toolchain and dependencies**: upgrade when requested or needed for a confirmed fix, one ecosystem at a time with validation per [upgrade-tools](../upgrade-tools/SKILL.md).
1. **Stack fit**: use the stack skills to resolve gaps; preserve established project choices unless changing them fixes an observed problem or fulfills the request.
1. **Tasks and hooks**: `mise.toml` exposes the canonical task vocabulary per [mise](../mise/SKILL.md); hooks and CI call those tasks per [lefthook](../github-actions/references/lefthook.md) and [github-actions](../github-actions/references/ci-cd/GUIDE.md).
1. **Complexity**: remove dead code, duplicated logic, stale config, unused dependencies, and abstractions that do not earn their maintenance cost.
1. **Security**: run the scans the repository has adopted; use [security-review](../security-review/references/code-review/GUIDE.md) for broader security work when the requested scope calls for it.
1. **Docs**: create or synchronize `README.md`, `AGENTS.md`, skills, and wider docs per [repository-docs](../repository-docs/SKILL.md).
1. **Agent files**: promote repeated instructions into `.agents/skills/` per [skillify](../skillify/SKILL.md).
1. **Final gate**: Run the full gate (`mise run all`); when the tree carries unrelated changes, apply the [dirty-tree rule](../mise/SKILL.md#gotchas).
1. **Report**: what changed per area (the tree holds only intended changes), what was left alone and why, and the highest proven rung of the [proof ladder](../production-readiness/SKILL.md).

## Documentation

- [mise tasks](https://mise.jdx.dev/tasks/) — the gate vocabulary this pass proves.
- Companion skills: [repository-review](../repository-review/SKILL.md) (audit only), [project-scaffolding](../project-scaffolding/references/bootstrap.md) (bootstrap layer), [git-add-commit-push](../git-delivery/references/git-add-commit-push.md) (commit on request).
