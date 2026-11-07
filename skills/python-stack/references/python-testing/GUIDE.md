---
name: python-testing
description: "Write Python tests with pytest, fixtures, property and mutation tests."
---

# Python Testing

Prove a behavior change with a test that fails without it and passes with it. Test-only maintenance follows [pytest mechanics](references/pytest.md) directly. The persona already forbids weakening a test to pass; an owner-approved [ty adoption baseline](../ty.md) only ever shrinks.

## Workflow

1. **Prove the regression test can fail**: reuse the observed red result; when the code came first, run the test against the unfixed code in isolation, then confirm green with the fix. For a critical boundary, run [mutation tests](references/mutation-tests.md).
1. **Audit the test diff**: list weakening candidates with `git diff -U0 <base> -- '*.py' '*.toml' | rg -s -e '^-\s*assert\b' -e '^-.*match=' -e '^\+.*(\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\[|type: ignore|fail_under|filterwarnings|deselect|omit|exclude_also|baseline)'` and, for untracked files, `git ls-files -o --exclude-standard -- '*.py' | xargs -r rg -s -nH '\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\['`; explain every hit in the report.
1. **List untested changed lines**: with fresh coverage data, run `uv run --locked coverage xml -q --fail-under=0 -o .cache/coverage.xml && uvx --from 'diff-cover==<version>' diff-cover .cache/coverage.xml --compare-branch=<base> --include-untracked`. Hits are review evidence, never a gate.

## Gotchas

- **Derive expectations without the code under test**: write expected values as hand-checked literals, never computed by the function or its helpers (a mirror assertion always passes). Skip change detectors that fail only on deliberate edits (a constant's value, message wording); test the behavior that depends on them. Run scripts and assert their effects instead of matching their source text. Build mocks with `create_autospec(..., spec_set=True)` and the full real payload shape.
- **Prefer real collaborators over mocks**: use real parsers, databases, filesystems, and HTTP handlers at lightweight boundaries; fake only paid, destructive, slow, or unreliable systems behind a narrow owned interface.
- **Keep routine suites sub-minute**: unit and subsystem tests avoid real sleeps, live network calls, and repeated heavy subprocess startup so `pre-push` and `mise run all` stay fast.

## References

- [pytest mechanics](references/pytest.md): read for fixture, collection, assertion, async-mode, xdist, plugin, or coverage maintenance.
- [Property tests](references/property-tests.md): read when parsers, codecs, migrations, or state transitions need generated input coverage.
- [Mutation tests](references/mutation-tests.md): read when a critical module needs proof that its tests detect regressions.

## Documentation

- Releases: [pytest changelog](https://docs.pytest.org/en/stable/changelog.html)
- Companion skills: [mise](../../../mise/SKILL.md) (task vocabulary).
