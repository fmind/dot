---
name: implementation-plan
description: "Turn accepted requirements into repository-grounded implementation steps and verification, or challenge a plan through assumptions, failure modes, and trade-offs."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/implementation-plan
  created: "2026-08-08"
  updated: "2026-09-19"
---

# Implementation Plan

Design the smallest sequence of independently verifiable vertical slices that satisfies accepted requirements, or challenge an existing plan before it is executed; implementation follows the accepted scope and applicable stack skills.

## Workflow

To write a plan, follow the steps below. To challenge an existing plan, read only [plan-review](references/plan-review.md); to settle an unfamiliar API or architecture choice first, read [research-brief](references/research-brief.md).

1. **Read the accepted scope**: identify the outcome, constraints, authorization, and unresolved decisions; stop planning when material options still need a user decision.
1. **Inspect the implementation**: verify relevant paths, interfaces, dependencies, tests, and current work; preserve user changes and reuse existing mechanisms.
1. **Choose useful slices**: order the smallest independently verifiable changes by dependency; identify shared files and real compatibility or migration risks.
1. **Specify proof**: each slice names its outcome, affected files, dependencies, implementation steps, focused checks with expected results, and objective acceptance criteria.
1. **Review the plan**: map every requirement to a slice, verify unfamiliar APIs, remove speculative flexibility, and state any decision that truly blocks execution.
1. **Deliver at the right scale**: use a compact task table for linear work; add interface contracts, concurrency, rollout, or rollback details where needed, retaining every applicable risk and proof boundary.
1. **Hand off**: identify the first executable slice and the full project gate; carry existing implementation authorization forward without requesting it again.

## Gotchas

- **Planning is read-only by default**: Do not edit source, create issues, install dependencies, or deploy while planning unless the user explicitly asked.
- **Deletion test**: An abstraction earns its place only when removing it would spread meaningful complexity or violate a real seam; delay a generalized adapter until a second concrete variation exists.
- **Deep modules**: Prefer modules that hide decisions over pass-through layers, and put tests and callers across the same real seam.

## Task guides

<!-- guides:start -->

- [plan-review](references/plan-review.md): Challenge a product or implementation plan: assumptions, failure modes, trade-offs, and a GO or NO-GO verdict.
- [research-brief](references/research-brief.md): Decision-ready research brief for an unfamiliar API or architecture choice: evidence table, options, and proof boundaries.

<!-- guides:end -->

## Documentation

- Adapted from [Superpowers writing-plans](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/writing-plans/SKILL.md), [Spec Kit plan template](https://github.com/github/spec-kit/blob/684b3d8e05263a7c1948d3d0699ab1cb4f77c3d5/templates/plan-template.md), [codebase design](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/codebase-design/SKILL.md), [domain modeling](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/domain-modeling/SKILL.md).
- Companion skills: [python-testing](../python-testing/SKILL.md) (red-green proof), [threat-model](../threat-model/SKILL.md) (security design risk).
