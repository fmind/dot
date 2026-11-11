---
name: dependabot
description: "Security-only dependency updates: alerts plus grouped fix PRs."
---

# Dependabot

Use Dependabot strictly for vulnerability alerts and grouped security fix PRs (`open-pull-requests-limit: 0` disables noisy version bumps; [upgrade-tools](../../upgrade-tools/SKILL.md) owns planned upgrades, and [code-security](../../code-security/references/code-review/GUIDE.md) adds `.github/dependabot.yml`).

## Workflow

1. **Enable repository alerts and security updates** (free on public and private repos; included in the [settings baseline](../../gh/references/repository/references/settings-baseline.md)):

   ```bash
   gh api -X PUT "repos/$repository/vulnerability-alerts"
   gh api -X PUT "repos/$repository/automated-security-fixes"
   gh api "repos/$repository/automated-security-fixes" --jq .enabled   # expect true
   ```

1. **Map advisory-backed ecosystems** (`directory` for one manifest root, `directories` for multiple):

   | Manifest                     | `package-ecosystem` |
   | ---------------------------- | ------------------- |
   | `.github/workflows/*.yml`    | `github-actions`    |
   | `pyproject.toml` + `uv.lock` | `uv`                |
   | `package.json` + lockfile    | `npm`               |
   | `go.mod`                     | `gomod`             |

1. **Write `.github/dependabot.yml`**: `open-pull-requests-limit: 0` disables version PRs while preserving `fix(deps)` prefixes and single-PR `security-updates` grouping:

   ```yaml
   # Docs: https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference
   # Security updates only: `open-pull-requests-limit: 0` disables version updates, while
   # Dependabot still opens one grouped fix PR per ecosystem when an alert has a patched
   # release. `schedule` is required by the schema; it only paces the disabled version updates.
   version: 2
   updates:
     - package-ecosystem: github-actions
       directory: /
       schedule:
         interval: weekly
       open-pull-requests-limit: 0
       commit-message:
         prefix: "fix(deps)"
       groups:
         actions-security:
           applies-to: security-updates
           patterns: ["*"]
     - package-ecosystem: uv
       directory: /
       schedule:
         interval: weekly
       open-pull-requests-limit: 0
       commit-message:
         prefix: "fix(deps)"
       groups:
         python-security:
           applies-to: security-updates
           patterns: ["*"]
   ```

1. **Validate**: run [jactionlint](jactionlint.md) (`--profile pedantic` flags `open-pull-requests-limit: 0` as `dependabot-missing-actions-update`, so set `dependabot-missing-actions-update: off` in `.github/jactionlint.yaml`); GitHub re-validates on push under Insights → Dependency graph → Dependabot.
1. **Verify security PRs locally before merge** (never enable auto-merge):

   ```bash
   gh pr list --app dependabot
   gh pr checkout <number>
   mise run check && mise run test
   ```

## Gotchas

- **Omit ecosystems without advisories**: `docker`, `docker-compose`, `terraform`, and `opentofu` emit no security updates; Trivy and [upgrade-tools](../../upgrade-tools/SKILL.md) cover them.
- **Keep `dependabot.yml`**: deleting it drops `fix(deps)` prefixes and security PR grouping.
- **Omit version-only keys**: skip `cooldown`, `allow.update-types`, and `schedule.day`/`time`.
- **Avoid `allow` and `ignore`**: both filter security updates too and can silently block vulnerability fixes.
- **Check remaining open alerts after merging**: grouped PRs skip conflicting bumps; inspect `gh api --paginate 'repos/OWNER/REPO/dependabot/alerts?state=open&per_page=100'` (omit `-f`, which switches to POST) and bump leftovers manually.
- **Set `directory` per manifest**: Dependabot does not recurse (`dot/` needs `directory: /dot`).
- **Only `.github/workflows` is graphed for Actions**: workflow templates elsewhere get no alerts; update them via [upgrade-tools](../../upgrade-tools/SKILL.md).
- **Enable account-level grouping for unconfigured repos**: toggle "Grouped security updates" in `https://github.com/settings/security_analysis` or org security settings; configure alert delivery separately under account notification settings.
- **Clear alerts on removed manifests**: if a deleted lockfile path keeps failing Dependabot jobs (`<directories> not found`), verify the active lock has a patched version and dismiss: `gh api -X PATCH repos/OWNER/REPO/dependabot/alerts/N -f state=dismissed -f dismissed_reason=not_used -f dismissed_comment="Manifest removed; current lock resolves PACKAGE VERSION"`. If the dependency graph reopens them, cycle `gh api -X DELETE repos/OWNER/REPO/vulnerability-alerts` (requires admin authority; briefly disables the graph) followed by `PUT` on `vulnerability-alerts` and `automated-security-fixes`, then confirm `.enabled == true`.
- **Manual re-checks are web-only**: trigger under Insights → Dependency graph → Dependabot.

## Documentation

- [Dependabot](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain) · [Options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) · [Security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates) · [changelog](https://github.blog/changelog/label/supply-chain-security/)
- Companion skills: [code-security](../../code-security/references/code-review/GUIDE.md), [upgrade-tools](../../upgrade-tools/SKILL.md), [jactionlint](jactionlint.md), [settings baseline](../../gh/references/repository/references/settings-baseline.md).
