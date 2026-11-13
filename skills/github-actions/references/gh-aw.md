---
name: gh-aw
description: "Configure and bound GitHub Agentic Workflows (gh-aw) with pinned extensions and safe outputs."
---

# GitHub Agentic Workflows (`gh-aw`)

1. **Install pinned**: run `gh extension install github/gh-aw --pin <tag>`, then `gh aw init`, and follow its generated workflow skill.
1. **Lint compiled locks cleanly**: treat generated `.github/workflows/*.lock.yml` files as reviewed supply-chain artifacts and scope `jactionlint` ignores explicitly to those locks.
1. **Bound execution and spend**: start with `staged: true`, explicit `max-turns`, and agent/threat-detection AI-credit caps; require explicit repository authority before running `gh aw run`, enabling unstaged safe outputs, `--push`, or `--auto-merge-prs`.
