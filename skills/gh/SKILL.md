---
name: gh
description: "Use gh for GitHub issues, pull requests, repo metadata and settings, Actions logs, auth, and API calls."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gh
  created: "2026-09-16"
  updated: "2026-11-10"
---

# GitHub CLI

Use `gh` for authenticated GitHub input and output. This connector owns account selection, request mechanics, and the task guides below for issues, pull requests, and repository settings; [github-actions](../github-actions/SKILL.md) owns workflow authoring and CI/CD policy, and [git-delivery](../git-delivery/SKILL.md) owns commits, pushes, and releases.

## Workflow

1. **Resolve the intended host and repository**: from the request and Git remotes, using `gh repo view --json nameWithOwner`; never print raw remote URLs, which can contain credentials. Pass `-R <owner>/<repo>` to repository commands and `--hostname <host>` to API calls when needed; do not silently use an unrelated current checkout.
1. **Check authentication**: run `gh auth status --active --hostname <host>` when authentication is uncertain. Environment credentials can override stored accounts; never print token values or use `--show-token`. Account changes and additional OAuth scopes need authority; [dot-cli authentication](../dot-cli/references/authentication.md) owns the login policy and its one-off grants.
1. **Prefer bounded native commands**: prefer the native command with an explicit `--limit` and selected `--json` fields. Read a remote file or directory with `gh repo read-file <path> -R <owner>/<repo> --ref <sha>` or `gh repo read-dir` (preview; pass `""`, not `.`, for the root) instead of cloning or decoding the contents API. For missing capabilities, use `gh api --method GET <endpoint>` with bounded `per_page` and `page` fields. Adding `--field` or `--raw-field` otherwise changes the default method to POST.
1. **Read failed Actions logs first**: `gh run view <run-id> -R <owner>/<repo> --job <job-id> --log-failed`, saved to a file when large.
1. **Write from files, then read back**: use `--body-file` or `gh api --input <file>` for an authorized write, re-read the changed fields, and reconcile remote state before retrying an uncertain write.

## Task guides

<!-- guides:start -->

- [issues](references/issues/GUIDE.md): Plan, draft, deduplicate, update, link, and close GitHub issues.
- [pull-request](references/pull-request.md): Open, update, verify, comment on, and merge GitHub pull requests.
- [repository](references/repository/GUIDE.md): Set GitHub repo description, homepage, topics, merge policy, and security settings.

<!-- guides:end -->

## Gotchas

- **Inspect auth state, not exit codes**: `gh auth status --json` can exit zero despite authentication failures; inspect the reported state.
- **Paginate only bounded collections**: `gh api --paginate` fetches every page; use it only for a bounded, intentionally complete collection. `--slurp` combines page objects, not individual records.

## Official Skills

Upstream `cli/cli` publishes agent skills, including a same-name `gh`: preview it, never install it under that name ([vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)). Review and install others only through the pinned [official-skills](references/official-skills.md) procedure.

## Documentation

- [GitHub CLI manual](https://cli.github.com/manual/) · [API command](https://cli.github.com/manual/gh_api)
- Releases: [GitHub CLI](https://github.com/cli/cli/releases)
- Companion skills: [github-actions](../github-actions/SKILL.md) (CI/CD workflows and Dependabot), [git-delivery](../git-delivery/SKILL.md) (commits, pushes, worktrees, and releases).
