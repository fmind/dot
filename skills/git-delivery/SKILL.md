---
name: git-delivery
description: "Stage, commit, push, and release scoped changes with Conventional Commits; fix hook failures."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-delivery
  created: "2026-09-16"
  updated: "2026-10-07"
---

# Git Delivery

Deliver only the authorized changes while preserving the index, branch intent, and enabled hooks. Branching, pushing, and release publication are separate modes of the same workflow.

## Workflow

1. **Resolve delivery authority and target branch**: take both from the request; inspect the current branch and unmerged work before switching. Never overwrite an existing branch or move unrelated commits.
1. **Match work to the request**: a commit-only request preserves the staged selection and stops after committing. A delivery request includes staging and pushing only its intended changes; neither implies release publication.
1. **Follow requested branch and release modes**: if the user requests a branch or PR, follow [git-worktree](../git-worktree/SKILL.md) and [github-pull-request](../github-pull-request/SKILL.md). A later release instruction selects the release mode; use the repository's native release task where present.
1. **Verify the delivery**: the exact commit, remote destination, and requested publication level. Keep published tags immutable and preserve enabled hooks.

## Task guides

<!-- guides:start -->

- [conventional-commit](references/conventional-commit.md): Commit the staged selection with Conventional Commits.
- [git-add-commit-push](references/git-add-commit-push.md): Stage, commit, push, and recover hook failures within the authorized scope.
- [release](references/release/GUIDE.md): Prepare, publish when requested, or verify versioned releases.

<!-- guides:end -->
