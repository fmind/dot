---
name: python-testing
description: "Write Python tests with pytest, fixtures, property tests, and TDD."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-testing
  created: "2026-08-08"
  updated: "2026-10-07"
---

# Python Testing

Prove a change with an honest red-green-refactor cycle: a failing test that detects the missing or broken behavior, then the smallest trustworthy change; [quality-assurance](../quality-assurance/SKILL.md) owns the broader campaign and [systematic-debugging](../systematic-debugging/SKILL.md) owns failures not yet understood.

Test-only maintenance follows [pytest mechanics](references/pytest.md) directly without inventing a production change; use the red-green-refactor workflow below when implementing a behavior change.

## Workflow

1. **State the contract**: Name the production change that would make the test pass and a plausible regression that would make it fail.
1. **RED**: Write one minimal test for one observable behavior; run it and confirm it fails for the missing behavior, not for a syntax, fixture, environment, or setup error.
1. **GREEN**: Implement only enough production code to satisfy that test; run the focused test and read the full output.
1. **Protect the neighborhood**: Run the package or subsystem tests; fix production code when the new behavior breaks a valid existing contract and revisit the spec when contracts conflict.
1. **REFACTOR**: Improve names, structure, duplication, and types only while everything stays green; add no behavior.
1. **Repeat**: Take the next smallest behavior, edge case, or failure path through a new red cycle.
1. **Prove the regression test**: Reuse the observed red result. If implementation preceded the test or its ability to detect the defect remains uncertain, safely exercise the test against the unfixed code in isolation, then confirm green with the fix.
1. **Qualify proportionately**: reuse passing focused and subsystem results while relevant inputs remain unchanged; add affected static checks. Run the full gate only when repository policy or cross-cutting risk requires it. Apply the [dirty-tree rule](../mise/SKILL.md#gotchas) when unrelated work is present.
1. **Report evidence**: summarize the observed red and green outcomes, checks actually run, and remaining limits; name every failure observed, including pre-existing ones. Do not run additional suites merely to fill the report.

## Gotchas

- **Never weaken an existing test**: do not loosen a type, add a skip, or mock away the defect to manufacture green.
- **Preserve code written before tests**: Never delete or overwrite user work because it preceded the test; preserve it, add a red-capable test, and disclose the sequence.
- **Disclose when test-first does not fit**: For a spike, generated code, or configuration-only change, say why and define another failing validation signal; do not call tests written afterward TDD.
- **Prefer real collaborators over mocks**: Prefer real parsers, databases, filesystems, and HTTP handlers at lightweight boundaries over mocks of the unit under test; fake only paid, destructive, slow, or unreliable systems behind a narrow owned interface.

## References

- [pytest mechanics](references/pytest.md): read for fixture, collection, assertion, async-mode, xdist, plugin, or coverage maintenance.
- [Property tests](references/property-tests.md): read when parsers, codecs, migrations, or state transitions need generated input coverage; use `uv` for project test dependencies.

## Documentation

- Adapted from [Superpowers test-driven-development](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/test-driven-development/SKILL.md), [agent-skills test-driven-development](https://github.com/addyosmani/agent-skills/blob/d2478bf0c73a6357df39a3ed6aff16acaa218843/skills/test-driven-development/SKILL.md).
- Releases: [pytest changelog](https://docs.pytest.org/en/stable/changelog.html)
- Companion skills: [implementation-plan](../implementation-plan/SKILL.md) (planned slices), [mise](../mise/SKILL.md) (task vocabulary).
