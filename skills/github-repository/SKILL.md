---
name: github-repository
description: "Set GitHub repo description, topics, merge policy, and security settings."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-repository
  created: "2026-06-23"
  updated: "2026-10-05"
---

# GitHub Repository

Derive a repository's description, homepage, and topics from its codebase and apply the requested fields with `gh repo edit`. For a new solo-maintained repository or an explicitly requested settings pass, use the [settings baseline](references/settings-baseline.md); a metadata-only request does not include merge policy, sidebar features, or security settings.

## Workflow

Use [gh](../gh/SKILL.md) for account selection, repository identity without printing raw remote URLs, bounded API calls, and request serialization when needed.

1. **Extract metadata** from the codebase:
   - Project metadata: Python `pyproject.toml` (`[project]` name, description, and URLs).
   - `README.md`: the first paragraphs give a one-line description under ~140 characters.
   - Homepage: use the configured, verified canonical site; do not infer a live Pages site merely from the repository name.
   - Topics: 3 to 6 lowercase tags for language, frameworks, tools, or domain (`agent`, `python`, `cli`); letters, numbers, and hyphens only, 50 characters max, 20 per repository.
1. **Inspect the current state** so the edit stays idempotent; stop when there is no GitHub remote or `gh` is not authenticated:

   ```bash
   state="$(gh repo view --json nameWithOwner,visibility,description,homepageUrl,repositoryTopics)"
   ```

1. **Build one scoped edit**: include only the requested metadata flags; add the desired topics and remove obsolete ones only when replacing the set:

   ```bash
   repository="$(jq -r .nameWithOwner <<<"$state")"
   desired_topics=(tag1 tag2 tag3)
   args=(--description "<description>" --homepage "<homepage-url>")
   for topic in "${desired_topics[@]}"; do args+=(--add-topic "$topic"); done
   while IFS= read -r topic; do
     [[ " ${desired_topics[*]} " == *" $topic "* ]] || args+=(--remove-topic "$topic")
   done < <(jq -r '(.repositoryTopics // [])[].name' <<<"$state")
   ```

1. **Extend for a settings pass** only when settings are in scope: the [settings baseline](references/settings-baseline.md) appends merge policy, sidebar features, and secret scanning to the same `args`, then protects a public repository after the edit.
1. **Apply** once with `gh repo edit "$repository" "${args[@]}"`.
1. **Verify** with the same `gh repo view --json ...` fields and report the ones that changed; a settings pass also runs the guide's read-back, which covers fields `gh repo view` does not expose.

## Task guides

<!-- guides:start -->

- [settings-baseline](references/settings-baseline.md): Apply the solo-maintainer merge, feature, secret-scanning, and default-branch protection baseline idempotently.

<!-- guides:end -->

## Gotchas

- **Avoid description truncation**: keep the description single-line and under ~140 characters or the GitHub UI truncates it.
- **Change visibility only on request**: never pass `--visibility` or `--accept-visibility-change-consequences` unless the user explicitly asks.

## Documentation

- [gh repo edit manual](https://cli.github.com/manual/gh_repo_edit)
- Releases: [GitHub CLI](https://github.com/cli/cli/releases)
- Companion skills: [github-pull-request](../github-pull-request/SKILL.md) (PR titles feed the squash message), [project-license](../project-scaffolding/references/project-license/GUIDE.md) (LICENSE), [project-scaffolding](../project-scaffolding/references/bootstrap.md) (bootstrap).
