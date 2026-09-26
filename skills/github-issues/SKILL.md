---
name: github-issues
description: "Plan, draft, update, link, and close GitHub issues with gh."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-issues
  created: "2026-08-30"
  updated: "2026-09-26"
---

# GitHub Issues

Plan, read, and mutate GitHub issues from verified repository and remote state. When audit findings need prioritization, drafts, or dependency ordering, follow the [backlog workflow](references/backlog.md) before any GitHub mutation.

## Workflow

Use [gh](../gh/SKILL.md) for account selection, bounded API calls, and request serialization when needed.

1. **Confirm the target**: resolve the repository from the explicit URL or `gh repo view --json nameWithOwner,visibility` and state `OWNER/REPO`; never print raw remote URLs, which can contain credentials; never infer another repository from a similarly named checkout.
1. **Refresh current state** before proposing a change:

   ```bash
   gh issue view <number> -R <owner>/<repo> --json number,title,body,state,stateReason,labels,assignees,milestone,url
   gh issue list -R <owner>/<repo> --state all --search '<distinct terms>' --limit 20 --json number,title,state,url
   ```

1. **Load discussion when relevant**: fetch comments separately when decisions, acceptance criteria, or requested replies depend on them; preserve that context before editing. Narrow or paginate a search that reaches its limit before claiming no duplicate exists.
1. **Deduplicate**: update the existing issue that represents the same outcome; keep reproduction, acceptance criteria, dependencies, decisions, and proof; drop stale logs and duplicate checklists.
1. **Draft before creating**: for multiple findings or dependency-aware work, apply the [backlog workflow](references/backlog.md) and [draft contract](references/draft-contract.md), present the reviewable set, and stop unless issue creation is already authorized.
1. **Apply one bounded mutation** the user authorized. Write substantial bodies to a temporary file and pass `--body-file`; avoid shell interpolation and interactive prompts:

   ```bash
   gh issue create -R <owner>/<repo> --title '<title>' --body-file <body-file>
   gh issue edit <number> -R <owner>/<repo> --body-file <body-file>
   ```

1. **Verify from GitHub**: re-read with `gh issue view --json ...`, compare the intended fields, and report the URL; a zero exit code alone is not proof of final state.

## Gotchas

- **Green is not closed**: verify the issue's acceptance criteria and requested delivery boundary before `gh issue close`; local passing code is not delivery.
- **People and planning fields**: assignments, comment notifications, milestones, and project changes are coordination acts; make them only when the request names them.
- **Raw findings**: classify, deduplicate, prioritize, and draft review findings through the [backlog workflow](references/backlog.md) before creating issues from them.

## Official Skills

Upstream: `cli/cli`. This package uses the preview `gh skill` path described in the shared [vendor-skill policy](../agent-project/references/vendor-skills.md):

```bash
gh skill search github --owner cli --json repo,skillName,description
gh skill preview cli/cli <name>
gh skill install cli/cli <name>
```

## Documentation

- [gh issue manual](https://cli.github.com/manual/gh_issue)
- Releases: [GitHub CLI](https://github.com/cli/cli/releases)
- Companion skills: [repository-review](../repository-review/SKILL.md) (verified findings), [implementation-plan](../implementation-plan/SKILL.md) (ordered implementation), [github-pull-request](../github-pull-request/SKILL.md) (the PR).
