---
name: python-testing
description: "Write Python tests with pytest, fixtures, property and mutation tests."
---

# Python Testing

Prove behavior changes with tests that fail before the fix and pass with it (for test-only maintenance, read [pytest mechanics](references/pytest.md) directly). Approved [ty baselines](../foundation/GUIDE.md#ty) only ever shrink.

## Workflow

1. **Confirm red -> green**: verify the test fails against unfixed code, then passes with the fix; run scoped mutation tests (`#mutation-tests`) on critical boundaries.
1. **Audit test diffs for weakening**: run `git diff -U0 <base> -- '*.py' '*.toml' | rg -s -e '^-\s*assert\b' -e '^-.*match=' -e '^\+.*(\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\[|type: ignore|fail_under|filterwarnings|deselect|omit|exclude_also|baseline)'` and `git ls-files -o --exclude-standard -- '*.py' | xargs -r rg -s -nH '\bskip(if)?\b|xfail|pragma: no cover|noqa|ignore\['`, explaining every hit.
1. **Check changed-line coverage** (review evidence, not a gate): `uv run --locked coverage xml -q --fail-under=0 -o .cache/coverage.xml && uvx --from 'diff-cover==<version>' diff-cover .cache/coverage.xml --compare-branch=<base> --include-untracked`.

## Gotchas

- **Hand-checked expectations**: use literal expected values (never recomputed by the system under test), assert observable behavior rather than source text or wording constants, and type-check mocks via `create_autospec(..., spec_set=True)`.
- **Real collaborators first**: use real parsers, temp dirs, SQLite/in-memory stores, and `MockTransport`; fake only paid, destructive, slow, or flaky external systems behind narrow owned interfaces.
- **Sub-minute suites**: avoid sleeps, live network calls, and repeated cold subprocesses in unit tests.

## References & Docs

- [pytest mechanics](references/pytest.md) · [Property tests](references/property-tests.md) · [pytest changelog](https://docs.pytest.org/en/stable/changelog.html) · [mise](../../../mise/SKILL.md).

## Mutation Tests

Run scoped `mutmut` probes on security, money, or data-loss boundaries — never as a routine gate or score target:

1. Isolate in a disposable [git worktree](../../../git-delivery/references/git-worktree/GUIDE.md) or scratch copy (`mutmut` writes `mutants/`).
1. Configure `[tool.mutmut]` with `source_paths = ["src/"]`, `only_mutate = ["src/<package>/<module>.py"]`, and `pytest_add_cli_args_test_selection = ["tests/test_<module>.py"]`, then run `uv run --with 'mutmut==<version>' mutmut run --max-children 2`, `mutmut results`, and `mutmut show <mutant>`.
1. Add red-capable tests in the real repo for surviving boundary, boolean, or call mutations (ignore message-string or equivalent mutants unless wording is contractual) ([mutmut](https://mutmut.readthedocs.io/en/latest/) · [changelog](https://github.com/boxed/mutmut/blob/main/HISTORY.rst)).
