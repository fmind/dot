---
name: git-delivery
description: "Commit, push, and release with Conventional Commits; branches, worktrees, conflicts, and hook fixes."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-delivery
  created: "2026-09-16"
  updated: "2026-10-29"
---

# Git Delivery

Deliver only the authorized changes while preserving the index, branch intent, and enabled hooks. Branching, pushing, and release publication are separate modes of the same workflow.

## Workflow

1. **Resolve delivery authority and target branch**: take both from the request; inspect the current branch and unmerged work before switching. Never overwrite an existing branch or move unrelated commits.
1. **Match work to the request**: a commit-only request preserves the staged selection and stops after committing. A delivery request includes staging and pushing only its intended changes; neither implies release publication.
1. **Follow requested branch and release modes**: if the user requests a branch or PR, follow [git-worktree](references/git-worktree/GUIDE.md) and [github-pull-request](../github-pull-request/SKILL.md). A later release instruction selects the release mode; use the repository's native release task where present.
1. **Verify the delivery**: the exact commit, remote destination, and requested publication level. Keep published tags immutable and preserve enabled hooks.

## Task guides

<!-- guides:start -->

- [conventional-commit](references/conventional-commit.md): Commit the staged selection with Conventional Commits.
- [git-add-commit-push](references/git-add-commit-push.md): Stage, commit, push, and recover hook failures within the authorized scope.
- [git-worktree](references/git-worktree/GUIDE.md): Create Git branches, worktrees, or isolated snapshots of uncommitted work.
- [branches](references/git-worktree/references/branches.md): Create and switch to a conventional `<type>/<slug>` branch in the current checkout.
- [release](references/release/GUIDE.md): Prepare, publish when requested, or verify versioned releases.
- [resolve-conflicts](references/resolve-conflicts.md): Resolve Git merge or rebase conflicts by both sides' intent; verify the result.

<!-- guides:end -->
