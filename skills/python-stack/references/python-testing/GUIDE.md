---
name: python-testing
description: "Write Python tests with pytest, fixtures, property and mutation tests, and TDD."
---

# Python Testing

Prove a change with an honest red-green-refactor cycle: a failing test that detects the missing or broken behavior, then the smallest trustworthy change; [quality-assurance](../../../quality-assurance/SKILL.md) owns the broader campaign and [systematic-debugging](../../../systematic-debugging/SKILL.md) owns failures not yet understood.

Test-only maintenance follows [pytest mechanics](references/pytest.md) directly without inventing a production change; use the red-green-refactor workflow below when implementing a behavior change.

## Workflow

1. **State the contract**: Name the production change that would make the test pass and a plausible regression that would make it fail.
1. **RED**: Write one minimal test for one observable behavior; run it and confirm it fails for the missing behavior, not for a syntax, fixture, environment, or setup error.
1. **GREEN**: Implement only enough production code to satisfy that test; run the focused test and read the full output.
1. **Protect the neighborhood**: Run the package or subsystem tests; fix production code when the new behavior breaks a valid existing contract and revisit the spec when contracts conflict.
1. **REFACTOR**: Improve names, structure, duplication, and types only while everything stays green; add no behavior.
1. **Repeat**: Take the next smallest behavior, edge case, or failure path through a new red cycle.
1. **Prove the regression test**: Reuse the observed red result. If implementation preceded the test or its ability to detect the defect remains uncertain, safely exercise the test against the unfixed code in isolation, then confirm green with the fix; for a critical boundary, run [mutation tests](references/mutation-tests.md).
1. **Qualify proportionately**: reuse passing focused and subsystem results while relevant inputs remain unchanged; add affected static checks. Run the full gate only when repository policy or cross-cutting risk requires it. Apply the [dirty-tree rule](../../../mise/SKILL.md#gotchas) when unrelated work is present.
1. **Audit the test diff**: list weakening candidates with `git diff -U0 <base> -- '*.py' '*.toml' | rg -s -e '^-\s*assert\b' -e '^-.*match=' -e '^\+.*(\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\[|type: ignore|fail_under|filterwarnings|deselect|omit|exclude_also|baseline)'` and, for untracked files, `git ls-files -o --exclude-standard -- '*.py' | xargs -r rg -s -nH '\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\['`; explain every hit in the report. With fresh coverage data, list changed lines no test executes: `uv run --locked coverage xml -q --fail-under=0 -o .cache/coverage.xml && uvx --from 'diff-cover==<version>' diff-cover .cache/coverage.xml --compare-branch=<base> --include-untracked`. Hits are review evidence, never a gate.
1. **Report evidence**: summarize the observed red and green outcomes, checks actually run, and remaining limits; name every failure observed, including pre-existing ones. Do not run additional suites merely to fill the report.

## Gotchas

- **Never weaken an existing test**: do not loosen a type or `pytest.raises`, add a skip, lower `fail_under`, add `pragma: no cover`, omit files from coverage, add ty baseline entries (an owner-approved [adoption baseline](../ty.md) only shrinks), or mock away the defect to manufacture green.
- **Preserve code written before tests**: Never delete or overwrite user work because it preceded the test; preserve it, add a red-capable test, and disclose the sequence.
- **Disclose when test-first does not fit**: For a spike, generated code, or configuration-only change, say why and define another failing validation signal; do not call tests written afterward TDD.
- **Prefer real collaborators over mocks**: Prefer real parsers, databases, filesystems, and HTTP handlers at lightweight boundaries over mocks of the unit under test; fake only paid, destructive, slow, or unreliable systems behind a narrow owned interface.
- **Keep routine suites sub-minute**: unit and subsystem tests avoid real sleeps, live network calls, and repeated heavy subprocess startup so `pre-push` and `mise run all` stay fast.

## References

- [pytest mechanics](references/pytest.md): read for fixture, collection, assertion, async-mode, xdist, plugin, or coverage maintenance.
- [Property tests](references/property-tests.md): read when parsers, codecs, migrations, or state transitions need generated input coverage; use `uv` for project test dependencies.
- [Mutation tests](references/mutation-tests.md): read when a critical module needs proof that its tests detect regressions.

## Documentation

- Adapted from [Superpowers test-driven-development](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/test-driven-development/SKILL.md), [agent-skills test-driven-development](https://github.com/addyosmani/agent-skills/blob/d2478bf0c73a6357df39a3ed6aff16acaa218843/skills/test-driven-development/SKILL.md).
- Releases: [pytest changelog](https://docs.pytest.org/en/stable/changelog.html)
- Companion skills: [implementation-plan](../../../implementation-plan/SKILL.md) (planned slices), [mise](../../../mise/SKILL.md) (task vocabulary).
