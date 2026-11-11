---
name: gh
description: "Use gh for GitHub issues, pull requests, repo metadata and settings, Actions logs, auth, and API calls."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gh
  created: "2026-09-16"
  updated: "2026-11-11"
---

# GitHub CLI

Use `gh` for authenticated GitHub reads and writes. This connector owns account selection, bounded requests, and the guides below; [github-actions](../github-actions/SKILL.md) owns workflows and [git-delivery](../git-delivery/SKILL.md) owns commits, pushes, and releases.

## Workflow

1. **Resolve host and repository**: confirm from the request and `gh repo view --json nameWithOwner` (never print raw remote URLs, which may embed credentials). Pass `-R <owner>/<repo>` (`--hostname <host>` on `gh api`) instead of assuming the current checkout.
1. **Verify auth**: run `gh auth status --active --hostname <host>` when uncertain; env tokens can override stored accounts, and never print tokens or pass `--show-token`. Account switches and extra scopes require authority per [dot-cli authentication](../dot-cli/references/authentication.md).
1. **Use bounded native reads**: pass explicit `--limit` and `--json` fields. Read remote files with `gh repo read-file <path> -R <owner>/<repo> --ref <sha>` or `gh repo read-dir` (preview; pass `""`, not `.`, for the root) instead of cloning. For API gaps, pass `gh api --method GET <endpoint>` with `per_page` and `page` (`--field`/`--raw-field` otherwise defaults to POST).
1. **Inspect failed Actions logs first**: `gh run view <run-id> -R <owner>/<repo> --job <job-id> --log-failed` (save large logs to a file).
1. **Write from files, then read back**: pass `--body-file` or `gh api --input <file>` on authorized writes, re-read modified fields, and reconcile remote state before retrying an uncertain write.

## Task guides

<!-- guides:start -->

- [issues](references/issues/GUIDE.md): Plan, draft, deduplicate, update, link, and close GitHub issues.
- [pull-request](references/pull-request.md): Open, update, verify, comment on, and merge GitHub pull requests.
- [repository](references/repository/GUIDE.md): Set GitHub repo description, homepage, topics, merge policy, and security settings.

<!-- guides:end -->

## Gotchas

- **Inspect auth fields, not exit codes**: `gh auth status --json` can exit 0 on failed auth.
- **Paginate only bounded sets**: `gh api --paginate` fetches all pages; `--slurp` wraps page responses rather than flattening items.

## Official Skills

Upstream `cli/cli` ships agent skills including a same-name `gh`: preview only and never install under `gh` ([vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)); follow [official-skills](references/official-skills.md) for pinned installs.

## Documentation

- [GitHub CLI manual](https://cli.github.com/manual/) · [gh api](https://cli.github.com/manual/gh_api) · [releases](https://github.com/cli/cli/releases)
- Companion skills: [github-actions](../github-actions/SKILL.md), [git-delivery](../git-delivery/SKILL.md).
