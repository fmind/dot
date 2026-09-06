---
name: plan-execution
description: Execute an accepted implementation plan in bounded, verified slices. Use when coordinating shared files, resuming planned work, or finishing scoped tasks.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/plan-execution
  created: "2026-08-08"
  updated: "2026-09-06"
---

# Plan Execution

Turn an accepted plan into reviewable evidence slice by slice; [implementation-plan](../implementation-plan/SKILL.md) writes the plan, and commit, push, deploy, and publication stay separate authorities.

## Workflow

1. **Read the task and baseline**: confirm implementation is requested, reconcile the accepted plan with current files and tests, and preserve staged, unstaged, and untracked user work.
1. **Execute by dependency**: take the smallest useful slice, use the applicable stack guidance, and touch only files needed for that outcome.
1. **Prove the change**: use [test-driven-development](../test-driven-development/SKILL.md) for regressions, characterization for refactors, and native validation for configuration or documentation.
1. **Inspect the result**: run focused checks, review the diff against the requested behavior, and fix unexpected failures before expanding the change.
1. **Continue**: finish the authorized slices; ask only when changed scope or an unresolved dependency requires a decision, and keep independent work moving.
1. **Gate and report**: run `mise run all`, then report the changes, evidence, and remaining proof gaps; preserve unrelated dirt per [mise](../mise/SKILL.md).

## Gotchas

- **Parallel agents**: Delegate only independent tasks with disjoint file or runtime ownership; give each worker the raw task contract and minimum context, not the intended answer.
- **Shared state**: Assign one owner to shared files, generated state, migrations, and runtime leases; serialize integration and gate the combined candidate.
- **Agent reports are not evidence**: Inspect every returned diff and rerun its proof.
- **Stop rather than weaken an assertion**: never skip a gate, broaden an exclusion, or hide a warning; use [systematic-debugging](../systematic-debugging/SKILL.md) for unexpected failures and revisit the plan when repeated fixes expose new coupling.
- **Blocked proof**: When a service, credential, decision, or runtime blocks proof, continue safe local work and report the exact gap; never claim completion because the budget or context is exhausted.

## Documentation

- Adapted from [Superpowers executing-plans](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/executing-plans/SKILL.md), [Superpowers subagent-driven development](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/subagent-driven-development/SKILL.md).
- Companion skills: [implementation-plan](../implementation-plan/SKILL.md) (the plan), [test-driven-development](../test-driven-development/SKILL.md) (red-green slices), [diff-review](../diff-review/SKILL.md) (risky deltas), [systematic-debugging](../systematic-debugging/SKILL.md) (unexpected failures), [production-readiness](../production-readiness/SKILL.md) (proof ladder).
