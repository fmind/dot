---
name: github-actions
description: "Build GitHub Actions CI/CD, gh-aw agentic workflows, Dependabot, Lefthook, and jactionlint."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-actions
  created: "2026-07-04"
  updated: "2026-11-11"
---

# GitHub Actions

Align local hooks, CI, security scans, and publishing with the repository's `mise` tasks.

## Workflow

Read only the selected guide and its linked resources.

- **GitHub Agentic Workflows (gh-aw)**: install via `gh extension install github/gh-aw --pin <tag>`, run `gh aw init`, and follow its generated skill; treat compiled `.lock.yml` files as supply-chain inputs and scope `jactionlint` ignores to `.github/workflows/*.lock.yml`. Start with `staged: true`, `max-turns`, and agent/threat-detection AI-credit caps; `gh aw run`, unstaged safe outputs, `--push`, and `--auto-merge-prs` each require explicit repository authority.

## Task guides

<!-- guides:start -->

- [ci-cd](references/ci-cd/GUIDE.md): GitHub Actions CI/CD setup, workflow validation, and publication.
- [dependabot](references/dependabot.md): Security-only dependency updates: alerts plus grouped fix PRs.
- [jactionlint](references/jactionlint.md): Lint and audit GitHub Actions workflows, composite actions, and Dependabot.
- [lefthook](references/lefthook.md): Local Git hooks aligned with repository tasks.

<!-- guides:end -->
