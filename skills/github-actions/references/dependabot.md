---
name: dependabot
description: "Security-only dependency updates: alerts plus grouped fix PRs."
---

# Dependabot

Run Dependabot for security only: alerts warn about vulnerable dependencies, and security updates open one grouped fix PR per ecosystem. Version updates stay off because weekly bumps are noise; [upgrade-tools](../../upgrade-tools/SKILL.md) owns deliberate upgrades, including the bumps Dependabot cannot make (mise pins, formatter plugins). [code-security](../../code-security/references/code-review/GUIDE.md) adds the config during the security pass.

## Workflow

1. **Enable alerts and security updates on the repository**: both are free for public and private repositories, and neither needs a token or app. The [settings baseline](../../github-repository/references/settings-baseline.md) runs this for every new repository:

   ```bash
   gh api -X PUT "repos/$repository/vulnerability-alerts"
   gh api -X PUT "repos/$repository/automated-security-fixes"
   gh api "repos/$repository/automated-security-fixes" --jq .enabled   # expect true
   ```

1. **Map the ecosystems**: one `updates` entry per ecosystem the GitHub Advisory Database covers, listing every manifest directory under `directories`, using the value Dependabot expects:

   | Manifest                     | `package-ecosystem` |
   | ---------------------------- | ------------------- |
   | `.github/workflows/*.yml`    | `github-actions`    |
   | `pyproject.toml` + `uv.lock` | `uv`                |
   | `package.json` + lockfile    | `npm`               |
   | `go.mod`                     | `gomod`             |

1. **Write the config**: `open-pull-requests-limit: 0` turns version updates off while security updates keep opening; the `fix(deps)` prefix and the `applies-to: security-updates` group still apply to security PRs, so each ecosystem gets one PR per run instead of one per advisory:

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

1. **Exempt the cooldown audit**: zizmor's `dependabot-cooldown` audit still flags this config, but `cooldown` never applies to security updates and version updates are off. Disable the audit in `.github/zizmor.yml` instead of adding inert `cooldown` blocks:

   ```yaml
   # Docs: https://docs.zizmor.sh/configuration/
   rules:
     # Dependabot runs security updates only, which ignore cooldowns; version updates are off.
     dependabot-cooldown:
       disable: true
   ```

1. **Validate**: `zizmor --offline --collect=dependabot --strict-collection .github/` checks the schema and audits the file offline (see [zizmor](zizmor.md)); GitHub re-validates on push and shows errors in the Dependabot tab.
1. **Review each security PR locally**: it is ready to merge once the gate passes; never merge blindly and never enable auto-merge (unavailable for private repositories on GitHub Free anyway).

   ```bash
   gh pr list --app dependabot    # open Dependabot PRs
   gh pr checkout <number>
   mise run check && mise run test
   ```

## Gotchas

- **Skip ecosystems without advisories**: `docker`, `docker-compose`, `terraform`, and `opentofu` get no security updates, so their entries do nothing once version updates are off; Trivy image scans and [upgrade-tools](../../upgrade-tools/SKILL.md) cover base images and providers.
- **Keep the config file**: deleting `dependabot.yml` also stops version updates, but security PRs then lose the grouping and Conventional Commit prefix.
- **Drop version-update options**: `cooldown`, `allow.update-types`, and `schedule.day`/`time` only shape version updates; leave them out so the file states what runs.
- **Avoid `allow` and `ignore`**: unlike `update-types`, they also filter security updates, so an `ignore` written to hold back a major can silently block its security fix.
- **Pin actions to commit SHAs**: pin every action to a full commit SHA with a trailing release comment; a security update bumps both the SHA and the comment. Routine pin refreshes come from [upgrade-tools](../../upgrade-tools/SKILL.md).
- **Directory is per manifest**: a uv project under `dot/` needs `/dot` in `directories`; Dependabot does not recurse from `/`.
- **Group the repositories without a config**: grouping for repositories with no `dependabot.yml` is the "Grouped security updates" toggle in the account (`https://github.com/settings/security_analysis`) or organization security settings, next to "Enable all" and "Automatically enable for new repositories".
- **Route alerts deliberately**: alert email and web delivery live under the account's notification settings (Dependabot alerts), separate from repository watching.
- **No CLI trigger**: forcing an immediate check happens only in the repository's Dependabot tab (Insights, Dependency graph).

## Documentation

- [Dependabot](https://docs.github.com/en/code-security/dependabot) · [Options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference) · [Configuring security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configuring-dependabot-security-updates)
- Releases: [Dependabot changelog](https://github.blog/changelog/label/dependabot/)
- Companion skills: [code-security](../../code-security/references/code-review/GUIDE.md) (security pass), [upgrade-tools](../../upgrade-tools/SKILL.md) (deliberate upgrades), [zizmor](zizmor.md) (offline validation), [settings baseline](../../github-repository/references/settings-baseline.md) (repository switches).
