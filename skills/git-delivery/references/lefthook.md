---
name: lefthook
description: "Configure local Lefthook Git hooks via mise tasks."
---

# Lefthook

Thin Git hooks delegating every check to `mise run <task>` so local hooks and CI never drift; Lefthook owns _when_, [mise](../../mise/SKILL.md) owns _what_.

## Workflow

1. **Pin**: declare `lefthook` in `mise.toml` `[tools]` ([Python stack](../../python/references/foundation/GUIDE.md) included), never in language dev dependencies.
1. **Configure**: copy `lefthook.yml` from the [Python](../../python/references/foundation/templates/lefthook.yml), [OpenTofu](../../infra-as-code/templates/lefthook.yml), or [docs](../../docs/references/site/templates/lefthook.yml) template, calling `check:local` and `check:network` ([task conventions](../../mise/references/task-conventions.md#conventions)); if all checks are offline, run `mise run check` in `pre-commit` and omit `check:network`.
1. **Activate**: wire `lefthook install` into `mise run install` and `lefthook validate` into `check:tasks`.

## Principles

- **pre-commit** (fast, offline): format `{staged_files}` (`stage_fixed: true`), run `check:leaks:staged`, then `check:local` (including `check:leaks`).
- **pre-push** (parallel): `test` plus `check:network` (online vulnerability/misconfiguration DBs).
- **post-commit** (optional): rebuild/reinstall local CLI packages when build inputs changed (non-blocking).
- **Delegate only**: every job runs `mise run <task>` with descriptive `name` (`format Python`, `check`, `test`); formatters accept `{staged_files}` via [argument forwarding](../../mise/references/task-conventions.md#conventions) while `check` and `test` inspect the full tree.

## Gotchas

- **Set `glob_matcher: doublestar` at the root of `lefthook.yml`**: required so recursive globs like `**/*.py` and `**/*.{json,md}` match nested files.
- **Prefer `jobs` over legacy `commands`**: `jobs` run sequentially in list order so formatters finish before checks.
- **Partial staging hides unstaged hunks**: Lefthook stashes unstaged hunks during `pre-commit` and restores them afterwards.
- **Scrub Git hook env vars for Git-creating tests**: Git sets `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, and `GIT_OBJECT_DIRECTORY` during hooks, which hijacks tests that initialize temporary Git repos or worktrees unless stripped in test fixtures or the `pre-push` command (`env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_COMMON_DIR -u GIT_OBJECT_DIRECTORY mise run test`).
- **Never pass `--no-verify`**: heal hook failures per [git-add-commit-push](git-add-commit-push.md).

## Documentation

- [Lefthook](https://lefthook.dev) · [Config reference](https://github.com/evilmartians/lefthook/tree/master/docs/configuration) · [releases](https://github.com/evilmartians/lefthook/releases) · [changelog](https://github.com/evilmartians/lefthook/blob/master/CHANGELOG.md)
- Companion skills: [mise](../../mise/SKILL.md), [ci-cd](../../github/references/ci-cd/GUIDE.md), [betterleaks](../../code-security/references/betterleaks.md).
