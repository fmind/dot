---
name: lefthook
description: "Local Git hooks aligned with repository tasks."
---

# Lefthook

Thin git hooks that delegate every command to a `mise run` task so hooks and CI run identical checks; lefthook decides _when_, [mise](../../mise/SKILL.md) owns _what_.

## Workflow

1. **Install**: pin `lefthook` in the repository's mise `[tools]`, Python projects included ([Python stack](../../python-stack/references/foundation/GUIDE.md)); never duplicate it in a package manager's dev dependencies.
1. **Configure**: create `lefthook.yml` at the repository root from the stack-neutral template below; Python adds the `sort Python imports` and `format Python` jobs from the [python-stack template](../../python-stack/references/foundation/templates/lefthook.yml). The template calls the `check:local` and `check:network` tasks from the [task conventions](../../mise/references/task-conventions.md#conventions); a repository whose checks all run offline (no `check:network`) runs `mise run check` in pre-commit and drops the `scan vulnerabilities` job.
1. **Activate**: `lefthook install`, wired into `mise run install`.

## Template

```yaml
# Docs: https://lefthook.dev/configuration/

# Jobs run in list order: formatters fix and restage only the staged files, then checks validate the tree.
pre-commit:
  jobs:
    - name: format docs and config
      glob: "*.{json,md,toml,yaml,yml}"
      run: mise run format:dprint {staged_files}
      stage_fixed: true
    - name: check
      run: mise run check:local
pre-push:
  parallel: true
  jobs:
    # Vulnerability and misconfiguration databases need the network; CI runs both through `check`.
    - name: scan vulnerabilities
      run: mise run check:network
    - name: test
      run: mise run test
```

## Principles

- **pre-commit** (fast, offline): format staged files, then `check:local`, including the working-tree secret scan.
- **pre-push** (slower): the test suite and `check:network` in parallel; vulnerability and misconfiguration databases need the network, so an offline commit still works.
- **post-commit** (optional): rebuild and reinstall a Python application from the repository's own package, guarded to commits that touch a build input; git ignores its exit status, so it never blocks a commit.
- **Delegate, don't duplicate**: every job runs `mise run <task>`; never inline tool commands. Name each job for what it does (`format Python`, `check`, `test`); the `run` line already names the task.
- **Staged formatters, whole-tree checks**: formatters take `{staged_files}` and restage fixes with `stage_fixed: true`; `check` and `test` take no files. The same formatter task serves hooks and `mise run format` ([argument forwarding](../../mise/references/task-conventions.md#conventions)).

## Gotchas

- **Use a `jobs` list**: jobs run sequentially in list order, so formatters precede checks; the legacy `commands` map needs `parallel: false` and a `priority` on every command to get the same order.
- **Formatters see only staged hunks**: during pre-commit lefthook hides the unstaged hunks of partially staged files and restores them afterwards, so formatters only see what is being committed.
- **Avoid `--no-verify`**: fix the failure instead — [git-add-commit-push](../../git-delivery/references/git-add-commit-push.md) heals hook failures.

## Documentation

- [Lefthook](https://lefthook.dev) · [Configuration reference](https://github.com/evilmartians/lefthook/tree/master/docs/configuration)
- Releases: [Lefthook](https://github.com/evilmartians/lefthook/releases) · [changelog](https://github.com/evilmartians/lefthook/blob/master/CHANGELOG.md)
- Companion skills: [mise](../../mise/SKILL.md) (task owner), [github-actions](ci-cd/GUIDE.md) (CI runs the same tasks), [betterleaks](../../code-security/references/betterleaks.md) (`check:leaks`).
