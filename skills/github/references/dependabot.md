---
name: dependabot
description: "Configure security-only Dependabot alerts and grouped fix PRs."
---

# Dependabot

Use Dependabot strictly for vulnerability alerts and grouped security fix PRs (`open-pull-requests-limit: 0` disables noisy version bumps; [upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md) owns planned upgrades, and [code-security](../../code-security/references/code-review/GUIDE.md) adds `.github/dependabot.yml`).

## Workflow

1. **Enable repository alerts and security updates** (free on public and private repos; included in the [settings baseline](repository/references/settings-baseline.md)):

   ```bash
   gh api -X PUT "repos/$repository/vulnerability-alerts"
   gh api -X PUT "repos/$repository/automated-security-fixes"
   gh api "repos/$repository/automated-security-fixes" --jq .enabled   # expect true
   ```

1. **Write `.github/dependabot.yml`**: copy [dependabot.yml](../templates/dependabot.yml) and add one entry per advisory-backed manifest root (`github-actions`, `uv`, `npm`, `gomod`; use `directory: /` for `.github/workflows` alone, or `directories: ["/", "/.github/actions/**/*"]` whenever local composite actions such as `setup-mise/action.yml` exist). Keeping `open-pull-requests-limit: 0` disables noisy version PRs while preserving `fix(deps)` prefixes and single-PR `security-updates` grouping (`schedule` is schema-required only).

1. **Validate**: run [jactionlint](jactionlint.md) (`--profile pedantic` flags `open-pull-requests-limit: 0` as `dependabot-missing-actions-update`, so set `dependabot-missing-actions-update: off` in `.github/jactionlint.yaml`); GitHub re-validates on push under Insights → Dependency graph → Dependabot.
1. **Verify security PRs locally before merge** (never enable auto-merge):

   ```bash
   gh pr list --app dependabot
   gh pr checkout <number>
   mise run check && mise run test
   ```

## Gotchas

- **Omit ecosystems without advisories**: `docker`, `docker-compose`, `terraform`, and `opentofu` emit no security updates; Trivy and [upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md) cover them.
- **Keep `dependabot.yml`**: deleting it drops `fix(deps)` prefixes and security PR grouping.
- **Omit version-only keys**: skip `cooldown`, `allow.update-types`, and `schedule.day`/`time`.
- **Avoid `allow` and `ignore`**: both filter security updates too and can silently block vulnerability fixes.
- **Check remaining open alerts after merging**: grouped PRs skip conflicting bumps; inspect `gh api --paginate 'repos/OWNER/REPO/dependabot/alerts?state=open&per_page=100'` (omit `-f`, which switches to POST) and bump leftovers manually.
- **Set `directory` per manifest**: Dependabot does not recurse (`dot/` needs `directory: /dot`).
- **Actions coverage scope**: `directory: /` covers only `.github/workflows`; use `directories: ["/", "/.github/actions/**/*"]` whenever local composite actions (like `setup-mise/action.yml`) exist. Workflow templates outside `.github/` get no alerts; update them via [upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md).
- **Enable account-level grouping for unconfigured repos**: toggle "Grouped security updates" in GitHub account/org `security_analysis` settings; configure alert delivery in notification settings.
- **Clear alerts on removed manifests**: if a deleted lockfile fails Dependabot jobs (`<directories> not found`), confirm the active lock is patched and dismiss: `gh api -X PATCH repos/OWNER/REPO/dependabot/alerts/N -f state=dismissed -f dismissed_reason=not_used -f dismissed_comment="Manifest removed; active lock resolves PACKAGE VERSION"`. If reopened, cycle `DELETE` then `PUT` on `vulnerability-alerts` (admin authority) and `PUT` `automated-security-fixes`, confirming `.enabled == true`.
- **Manual re-checks are web-only**: trigger under Insights → Dependency graph → Dependabot.

## Documentation

- [Dependabot](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain) · [Options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) · [Security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates) · [changelog](https://github.blog/changelog/label/supply-chain-security/)
- Companions: [code-security](../../code-security/references/code-review/GUIDE.md), [upgrade-tools](../../mise/references/upgrade-tools/GUIDE.md), [jactionlint](jactionlint.md), [settings baseline](repository/references/settings-baseline.md).
