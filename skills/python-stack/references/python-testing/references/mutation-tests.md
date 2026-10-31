# Mutation Tests

Use scoped mutation testing as a review probe when a security, money, or data-loss boundary depends on a module's tests, or when the user asks for proof that tests catch regressions; never as a gate or a score to optimize.

1. **Work in a disposable copy**: use a [git worktree](../../../../git-delivery/references/git-worktree/GUIDE.md) or scratch copy; mutmut writes a `mutants/` tree and needs temporary configuration that must not reach the project.
1. **Scope to the changed module and its tests**: add to the copy's `pyproject.toml`, keeping `-n` out of pytest arguments:

   ```toml
   [tool.mutmut]
   source_paths = ["src/"]
   only_mutate = ["src/<package>/<module>.py"]
   pytest_add_cli_args_test_selection = ["tests/test_<module>.py"]
   ```

   Run `uv run --with 'mutmut==<version>' mutmut run --max-children 2`, then `uv run --with 'mutmut==<version>' mutmut results` and `uv run --with 'mutmut==<version>' mutmut show <mutant>`.
1. **Triage survivors by meaning**: a surviving comparison boundary, boolean operator, or dropped call is a missing test; changed message strings and equivalent mutants are noise unless the text is the contract. Add a red-capable test for each real gap in the project, then rerun that mutant in the copy.

Sources: [mutmut](https://mutmut.readthedocs.io/en/latest/) · [changelog](https://github.com/boxed/mutmut/blob/main/HISTORY.rst)
