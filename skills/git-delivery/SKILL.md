---
name: git-delivery
description: "Stage, commit, push, and publish releases when requested; preserve scope, hooks, and history."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-delivery
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Git Delivery

Deliver only the authorized changes while preserving the index, branch intent, and enabled hooks. Branching, pushing, and release publication are separate modes of the same workflow.

## Workflow

1. Resolve delivery authority from the request. For an authorized stage/commit/push flow in `github.com/fmind/*`, use `main` by default when no branch or PR flow was requested; inspect the current branch and unmerged work before switching. Never overwrite an existing branch or move unrelated commits to enforce that default.
1. A commit-only request preserves the staged selection and stops after committing. A delivery request includes staging and pushing only its intended changes; neither implies release publication.
1. If the user requests a branch or PR, follow [git-worktree](../git-worktree/SKILL.md) and [github-pull-request](../github-pull-request/SKILL.md). A later release instruction selects the release mode; use the repository's native release task where present.
1. Verify the exact commit, remote destination, and requested publication level. Keep published tags immutable and preserve enabled hooks.

## Task guides

<!-- guides:start -->

- [conventional-commit](references/conventional-commit.md): Commit the staged selection with Conventional Commits.
- [git-add-commit-push](references/git-add-commit-push.md): Stage, commit, push, and recover hook failures within the authorized scope.
- [release](references/release/GUIDE.md): Prepare, publish when requested, or verify versioned releases.

<!-- guides:end -->
