---
name: settings-baseline
description: "Apply the solo-maintainer merge, feature, secret-scanning, and default-branch protection baseline idempotently."
---

# Settings Baseline

Use for a new solo-maintained repository or an explicitly requested settings pass, after the root's inspect step and with its `repository` and `args` variables. Preserve an existing team's policy and active wiki/projects/discussions unless their removal was requested. Every step is safe to re-run.

## Workflow

1. **Read current settings** before changing them, and keep this output to compare after the edit:

   ```bash
   settings_fields=deleteBranchOnMerge,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,hasIssuesEnabled,hasProjectsEnabled,hasWikiEnabled,hasDiscussionsEnabled
   gh repo view "$repository" --json "$settings_fields"
   ```

1. **Extend the edit**: append the baseline before the root's single `gh repo edit`. Add `--enable-issues=false` only when the project tracks issues elsewhere. Add the two secret-scanning flags only for a public repository or when `security_and_analysis.secret_scanning` is present; otherwise report that the capability is unavailable and continue with the remaining settings:

   ```bash
   repository_json="$(gh api "repos/$repository")"
   args+=(
     --delete-branch-on-merge --enable-squash-merge
     --squash-merge-commit-message pr-title-description
     --enable-merge-commit=false --enable-rebase-merge=false --allow-update-branch
     --enable-wiki=false --enable-projects=false --enable-discussions=false
   )
   if [[ "$(jq -r .visibility <<<"$repository_json")" == public ]] ||
     [[ "$(jq -r '.security_and_analysis.secret_scanning.status? // empty' <<<"$repository_json")" ]]; then
     args+=(--enable-secret-scanning --enable-secret-scanning-push-protection)
   else
     echo "Secret scanning is unavailable for $repository; leaving it unchanged." >&2
   fi
   ```

1. **Protect a public repository** after the edit: enable private vulnerability reporting and keep exactly one repository ruleset, `Protect default branch`, that blocks deletion and force pushes without requiring pull requests or signatures, so direct pushes keep working. Look it up by name and update it in place; create it only when it is absent and no other ruleset already enforces both rules. Duplicates left by earlier runs stop the step: report their IDs and delete extras only with the user's approval.

   ```bash
   branch="$(gh repo view "$repository" --json defaultBranchRef --jq .defaultBranchRef.name)"
   ruleset='{"name": "Protect default branch", "target": "branch", "enforcement": "active",
     "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
     "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}], "bypass_actors": []}'
   gh api -X PUT "repos/$repository/private-vulnerability-reporting"
   ids="$(gh api --paginate "repos/$repository/rulesets?includes_parents=false" \
     --jq '.[] | select(.name == "Protect default branch") | .id')"
   if (( $(wc -w <<<"$ids") > 1 )); then
     echo "Duplicate 'Protect default branch' rulesets: $ids; resolve before editing." >&2
   elif [[ -n "$ids" ]]; then
     gh api -X PUT "repos/$repository/rulesets/$ids" --input - --jq .id <<<"$ruleset"
   elif [[ "$(gh api "repos/$repository/rules/branches/$branch" \
     --jq '[.[].type] | contains(["deletion", "non_fast_forward"])')" == true ]]; then
     echo "Another ruleset already blocks deletion and force pushes on $branch."
   else
     gh api -X POST "repos/$repository/rulesets" --input - --jq .id <<<"$ruleset"
   fi
   ```

1. **Read back** what the edit and protection changed: repeat the settings read, then query the update-branch, squash-message, security, and ruleset state that `gh repo view` omits. Expect `deletion` and `non_fast_forward` among the effective branch rules and `true` for vulnerability reporting on a public repository:

   ```bash
   gh repo view "$repository" --json "$settings_fields"
   gh api "repos/$repository" \
     --jq '{allow_update_branch, squash_merge_commit_title, squash_merge_commit_message, security_and_analysis}'
   gh api "repos/$repository/private-vulnerability-reporting" --jq .enabled
   gh api --paginate "repos/$repository/rulesets?includes_parents=false" --jq '.[] | {id, name, enforcement}'
   gh api "repos/$repository/rules/branches/$branch" --jq 'map(.type)'
   ```

## Gotchas

- **Detect secret-scanning eligibility**: public repositories are covered; private and internal repositories require an eligible GitHub Secret Protection or Advanced Security entitlement. Capability-detect instead of inferring availability from personal versus organization ownership.
- **Report plan limits as gaps**: rulesets and branch protection on a private repository need GitHub Pro or Team; on Free the API answers 403 `Upgrade to GitHub Pro`. Report the gap instead of changing visibility. Private vulnerability reporting applies to public repositories only.
- **Edit only the owned ruleset**: `rules/branches/<branch>` merges organization and repository rulesets; edit only the repository ruleset this guide owns, and never a parent organization's.

## Documentation

- [Repository rulesets API](https://docs.github.com/en/rest/repos/rules) · [Private vulnerability reporting API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository)
