---
name: jactionlint
description: "Lint and audit GitHub Actions workflows, composite actions, and Dependabot."
---

# jactionlint

Static linter and security auditor scanning `.github/workflows/*.{yml,yaml}`, composite actions (`.github/actions/**/action.{yml,yaml}`), `.github/dependabot.yml`, and `.github/jactionlint.yaml`, wired into `check:actions` by [ci-cd](ci-cd/GUIDE.md).

## Commands

```bash
jactionlint --profile pedantic              # offline gate (check:actions)
jactionlint --format sarif > jactionlint.sarif
jactionlint --online=strict --strict-exit   # scheduled audit: archived/impostor/vulnerable actions; fails on skips
jactionlint --fix                           # mechanical fixes; review diff cleanly
```

## Common Findings and Fixes

| Finding                 | Fix                                                    |
| ----------------------- | ------------------------------------------------------ |
| `template-injection`    | Pass `${{ ... }}` values through `env:`.               |
| `artipacked`            | `persist-credentials: false` unless a step pushes.     |
| `excessive-permissions` | Top-level `contents: read`; widen per job.             |
| `unpinned-uses`         | Full commit SHA plus a release comment.                |
| `cache-poisoning`       | `cache: false` in release and deploy jobs.             |
| `dangerous-triggers`    | No PR code under `pull_request_target`/`workflow_run`. |

## Gotchas

- **Scope rule overrides narrowly**: use `.github/jactionlint.yaml` (`rules:` for deliberate repository-policy conflicts such as `dependabot-missing-actions-update: off` under security-only Dependabot or `action-release-cooldown: off` when [upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades; `ignores:` with `rule`, `file`, `reason` for one-offs) or `# jactionlint ignore=RULE`; never disable `unpinned-uses` globally.
- **`pull_request_target` default block**: starting 2026-12-02, GitHub blocks it by default on public repos; scope any exception to the single workflow file via [event policy](https://docs.github.com/en/actions/how-tos/administer/control-workflow-execution).
- **Keep `--online` out of local/PR gates**: it calls the GitHub API and hits rate limits; reserve for manual audits or scheduled jobs.

## Documentation

- [jactionlint](https://jactionlint.jdx.dev) · [Rules](https://jactionlint.jdx.dev/rules) · [Config](https://jactionlint.jdx.dev/config) · [releases](https://github.com/jdx/jactionlint/releases) · [changelog](https://github.com/jdx/jactionlint/blob/main/CHANGELOG.md)
- Companion skills: [ci-cd](ci-cd/GUIDE.md), [dependabot](dependabot.md), [code-security](../../code-security/references/code-review/GUIDE.md).
