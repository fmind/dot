---
name: diff-review
description: Inspect changed code in a diff, patch, branch, or PR for correctness defects. Use for pre-merge or self-review, spec compliance, test gaps, and regression risk, not whole-repo audit or plan review.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diff-review
  created: "2026-08-08"
  updated: "2026-09-05"
---

# Diff Review

Review a bounded code change for concrete correctness defects and missing intent. [repository-review](../repository-review/SKILL.md) owns whole-repository audits and [plan-review](../plan-review/SKILL.md) owns proposals.

## Workflow

1. **Resolve the diff**: intended behavior, base/head or working-tree scope, affected callers, tests, and repository constraints; preserve unrelated work.
1. **Check intent**: verify required behavior and acceptance before judging implementation quality; read surrounding code and dependency contracts.
1. **Trace failures**: inputs, state transitions, error paths, concurrency, persistence, permissions, and compatibility only where the change affects them.
1. **Verify proportionally**: reproduce material findings with focused tests or source evidence; keep full-gate and runtime proof tied to the reviewed candidate.
1. **Report actionable defects**: priority, exact location, reachable trigger, impact, and smallest correction; separate confirmed findings from uncertainty and avoid preference-only noise.

## Gotchas

- **Review only by default**: Do not edit code, resolve threads, or approve the pull request unless the user separately asks; act on review threads with [github-pull-request](../github-pull-request/SKILL.md).
- **Design smells**: Challenge pass-through abstractions, hidden dependency construction, tests that bypass the public seam, and flexibility with no second concrete use.
- **Generated and vendored hunks**: Review the generator input and the regeneration command, not the output line by line.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- Companion skills: [repository-review](../repository-review/SKILL.md) (whole-repository audit), [plan-review](../plan-review/SKILL.md) (plans), [quality-assurance](../quality-assurance/SKILL.md) (broader test campaign), [github-pull-request](../github-pull-request/SKILL.md) (acting on review threads).
