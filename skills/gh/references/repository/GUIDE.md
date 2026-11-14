---
name: repository
description: "Set GitHub repo description, homepage, topics, merge policy, and security settings."
---

# GitHub Repository

Set repository description, homepage, and topics via `gh repo edit` ([gh](../../SKILL.md)). Run the [settings baseline](references/settings-baseline.md) only for new solo-maintained repos or explicit settings passes, never on metadata-only requests.

## Workflow

1. **Check repo state and apply metadata**:
   - Derive single-line `<140`-char description, canonical homepage URL, and `3–6` lowercase `[a-z0-9-]` topics (`<=50` chars) from `pyproject.toml` and `README.md`.

   ```bash
   state="$(gh repo view --json nameWithOwner,visibility,description,homepageUrl,repositoryTopics)"
   repository="$(jq -r .nameWithOwner <<<"$state")"
   desired_topics=(tag1 tag2 tag3)
   args=(--description "<description>" --homepage "<homepage-url>")
   for topic in "${desired_topics[@]}"; do args+=(--add-topic "$topic"); done
   while IFS= read -r topic; do
     [[ " ${desired_topics[*]} " == *" $topic "* ]] || args+=(--remove-topic "$topic")
   done < <(jq -r '(.repositoryTopics // [])[].name' <<<"$state")
   gh repo edit "$repository" "${args[@]}"
   ```

1. **Verify**: re-read the same `gh repo view --json ...` fields.
1. **Apply settings when requested**: run [settings-baseline.md](references/settings-baseline.md) (`--disable` sidebar features, squash merges, rulesets, Actions/Dependabot/secret-scanning).

## Gotchas

- **Keep descriptions single-line and under 140 chars** to avoid UI truncation; never pass `--visibility` unasked.

## Documentation

- [gh repo edit manual](https://cli.github.com/manual/gh_repo_edit) · [releases](https://github.com/cli/cli/releases)
- Companion skills: [pull-request](../pull-request.md), [project-license](../../../project-scaffolding/references/project-license/GUIDE.md), [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).
