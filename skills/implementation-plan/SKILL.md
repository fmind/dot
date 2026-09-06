---
name: implementation-plan
description: Turn accepted requirements into dependency-ordered, repository-grounded implementation slices. Use before editing cross-system, migration, or rollout-risk work.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/implementation-plan
  created: "2026-08-08"
  updated: "2026-09-06"
---

# Implementation Plan

Design the smallest sequence of independently verifiable vertical slices that satisfies accepted requirements; [plan-review](../plan-review/SKILL.md) challenges the plan and [plan-execution](../plan-execution/SKILL.md) carries it out.

## Workflow

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

## Documentation

- Adapted from [Superpowers writing-plans](https://github.com/obra/superpowers/blob/44c9b2d6e889982ac18c27d05a19fefe335194e1/skills/writing-plans/SKILL.md), [Spec Kit plan template](https://github.com/github/spec-kit/blob/684b3d8e05263a7c1948d3d0699ab1cb4f77c3d5/templates/plan-template.md), [codebase design](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/codebase-design/SKILL.md), [domain modeling](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/domain-modeling/SKILL.md).
- Companion skills: [plan-review](../plan-review/SKILL.md) (challenge the plan), [plan-execution](../plan-execution/SKILL.md) (carry it out), [technical-research](../technical-research/SKILL.md) (verify APIs), [test-driven-development](../test-driven-development/SKILL.md) (red-green proof), [threat-model](../threat-model/SKILL.md) (security design risk).
