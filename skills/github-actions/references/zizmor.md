---
name: zizmor
description: "Workflow security analysis and finding verification."
---

# Zizmor

Static security audit for `.github/workflows/*.yml` and composite actions; `actionlint` checks correctness, zizmor checks what an attacker could do with the workflow, and [github-actions](ci-cd/GUIDE.md) wires both into `check:actions`.

## Commands

```bash
zizmor --offline .github/workflows/                       # default gate: no network, no token needed
zizmor --offline --min-severity medium .github/           # bound noise in large repositories
zizmor --offline --persona pedantic .github/              # stricter pass before a release
zizmor --offline --format sarif .github/ > zizmor.sarif
zizmor --offline --collect dependabot --strict-collection . # audit .github/dependabot.yml too: schema plus rules such as dependabot-cooldown
GH_TOKEN="$(gh auth token)" zizmor .github/               # online audits (impostor commits, ref confusion)
zizmor --fix .github/workflows/                           # experimental; the default mode applies only safe fixes, review the diff
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

- **Config exceptions**: add narrow, reasoned ignores only when the workflow cannot satisfy a rule; do not relax `unpinned-uses` globally.
- **Offline is the gate**: online audits need `GH_TOKEN` and hit rate limits; keep them for manual reviews.
- **Fix mode edits files**: run it on a clean tree and review every change before committing.

## Documentation

- [zizmor](https://docs.zizmor.sh) · [Audit rules](https://docs.zizmor.sh/audits/)
- Releases: [zizmor release notes](https://docs.zizmor.sh/release-notes/) · [GitHub releases](https://github.com/zizmorcore/zizmor/releases)
- Companion skills: [github-actions](ci-cd/GUIDE.md) (the `check:actions` task), [dependabot](dependabot.md) (`--collect dependabot`), [security-review](../../security-review/references/code-review/GUIDE.md).
