---
name: issues
description: "Plan, draft, deduplicate, update, link, and close GitHub issues."
---

# GitHub Issues

Plan, read, and update GitHub issues from verified repo and remote state via [gh](../../SKILL.md).

## Workflow

1. **Confirm target**: resolve `OWNER/REPO` from the URL or `gh repo view --json nameWithOwner,visibility`; never infer from a similarly named checkout.
1. **Refresh remote state**:

   ```bash
   gh issue view <number> -R <owner>/<repo> --json number,title,body,state,stateReason,labels,assignees,milestone,url
   gh issue list -R <owner>/<repo> --state all --search '<distinct terms>' --limit 20 --json number,title,state,url
   gh search issues '<problem in plain words>' -R <owner>/<repo> --search-type hybrid --limit 20 --json number,title,state,url
   ```

1. **Check comments and duplicates**: fetch comments when decisions, criteria, or replies depend on them. Narrow/paginate capped lexical searches and run one hybrid search page before declaring no duplicate exists.
1. **Deduplicate**: update an existing issue sharing the same outcome, retaining reproduction, acceptance criteria, dependencies, decisions, and proof while dropping stale logs and duplicate checklists.
1. **Draft multi-issue sets**: for multiple findings or dependencies, follow the [backlog workflow](references/backlog.md), present drafts, and stop unless creation is authorized.
1. **Apply authorized mutations** via `--body-file` (no shell interpolation or prompts):

   ```bash
   gh issue create -R <owner>/<repo> --title '<title>' --body-file <body-file>
   gh issue edit <number> -R <owner>/<repo> --body-file <body-file>
   ```

1. **Read back**: re-read via `gh issue view --json ...`, verify changed fields, and report the URL.

## Gotchas

- **Green is not closed**: confirm acceptance criteria and the requested delivery boundary before `gh issue close`.
- **Touch coordination fields only when asked**: change assignees, milestones, projects, or comment pings only on explicit request.

## Documentation

- Upstream `github/awesome-copilot` ships `github-issues` (MCP-based); follow [vendor-skill policy](../../../agent-project/references/vendor-skills.md) before installing.
- [gh issue manual](https://cli.github.com/manual/gh_issue) · [releases](https://github.com/cli/cli/releases)
- Companion skills: [full-review](../../../full-review/SKILL.md), [pull-request](../pull-request.md).
