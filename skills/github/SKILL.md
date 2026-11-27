---
name: github
description: "Operate GitHub via gh (issues, PRs, repos, Actions logs), bootstrap repos, pick LICENSE, and configure CI/CD & Dependabot."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github
  created: "2026-11-21"
  updated: "2026-11-27"
---

# GitHub & Actions

Use `gh` for authenticated GitHub reads and writes, bootstrap repositories, select licenses, and configure pinned GitHub Actions CI/CD, Dependabot, and `jactionlint`. [git-delivery](../git-delivery/SKILL.md) owns local commits, branches, pushes, Lefthook hooks, and releases.

## Workflow (`gh` CLI)

1. **Resolve host and repository**: confirm from `gh repo view --json nameWithOwner` (never print raw remote URLs); pass `-R <owner>/<repo>` (`--hostname <host>` on `gh api`) explicitly.
1. **Verify auth**: run `gh auth status --active --hostname <host>` (`gh auth status --json` can exit 0 on failed auth); never print tokens or pass `--show-token`. Account switches and extra scopes follow [dot-cli authentication](../dot-cli/references/authentication.md).
1. **Use bounded native reads**: pass `--limit` and `--json` fields; read remote files via `gh repo read-file <path> -R <owner>/<repo> --ref <sha>` or `gh repo read-dir -R <owner>/<repo>` (omit path for root) instead of cloning; inspect failed Actions logs via `gh run view <run-id> -R <owner>/<repo> --job <job-id> --log-failed`.
1. **Write humanized text from files, review, then read back**: shape external copy with [humanize](../humanize/SKILL.md) (`fmind-review-human` on substantive PRs/issues), scan payloads with `betterleaks stdin --redact`, audit non-trivial workflow or security changes with `fmind-review-cicd` / `fmind-review-security`, pass `--body-file` or `gh api --input <file>`, and re-read modified fields before retrying.

## Task guides

<!-- guides:start -->

- [bootstrap](references/bootstrap.md): Create a new repository: location, visibility, stack composition, shared layer, checks, and first push.
- [ci-cd](references/ci-cd/GUIDE.md): Wire Python CI, scheduled security scans, and OIDC PyPI/OCI CD.
- [dependabot](references/dependabot.md): Configure security-only Dependabot alerts and grouped fix PRs.
- [issues](references/issues/GUIDE.md): Plan, draft, deduplicate, update, link, and close GitHub issues.
- [jactionlint](references/jactionlint.md): Lint and audit GitHub Actions workflows and Dependabot with jactionlint.
- [project-license](references/project-license/GUIDE.md): Choose, write, and declare a repository LICENSE (MIT, CC-BY-4.0, or proprietary) by namespace and content.
- [pull-request](references/pull-request.md): Open, update, verify, comment on, and merge GitHub pull requests.
- [repository](references/repository/GUIDE.md): Set GitHub repo description, homepage, topics, merge policy, and security settings.

<!-- guides:end -->

## Official Skills

Upstream `cli/cli` ships `gh` (avoid installing alongside this skill to prevent overlapping GitHub triggers per [vendor-skill policy](../agent-harnesses/references/vendor-skills.md#name-collisions)) and `gh-skill`.

## Documentation

- [GitHub CLI manual](https://cli.github.com/manual/) · [GitHub Actions](https://docs.github.com/en/actions) · [Dependabot](https://docs.github.com/en/code-security/dependabot)
- Companions: [git-delivery](../git-delivery/SKILL.md), [mise](../mise/SKILL.md), [code-security](../code-security/SKILL.md).
