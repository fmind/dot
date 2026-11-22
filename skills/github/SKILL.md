---
name: github
description: "Operate GitHub via gh (issues, PRs, repos, Actions logs) and configure CI/CD, Dependabot, Lefthook."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github
  created: "2026-11-21"
  updated: "2026-11-22"
---

# GitHub & Actions

Use `gh` for authenticated GitHub reads and writes, and configure pinned GitHub Actions CI/CD, Dependabot, Lefthook, and `jactionlint`. [git-delivery](../git-delivery/SKILL.md) owns local commits, branches, pushes, and releases.

## Workflow (`gh` CLI)

1. **Resolve host and repository**: confirm from `gh repo view --json nameWithOwner` (never print raw remote URLs); pass `-R <owner>/<repo>` (`--hostname <host>` on `gh api`) explicitly.
1. **Verify auth**: run `gh auth status --active --hostname <host>` (`gh auth status --json` can exit 0 on failed auth); never print tokens or pass `--show-token`. Account switches and extra scopes follow [dot-cli authentication](../dot-cli/references/authentication.md).
1. **Use bounded native reads**: pass `--limit` and `--json` fields; read remote files via `gh repo read-file <path> -R <owner>/<repo> --ref <sha>` or `gh repo read-dir` (`""`, not `.`, for root) instead of cloning; inspect failed Actions logs via `gh run view <run-id> -R <owner>/<repo> --job <job-id> --log-failed`.
1. **Write humanized text from files, then read back**: shape copy with [humanize](../humanize/SKILL.md), scan payloads with `betterleaks stdin --redact`, pass `--body-file` or `gh api --input <file>`, and re-read modified fields before retrying.

## Task guides

<!-- guides:start -->

- [bootstrap](references/bootstrap.md): Create a new repository: location, visibility, stack composition, shared layer, checks, and first push.
- [ci-cd](references/ci-cd/GUIDE.md): Wire Python CI, scheduled security scans, and OIDC PyPI/OCI CD.
- [dependabot](references/dependabot.md): Configure security-only Dependabot alerts and grouped fix PRs.
- [gh-aw](references/gh-aw.md): Configure and bound gh-aw agentic workflows with safe outputs.
- [issues](references/issues/GUIDE.md): Plan, draft, deduplicate, update, link, and close GitHub issues.
- [jactionlint](references/jactionlint.md): Lint and audit GitHub Actions workflows and Dependabot with jactionlint.
- [lefthook](references/lefthook.md): Configure local Lefthook Git hooks via mise tasks.
- [project-license](references/project-license/GUIDE.md): Choose, write, and declare a repository LICENSE (MIT, CC-BY-4.0, or proprietary) by namespace and content.
- [pull-request](references/pull-request.md): Open, update, verify, comment on, and merge GitHub pull requests.
- [repository](references/repository/GUIDE.md): Set GitHub repo description, homepage, topics, merge policy, and security settings.

<!-- guides:end -->

## Official Skills

Upstream `cli/cli` ships `gh` (avoid installing alongside this skill to prevent overlapping GitHub triggers per [vendor-skill policy](../agent-harnesses/references/vendor-skills.md#name-collisions)) and `gh-skill`.

## Documentation

- [GitHub CLI manual](https://cli.github.com/manual/) · [GitHub Actions](https://docs.github.com/en/actions) · [Dependabot](https://docs.github.com/en/code-security/dependabot)
- Companions: [git-delivery](../git-delivery/SKILL.md), [mise](../mise/SKILL.md), [code-security](../code-security/SKILL.md).
