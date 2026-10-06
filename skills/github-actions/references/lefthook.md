---
name: lefthook
description: "Local Git hooks aligned with repository tasks."
---

# Lefthook

Thin git hooks that delegate every command to a `mise run` task so hooks and CI run identical checks; lefthook decides _when_, [mise](../../mise/SKILL.md) owns _what_.

## Workflow

1. **Install**: pin `lefthook` in the repository's mise `[tools]`, Python projects included ([Python stack](../../python-stack/references/foundation/GUIDE.md)); never duplicate it in a package manager's dev dependencies.
1. **Configure**: create `lefthook.yml` at the repository root from the stack-neutral template below; Python adds the `format:imports` (priority 10) and `format:ruff` (15) hooks from the [python-stack template](../../python-stack/references/foundation/templates/lefthook.yml).
1. **Activate**: `lefthook install`, wired into `mise run install`.

## Template

```yaml
output: [summary, failure, execution_out] # quiet commits: no version banner, no successful-step noise
pre-commit:
  parallel: false
  commands:
    format:dprint:
      glob: "*.{json,md,toml,yaml,yml}"
      priority: 10
      run: mise run format:dprint {staged_files}
      stage_fixed: true
    check:
      priority: 30
      run: mise run check
pre-push:
  commands:
    test:
      run: mise run test
```

## Principles

- **pre-commit** (fast): format staged files, then the static checks, including the working-tree secret scan.
- **pre-push** (slower): the test suite.
- **post-commit** (optional): rebuild and reinstall a Python application from the repository's own package, guarded to commits that touch a build input; git ignores its exit status, so it never blocks a commit.
- **Delegate, don't duplicate**: every command is `mise run <task>` and its name mirrors the task; never inline tool commands.
- **Staged formatters, whole-tree checks**: formatters take `{staged_files}` and restage fixes with `stage_fixed: true`; `check` and `test` take no files.

## Gotchas

- **Set a priority on every command**: with `parallel: false`, commands run by ascending `priority` (`10` imports/config, `15` Python formatting, `30` `check`); commands without a priority run last in unspecified order, so set it on every command.
- **Formatters see only staged hunks**: during pre-commit lefthook hides the unstaged hunks of partially staged files and restores them afterwards, so formatters only see what is being committed.
- **Avoid `--no-verify`**: fix the failure instead — [git-add-commit-push](../../git-delivery/references/git-add-commit-push.md) heals hook failures.

## Documentation

- [Lefthook](https://lefthook.dev) · [Configuration reference](https://github.com/evilmartians/lefthook/tree/master/docs/configuration)
- Releases: [Lefthook](https://github.com/evilmartians/lefthook/releases) · [changelog](https://github.com/evilmartians/lefthook/blob/master/CHANGELOG.md)
- Companion skills: [mise](../../mise/SKILL.md) (task owner), [github-actions](ci-cd/GUIDE.md) (CI runs the same tasks), [gitleaks](../../code-security/references/gitleaks.md) (`check:leaks`).
