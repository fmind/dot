---
name: repository
description: "Set GitHub repo description, homepage, topics, merge policy, and security settings."
---

# GitHub Repository

Set repository description, homepage, and topics via `gh repo edit` ([gh](../../SKILL.md)). Run the [settings baseline](references/settings-baseline.md) only for new solo-maintained repos or explicit settings passes, never on metadata-only requests.

## Workflow

1. **Derive metadata from code**:
   - `pyproject.toml` `[project]` name, description, and URLs; `README.md` lead for a single-line description under ~140 chars.
   - Homepage: verified canonical URL only (never assume a Pages URL from the repo name).
   - Topics: 3–6 lowercase `[a-z0-9-]` tags (`<=50` chars each, max 20) covering language, stack, or domain.
1. **Read state and apply in one script** (shell variables do not persist across tool calls; remove old topics only when replacing the full set):

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

1. **Verify**: re-read the same `gh repo view --json ...` fields and report changes.
1. **Apply settings when requested**: run [settings-baseline.md](references/settings-baseline.md) for merge policy, sidebar features, secret scanning, Dependabot security updates, Actions hardening, immutable releases, and branch protection.

## Gotchas

- **Keep descriptions single-line and <140 chars** to avoid GitHub UI truncation.
- **Never change visibility unasked**: never pass `--visibility` or `--accept-visibility-change-consequences` without explicit instruction.

## Documentation

- [gh repo edit manual](https://cli.github.com/manual/gh_repo_edit) · [releases](https://github.com/cli/cli/releases)
- Companion skills: [pull-request](../pull-request.md), [project-license](../../../project-scaffolding/references/project-license/GUIDE.md), [project-scaffolding](../../../project-scaffolding/references/bootstrap.md).
