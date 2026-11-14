---
name: lefthook
description: "Local Git hooks aligned with repository tasks."
---

# Lefthook

Thin Git hooks delegating every check to `mise run <task>` so local hooks and CI never drift; Lefthook owns _when_, [mise](../../mise/SKILL.md) owns _what_.

## Workflow

1. **Pin**: declare `lefthook` in `mise.toml` `[tools]` ([Python stack](../../python-stack/references/foundation/GUIDE.md) included), never in language dev dependencies.
1. **Configure**: copy `lefthook.yml` from the [Python](../../python-stack/references/foundation/templates/lefthook.yml) or [OpenTofu](../../infra-as-code/templates/lefthook.yml) template, calling `check:local` and `check:network` ([task conventions](../../mise/references/task-conventions.md#conventions)); if all checks are offline, run `mise run check` in `pre-commit` and omit `check:network`.
1. **Activate**: wire `lefthook install` into `mise run install`.

## Principles

- **pre-commit** (fast, offline): format `{staged_files}` (`stage_fixed: true`), then `check:local` (including `check:leaks`).
- **pre-push** (parallel): `test` plus `check:network` (online vulnerability/misconfiguration DBs).
- **post-commit** (optional): rebuild/reinstall local CLI packages when build inputs changed (non-blocking).
- **Delegate only**: every job runs `mise run <task>` with descriptive `name` (`format Python`, `check`, `test`); formatters accept `{staged_files}` via [argument forwarding](../../mise/references/task-conventions.md#conventions) while `check` and `test` inspect the full tree.

## Gotchas

- **Set `glob_matcher: doublestar` at the root of `lefthook.yml`**: required so recursive globs like `**/*.py` and `**/*.{json,md}` match nested files.
- **Prefer `jobs` over legacy `commands`**: `jobs` run sequentially in list order so formatters finish before checks.
- **Partial staging hides unstaged hunks**: Lefthook stashes unstaged hunks during `pre-commit` and restores them afterwards.
- **Never pass `--no-verify`**: heal hook failures per [git-add-commit-push](../../git-delivery/references/git-add-commit-push.md).

## Documentation

- [Lefthook](https://lefthook.dev) · [Config reference](https://github.com/evilmartians/lefthook/tree/master/docs/configuration) · [releases](https://github.com/evilmartians/lefthook/releases) · [changelog](https://github.com/evilmartians/lefthook/blob/master/CHANGELOG.md)
- Companion skills: [mise](../../mise/SKILL.md), [ci-cd](ci-cd/GUIDE.md), [betterleaks](../../code-security/references/betterleaks.md).
