---
name: jactionlint
description: "Lint and audit GitHub Actions workflows, composite actions, and Dependabot."
---

# jactionlint

Static correctness linter and security auditor for `.github/workflows/*.yml`, composite actions, and `.github/dependabot.yml`; [github-actions](ci-cd/GUIDE.md) wires it into `check:actions`.

## Commands

```bash
jactionlint                                               # default gate: workflows, composite actions, and dependabot.yml
jactionlint --profile pedantic                            # stricter pass before a release
jactionlint --format sarif > jactionlint.sarif
jactionlint --online                                      # online checks (archived repos, impostor commits, vulnerable actions)
jactionlint --fix                                         # apply safe mechanical fixes; review the diff
```

## Common Findings and Fixes

| Finding                 | Fix                                                                                       |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `template-injection`    | Never expand `${{ ... }}` inside `run:`; pass values through `env:` and read `$VAR`.      |
| `artipacked`            | `actions/checkout` with `persist-credentials: false` unless a later step must push.       |
| `excessive-permissions` | Top-level `permissions: contents: read`; widen per job only (`id-token: write` for OIDC). |
| `unpinned-uses`         | Pin actions to a full commit SHA and retain the release as a trailing review comment.     |
| `cache-poisoning`       | Disable caches (`cache: false`) in release and deploy jobs that produce signed artifacts. |
| `dangerous-triggers`    | Avoid `pull_request_target` and `workflow_run` unless the job never checks out PR code.   |

## Gotchas

- **Add narrow, reasoned ignores**: configure `.github/jactionlint.yaml` (`ignores:` entries with `rule`, `file`, and `reason`) or `# jactionlint ignore=RULE` only when the workflow cannot satisfy a rule; do not relax `unpinned-uses` globally.
- **Expect `pull_request_target` to be blocked on public repositories**: from 2026-12-02 GitHub's default Actions event policy disables it there; allow it only through an event policy scoped to the workflow file that needs it ([control workflow execution](https://docs.github.com/en/actions/how-tos/administer/control-workflow-execution)).
- **Offline is the gate**: `--online` queries the GitHub API and hits rate limits; keep it for manual reviews or a scheduled workflow.
- **Fix mode edits files**: run `--fix` on a clean tree and review every change before committing.

## Documentation

- [jactionlint](https://jactionlint.jdx.dev) · [Rules](https://jactionlint.jdx.dev/rules) · [Configuration](https://jactionlint.jdx.dev/config)
- Releases: [GitHub releases](https://github.com/jdx/jactionlint/releases) · [changelog](https://github.com/jdx/jactionlint/blob/main/CHANGELOG.md)
- Companion skills: [github-actions](ci-cd/GUIDE.md) (the `check:actions` task), [dependabot](dependabot.md), [code-security](../../code-security/references/code-review/GUIDE.md).
