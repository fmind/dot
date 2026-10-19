---
name: settings-baseline
description: "Apply the solo-maintainer merge, feature, secret-scanning, Dependabot, Actions hardening, immutable-release, and default-branch protection baseline idempotently."
---

# Settings Baseline

Use for a new solo-maintained repository or an explicitly requested settings pass, after the root's inspect step and with its `repository` and `args` variables. Preserve an existing team's policy and active wiki/projects/discussions unless their removal was requested. Every step is safe to re-run.

## Workflow

1. **Read current settings** before changing them, and keep this output to compare after the edit:

   ```bash
   settings_fields=deleteBranchOnMerge,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,hasIssuesEnabled,hasProjectsEnabled,hasWikiEnabled,hasDiscussionsEnabled
   gh repo view "$repository" --json "$settings_fields"
   ```

1. **Extend the edit**: append the baseline before the root's single `gh repo edit`. For a new repository, disable unused sidebar features with `--enable-wiki=false --enable-projects=false --enable-discussions=false`; on an existing repository, add each flag only when that feature's removal was requested. Add `--enable-issues=false` only when the project tracks issues elsewhere. Add the two secret-scanning flags only for a public repository or when `security_and_analysis.secret_scanning` is present; otherwise report that the capability is unavailable and continue with the remaining settings:

   ```bash
   repository_json="$(gh api "repos/$repository")"
   args+=(
     --delete-branch-on-merge --enable-squash-merge
     --squash-merge-commit-message pr-title-description
     --enable-merge-commit=false --enable-rebase-merge=false --allow-update-branch
   )
   if [[ "$(jq -r .visibility <<<"$repository_json")" == public ]] ||
     [[ "$(jq -r '.security_and_analysis.secret_scanning.status? // empty' <<<"$repository_json")" ]]; then
     args+=(--enable-secret-scanning --enable-secret-scanning-push-protection)
   else
     echo "Secret scanning is unavailable for $repository; leaving it unchanged." >&2
   fi
   ```

1. **Enable Dependabot security updates** on every repository, public or private (free on every plan): alerts warn about vulnerable dependencies and security updates open the fix PRs; the [dependabot](../../github-actions/references/dependabot.md) config keeps version updates off and groups the fixes:

   ```bash
   gh api -X PUT "repos/$repository/vulnerability-alerts"
   gh api -X PUT "repos/$repository/automated-security-fixes"
   ```

1. **Harden Actions** when Actions is enabled; leave a repository with Actions off untouched, because this endpoint's `enabled` field would switch it on. Require full-SHA action pins only after every `uses:` in `.github/workflows` and `.github/actions` is pinned ([zizmor](../../github-actions/references/zizmor.md) `unpinned-uses`), or the next run fails; GitHub-managed workflows (CodeQL, Dependabot, dependency graph, legacy Pages builds) keep working. Keep the default `GITHUB_TOKEN` read-only, and on a public repository require approval for every outside contributor's pull request run:

   ```bash
   actions="$(gh api "repos/$repository/actions/permissions")"
   if [[ "$(jq -r .enabled <<<"$actions")" == true ]]; then
     jq '{enabled: true, allowed_actions, sha_pinning_required: true}' <<<"$actions" |
       gh api -X PUT "repos/$repository/actions/permissions" --input -
     gh api -X PUT "repos/$repository/actions/permissions/workflow" \
       -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
     if [[ "$(jq -r .visibility <<<"$repository_json")" == public ]]; then
       gh api -X PUT "repos/$repository/actions/permissions/fork-pr-contributor-approval" \
         -f approval_policy=all_external_contributors
     fi
   fi
   ```

1. **Lock releases** of a public repository that publishes GitHub releases: immutable releases freeze each published release's tag and assets and add a release attestation, so a release workflow must attach every asset before publishing (`gh release create` with its files, or a draft published last). Restrict each publishing environment, such as `pypi`, to the release tags so only a tag push can publish:

   ```bash
   gh api -X PUT "repos/$repository/immutable-releases"
   for env in $(gh api "repos/$repository/environments" --jq '.environments[].name | select(. == "pypi" or . == "release")'); do
     jq -n '{deployment_branch_policy: {protected_branches: false, custom_branch_policies: true}}' |
       gh api -X PUT "repos/$repository/environments/$env" --input - >/dev/null
     gh api "repos/$repository/environments/$env/deployment-branch-policies" \
       --jq '.branch_policies[] | select(.type == "tag") | .name' | grep -qx 'v\*' ||
       gh api -X POST "repos/$repository/environments/$env/deployment-branch-policies" -f name='v*' -f type=tag
   done
   ```

1. **Protect a public repository** after the edit: enable private vulnerability reporting and keep exactly one repository ruleset, `Protect default branch`, that blocks deletion and force pushes without requiring pull requests or signatures, so direct pushes keep working. Look it up by name and update it in place; create it only when it is absent and no other ruleset already enforces both rules. Duplicates left by earlier runs stop the step: report their IDs and delete extras only with the user's approval.

   ```bash
   set -euo pipefail
   branch="$(gh repo view "$repository" --json defaultBranchRef --jq .defaultBranchRef.name)"
   ruleset='{"name": "Protect default branch", "target": "branch", "enforcement": "active",
     "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
     "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}], "bypass_actors": []}'
   ids="$(gh api --paginate "repos/$repository/rulesets?includes_parents=false" \
     --jq '.[] | select(.name == "Protect default branch") | .id')"
   if (( $(wc -w <<<"$ids") > 1 )); then
     echo "Duplicate 'Protect default branch' rulesets: $ids; resolve before editing." >&2
     exit 1
   fi
   # A failing read inside an if/elif condition would bypass errexit and trigger creation.
   protected="$(gh api "repos/$repository/rules/branches/$branch" \
     --jq '[.[].type] | contains(["deletion", "non_fast_forward"])')"
   gh api -X PUT "repos/$repository/private-vulnerability-reporting"   # the owner's .github SECURITY.md points reporters here
   if [[ -n "$ids" ]]; then
     gh api -X PUT "repos/$repository/rulesets/$ids" --input - --jq .id <<<"$ruleset"
   elif [[ "$protected" == true ]]; then
     echo "Another ruleset already blocks deletion and force pushes on $branch."
   else
     gh api -X POST "repos/$repository/rulesets" --input - --jq .id <<<"$ruleset"
   fi
   ```

1. **Read back** what the edit changed: repeat the settings read, then query the update-branch, squash-message, and security state that `gh repo view` omits. Only for a public repository, verify the protection step as well: expect `deletion` and `non_fast_forward` among the effective branch rules and `true` for vulnerability reporting. Private repositories skip these public-baseline checks, including APIs their plan may not support:

   ```bash
   gh repo view "$repository" --json "$settings_fields"
   gh api "repos/$repository" \
     --jq '{allow_update_branch, squash_merge_commit_title, squash_merge_commit_message, security_and_analysis}'
   gh api "repos/$repository/automated-security-fixes" --jq .enabled   # expect true
   gh api "repos/$repository/actions/permissions" --jq '{enabled, sha_pinning_required}'
   gh api "repos/$repository/actions/permissions/workflow" --jq .default_workflow_permissions   # expect read
   if [[ "$(jq -r .visibility <<<"$repository_json")" == public ]]; then
     gh api "repos/$repository/actions/permissions/fork-pr-contributor-approval" --jq .approval_policy
     gh api "repos/$repository/immutable-releases" --jq .enabled
     gh api "repos/$repository/private-vulnerability-reporting" --jq .enabled
     gh api --paginate "repos/$repository/rulesets?includes_parents=false" --jq '.[] | {id, name, enforcement}'
     gh api "repos/$repository/rules/branches/$branch" --jq 'map(.type)'
   fi
   ```

## Gotchas

- **Detect secret-scanning eligibility**: public repositories are covered; private and internal repositories require an eligible GitHub Secret Protection or Advanced Security entitlement. Capability-detect instead of inferring availability from personal versus organization ownership.
- **Report plan limits as gaps**: rulesets and branch protection on a private repository need GitHub Pro or Team; on Free the API answers 403 `Upgrade to GitHub Pro`. Report the gap instead of changing visibility. Private vulnerability reporting applies to public repositories only.
- **Edit only the owned ruleset**: `rules/branches/<branch>` merges organization and repository rulesets; edit only the repository ruleset this guide owns, and never a parent organization's.
- **Expect silent no-ops on Free**: secret-scanning validity checks and non-provider patterns stay `disabled` after a PATCH on a public repository without an error; they need GitHub Secret Protection. Do not retry them.
- **Rely on the owner's default security policy**: the public `fmind/.github` and `MLOps-Courses/.github` repositories supply `SECURITY.md` to every public repository without one; add a repository file only for a product-specific scope or supported-versions policy.
- **Grant personal-repository access as write or nothing**: a repository owned by a user account has no read-only collaborator role (the API answers 422), so remove an inactive collaborator instead of downgrading; organization repositories accept `pull`.
- **Apply organization settings once**: for `fmind-ai` and `MLOps-Courses`, require 2FA and SHA-pinned actions and set the "GitHub recommended" code security configuration as the default for new repositories at the organization level; those endpoints need the `admin:org` scope, and the 2FA requirement is a web setting.

## Documentation

- [Repository rulesets API](https://docs.github.com/en/rest/repos/rules) · [Dependabot security updates API](https://docs.github.com/en/rest/repos/repos#enable-dependabot-security-updates) · [Private vulnerability reporting API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository)
- [Actions permissions API](https://docs.github.com/en/rest/actions/permissions) · [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases) · [Default community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
