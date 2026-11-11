# Mutation Tests

Run scoped mutation tests as a review probe on security, money, or data-loss boundaries — never as a routine gate or score target.

1. **Isolate**: work in a disposable [git worktree](../../../../git-delivery/references/git-worktree/GUIDE.md) or scratch copy (`mutmut` writes `mutants/` and temp config).
1. **Scope to one module + serial pytest** (no `-n`):
   ```toml
   [tool.mutmut]
   source_paths = ["src/"]
   only_mutate = ["src/<package>/<module>.py"]
   pytest_add_cli_args_test_selection = ["tests/test_<module>.py"]
   ```
   Run `uv run --with 'mutmut==<version>' mutmut run --max-children 2`, then `mutmut results` and `mutmut show <mutant>`.
1. **Triage survivors**: add red-capable tests in the real repo for surviving boundary/boolean/call mutations (ignore message-string or equivalent mutants unless text is contractual), then re-verify.

Sources: [mutmut](https://mutmut.readthedocs.io/en/latest/) · [changelog](https://github.com/boxed/mutmut/blob/main/HISTORY.rst)
