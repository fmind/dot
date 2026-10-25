---
name: settings-baseline
description: "Apply or check the solo-maintainer merge, feature, secret-scanning, Dependabot, Actions, immutable-release, and branch-protection baseline with one script."
---

# Settings Baseline

Use for a new solo-maintained repository or an explicitly requested settings pass; preserve an existing team's policy and active wiki/projects/discussions unless their removal was requested. [settings_baseline.py](../scripts/settings_baseline.py) reads the repository with GET requests only, applies every applicable setting idempotently, and prints a JSON read-back, so no shell state has to survive between tool calls. Every run is safe to repeat.

## Workflow

1. **Choose the judgment flags**; the script detects everything else from the repository's state:
   - `--disable wiki --disable projects --disable discussions` for a new repository; on an existing one, pass each only when that feature's removal was requested. Add `--disable issues` only when the project tracks issues elsewhere.
   - `--skip-sha-pinning` while any `uses:` in `.github/workflows` or `.github/actions` is unpinned ([zizmor](../../github-actions/references/zizmor.md) `unpinned-uses`), because requiring full-SHA pins first fails the next run; GitHub-managed workflows (CodeQL, Dependabot, dependency graph, legacy Pages builds) keep working.
1. **Preview** with `--check`, which sends GET requests only and changes nothing:

   ```bash
   python -I ~/.agents/skills/github-repository/scripts/settings_baseline.py OWNER/REPO --check
   ```

1. **Apply** with the chosen flags; a failed read or duplicate rulesets stop the run before any change:

   ```bash
   python -I ~/.agents/skills/github-repository/scripts/settings_baseline.py OWNER/REPO --disable wiki --disable projects --disable discussions
   ```

1. **Report the read-back**: stdout is JSON with `state`, `changed` (apply only, as before and after values), `notes` (settings left unchanged and why), and `drift` (expected values not met). Exit `0` means no drift; `1` means a failed `gh` call (its error stays on stderr), duplicate rulesets, or drift; `2` means invalid arguments. Pass the same flags to a later `--check`, and rerun it once if a just-applied value lags.

## Decisions

| Setting                                                                                  | Applied when                                                                                                  |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Squash-only merges titled and described by the PR, deleted head branches, branch updates | Always                                                                                                        |
| Secret scanning and push protection                                                      | Public, or `security_and_analysis.secret_scanning` present; otherwise a note                                  |
| Dependabot alerts and security updates                                                   | Always (free on every plan); [dependabot](../../github-actions/references/dependabot.md) owns the config file |
| Full-SHA action pins, read-only `GITHUB_TOKEN`, no pull request approvals by Actions     | Actions enabled; the permissions endpoint's `enabled` field would switch it on                                |
| Approval for every outside contributor's pull request run                                | Public, Actions enabled                                                                                       |
| Immutable releases; `pypi` and `release` environments limited to `v*` tags               | Public with a GitHub release or one of those environments                                                     |
| Private vulnerability reporting; one `Protect default branch` ruleset                    | Public                                                                                                        |

- **Attach release assets before publishing**: immutable releases freeze each published release's tag and assets and add a release attestation, so a release workflow uploads every asset at creation (`gh release create` with its files, or a draft published last). A new repository without a release or publishing environment gets them on the rerun after its first release.
- **Keep environment reviewers**: an environment PUT replaces its settings, so the script carries required reviewers, self-review prevention, and the wait timer forward before restricting deployments to release tags.
- **Keep direct pushes working**: the ruleset blocks deletion and force pushes without requiring pull requests or signatures. The script updates it in place by name and creates it only when absent and no other ruleset already enforces both rules; duplicates left by earlier runs stop it with their IDs, and extras are deleted only with the user's approval.

## Gotchas

- **Detect secret-scanning eligibility**: public repositories are covered; private and internal repositories require an eligible GitHub Secret Protection or Advanced Security entitlement. Capability-detect instead of inferring availability from personal versus organization ownership.
- **Report plan limits as gaps**: rulesets and branch protection on a private repository need GitHub Pro or Team; on Free the API answers 403 `Upgrade to GitHub Pro`, so the script skips public-only settings on private repositories. Report the gap instead of changing visibility. Private vulnerability reporting applies to public repositories only.
- **Edit only the owned ruleset**: `rules/branches/<branch>` merges organization and repository rulesets; edit only the repository ruleset this guide owns, and never a parent organization's.
- **Expect silent no-ops on Free**: secret-scanning validity checks and non-provider patterns stay `disabled` after a PATCH on a public repository without an error; they need GitHub Secret Protection. Do not retry them.
- **Rely on the owner's default security policy**: the public `fmind/.github` and `MLOps-Courses/.github` repositories supply `SECURITY.md` to every public repository without one, and point reporters to private vulnerability reporting; add a repository file only for a product-specific scope or supported-versions policy.
- **Grant personal-repository access as write or nothing**: a repository owned by a user account has no read-only collaborator role (the API answers 422), so remove an inactive collaborator instead of downgrading; organization repositories accept `pull`.
- **Apply organization settings once**: for `fmind-ai` and `MLOps-Courses`, require 2FA and SHA-pinned actions and set the "GitHub recommended" code security configuration as the default for new repositories at the organization level; those endpoints need the `admin:org` scope (`dot login github --grant admin:org`, then `dot setup github` to remove it), and the 2FA requirement is a web setting.

## Documentation

- [Repository rulesets API](https://docs.github.com/en/rest/repos/rules) · [Dependabot security updates API](https://docs.github.com/en/rest/repos/repos#enable-dependabot-security-updates) · [Private vulnerability reporting API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository)
- [Actions permissions API](https://docs.github.com/en/rest/actions/permissions) · [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases) · [Default community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
