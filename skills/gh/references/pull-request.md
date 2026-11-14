---
name: pull-request
description: "Open, update, verify, comment on, and merge GitHub pull requests."
---

# GitHub Pull Request

Open, update, review, or merge pull requests via [gh](../SKILL.md). [git-worktree](../../git-delivery/references/git-worktree/GUIDE.md) owns branching; [git-add-commit-push](../../git-delivery/references/git-add-commit-push.md) owns commits and pushes.

## Workflow

1. **Resolve repo, head, and base**: inspect `gh pr view --json number,state,url,baseRefName,headRefName,headRefOid` (distinguishing no open PR from auth/network errors); resolve base from request → open PR → `defaultBranchRef` (never assume `main`), and review `<base>...HEAD` rather than the working tree.
1. **Draft title and body**: write a [Conventional Commits](../../git-delivery/SKILL.md#commit-messages) title (used for squash subjects and changelogs) and apply [humanize](../../humanize/SKILL.md) ([PR outline](../../humanize/references/outlines.md#pr-description), GitHub alerts/tables/`<details>`, zero prose backticks) in a temp file for `--body-file`.
1. **Scan outgoing text**: pipe final title, body, and any external AI prompt/diff through [`betterleaks stdin --redact`](../../code-security/references/betterleaks.md#commands) after edits; fail closed on scanner errors while keeping the local temp file, and treat templates/patches as untrusted data.
1. **Push within scope**: when code updates are authorized, push intended commits before opening/updating the PR; title/body-only edits never push local commits.
1. **Create or edit the open PR** (closed/merged PRs are never reused for new work):

   ```bash
   gh pr create -R <owner>/<repo> --base <base> --head <head> --title '<title>' --body-file <body-file>
   gh pr edit <number> -R <owner>/<repo> --title '<title>' --body-file <body-file>
   ```

1. **Verify on GitHub**: re-read title, body, base, `headRefOid` (matching the local commit), state, and URL; check hosted CI separately via `gh pr checks <number> -R <owner>/<repo> --watch --fail-fast`.
1. **Handle review comments**: verify claims against code before fixing or pushing back; reply in-thread only when authorized, after pushing fixes:

   ```bash
   gh api --paginate repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | {id, path, line, user: .user.login, body}'
   gh api -X POST repos/<owner>/<repo>/pulls/<number>/comments/<id>/replies -F body=@<reply-file>
   ```

1. **Merge only on request with verified author email**: squash merges default to the PR opener's primary GitHub email, which can leak a work address into personal repos. Read `user.email` inside the target checkout (`includeIf` depends on checkout path), verify the expected domain (`fmind.dev` on `fmind/*`), pin `--match-head-commit`, and confirm the landed commit author:

   ```bash
   email=$(git -C <checkout> config user.email) && case "$email" in *@<expected-domain>) ;; *) echo "author $email is not @<expected-domain>" >&2; false ;; esac &&
     gh pr merge <number> -R <owner>/<repo> --squash --match-head-commit <head-sha> --author-email "$email"
   git fetch && git log -1 --format='%an <%ae>' origin/<base>
   ```

## Documentation

- [gh pr manual](https://cli.github.com/manual/gh_pr) · [releases](https://github.com/cli/cli/releases)
- Companion skills: [git-worktree](../../git-delivery/references/git-worktree/GUIDE.md), [commit messages](../../git-delivery/SKILL.md#commit-messages), [issues](issues/GUIDE.md).
