---
name: repository-review
description: "Review code, diffs, PRs, or repositories for correctness and regressions."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-review
  created: "2026-08-01"
  updated: "2026-09-26"
---

# Repository Review

Review code or a repository read-only and report actionable defects. Select the requested scope before loading a procedure; a patch review does not imply a whole-repository audit. [plan-review](../implementation-plan/references/plan-review.md) owns proposals; [repository-maintenance](../repository-maintenance/SKILL.md) owns applying broad fixes.

## Workflow

1. **Select scope**: for a diff, patch, branch, PR, or self-review, follow [diff review](references/diff-review.md). For an entire repository or cross-cutting audit, follow [repository audit](references/repository-audit.md) and the [review matrix](references/review-matrix.md). Load only the requested mode.
1. **Record the candidate**: read repository instructions and inspect Git status; distinguish the base/head, staged, unstaged, and untracked changes relevant to the review. Preserve user work and tie evidence to that candidate.
1. **Establish intent**: trace requirements through the affected source, callers, tests, and contracts; inspect generator inputs for generated or vendored changes. Challenge speculative abstractions and tests that bypass the public boundary only when they cause a concrete defect.
1. **Trace risk**: examine reachable failures in correctness, permissions, data integrity, concurrency, compatibility, and resource lifecycle within scope. Use [security-review](../security-review/references/code-review/GUIDE.md) for security-sensitive changes such as authorization, uploads, deserialization, subprocesses, credentials, and agent tools. Trace removed safeguards through callers and history, and search for variants of confirmed defects.
1. **Verify proportionately**: establish findings with source evidence, focused tests, or safe experiments. A read-only review does not automatically require tests or a build. Reuse passing results while relevant inputs remain unchanged; run a full gate only for explicit qualification, repository requirements, or cross-cutting risk. Isolate write-formatting checks when unrelated work is present.
1. **Report findings**: rank actionable defects using the scale below. Give the exact location, reachable trigger, evidence, impact, and smallest correction. Discard preferences and speculation; if none are material, say so. Summarize candidate identity, checks actually run, and remaining limits without expanding validation just to fill a report.

## Severity

- **P0**: immediate security breach, irreversible data loss, or broad outage risk.
- **P1**: likely correctness, security, or availability defect that should block merge.
- **P2**: material edge-case, maintainability, performance, or test defect worth fixing before or soon after merge.
- **P3**: minor issue, reported only when the user asked for an exhaustive review.

## Boundaries

- **Review only**: inspection, bounded validation, and local reports are in scope. Editing code, resolving threads, approving PRs, creating remote issues/comments, deploying, or publishing requires the corresponding authorization.
- **Evidence limits**: distinguish observed defects from risks. Keep scan timeouts, skipped targets, unavailable dependencies, and other material gaps explicit; partial evidence is not full qualification.
- **Live evidence**: inspect only authorized targets. Compare CI, tags, releases, or runtime observations with the exact reviewed revision; never transfer a green result across commits or equate local checks with deployed acceptance.

## Documentation

- Companion skills: [github-pull-request](../github-pull-request/SKILL.md) (acting on review threads), [github-issues](../github-issues/SKILL.md) (findings to issue drafts), [quality-assurance](../quality-assurance/SKILL.md) (test campaigns), [production-readiness](../production-readiness/SKILL.md) (proof ladder and go/no-go), [mise](../mise/SKILL.md) (validation tasks).
