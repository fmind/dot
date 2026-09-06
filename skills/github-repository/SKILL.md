---
name: github-repository
description: Configure a GitHub repository's description, homepage, topics, and solo-developer settings via gh, derived from the codebase. Use when tidying repo settings.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-repository
  created: "2026-06-23"
  updated: "2026-09-06"
---

# GitHub Repository

Derive a repository's description, homepage, and topics from its codebase and apply them with `gh repo edit` together with solo-developer settings: squash-only merges, secure defaults, a decluttered sidebar.

## Workflow

1. **Extract metadata** from the codebase:
   - Project metadata: Python `pyproject.toml` (`[project]` name, description, and URLs).
   - `README.md`: the first paragraphs give a one-line description under ~140 characters.
   - Homepage: derive from hosting, e.g. `https://<owner>.github.io/<repo>` for GitHub Pages.
   - Topics: 3 to 6 lowercase tags for language, frameworks, tools, or domain (`agent`, `python`, `cli`); letters, numbers, and hyphens only, 50 characters max, 20 per repository.
1. **Inspect the current state** so the edit stays idempotent; stop when there is no GitHub remote or `gh` is not authenticated:

   ```bash
   gh auth status
   git config --get remote.origin.url
   gh repo view --json nameWithOwner,visibility,isInOrganization,description,homepageUrl,repositoryTopics,deleteBranchOnMerge,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,hasIssuesEnabled,hasProjectsEnabled,hasWikiEnabled,hasDiscussionsEnabled
   ```

1. **Build one consolidated edit**: add the desired topics, remove every current topic not in that desired set, and append `--enable-issues=false` only when the project tracks issues elsewhere. Query the repository REST payload and add the two secret-scanning flags only for a public repository or when `security_and_analysis.secret_scanning` is present; otherwise report that the capability is unavailable and continue with the remaining settings:

   ```bash
   repository="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
   repository_json="$(gh api "repos/$repository")"
   desired_topics=(tag1 tag2 tag3)
   args=(
     --description "<description>" --homepage "<homepage-url>"
     --delete-branch-on-merge --enable-squash-merge
     --squash-merge-commit-message pr-title-description
     --enable-merge-commit=false --enable-rebase-merge=false --allow-update-branch
     --enable-wiki=false --enable-projects=false --enable-discussions=false
   )
   for topic in "${desired_topics[@]}"; do args+=(--add-topic "$topic"); done
   while IFS= read -r topic; do
     [[ " ${desired_topics[*]} " == *" $topic "* ]] || args+=(--remove-topic "$topic")
   done < <(jq -r '.topics[]' <<<"$repository_json")
   if [[ "$(jq -r .visibility <<<"$repository_json")" == public ]] ||
     [[ "$(jq -r '.security_and_analysis.secret_scanning.status? // empty' <<<"$repository_json")" ]]; then
     args+=(--enable-secret-scanning --enable-secret-scanning-push-protection)
   else
     echo "Secret scanning is unavailable for $repository; leaving it unchanged." >&2
   fi
   gh repo edit "$repository" "${args[@]}"
   ```

1. **Verify** with the same `gh repo view --json ...` call and report the fields that changed.

## Gotchas

- **Truncation**: keep the description single-line and under ~140 characters or the GitHub UI truncates it.
- **Secret scanning eligibility**: public repositories are covered; private and internal repositories require an eligible GitHub Secret Protection or Advanced Security entitlement. Capability-detect instead of inferring availability from personal versus organization ownership.
- **Visibility**: never pass `--visibility` or `--accept-visibility-change-consequences` unless the user explicitly asks.

## Documentation

- [gh repo edit manual](https://cli.github.com/manual/gh_repo_edit)
- Companion skills: [github-pull-request](../github-pull-request/SKILL.md) (PR titles feed the squash message), [project-license](../project-license/SKILL.md) (LICENSE), [new-project](../new-project/SKILL.md) (bootstrap).
