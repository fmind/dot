---
name: git-delivery
description: "Commit, push, and release with Conventional Commits; branches, worktrees, conflicts, and hook fixes."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-delivery
  created: "2026-09-16"
  updated: "2026-11-08"
---

# Git Delivery

Deliver only the authorized changes while preserving the index, branch intent, and enabled hooks. Branching, pushing, and release publication are separate modes of the same workflow.

## Workflow

1. **Resolve delivery authority and target branch**: take both from the request; inspect the current branch and unmerged work before switching. Never overwrite an existing branch or move unrelated commits. History investigation is read-only: fetch missing objects into an isolated clone and bisect in a disposable worktree; pulling into the working tree or rewriting history needs authority.
1. **Match work to the request**: a commit-only request preserves the staged selection and stops after committing. A delivery request includes staging and pushing only its intended changes; neither implies release publication.
1. **Follow requested branch and release modes**: if the user requests a branch or PR, follow [git-worktree](references/git-worktree/GUIDE.md) and [github-pull-request](../github-pull-request/SKILL.md). A later release instruction selects the release mode; use the repository's native release task where present.
1. **Verify the delivery**: the exact commit, remote destination, and requested publication level. Keep published tags immutable and preserve enabled hooks.

## Commit messages

- **Write one Conventional Commits subject**: `<type>(<scope>): <description>` with type `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, or `revert`; imperative, under 72 characters, `!` after the type or scope for a breaking change, and no AI attribution or co-author trailers.
- **Commit only the staged selection**: never auto-stage unrelated changes; on a hook failure or an empty index, report it and do not amend.

## Task guides

<!-- guides:start -->

- [git-add-commit-push](references/git-add-commit-push.md): Stage, commit, push, and recover hook failures within the authorized scope.
- [git-worktree](references/git-worktree/GUIDE.md): Create Git branches, worktrees, or isolated snapshots of uncommitted work.
- [release](references/release/GUIDE.md): Prepare, publish when requested, or verify versioned releases.
- [resolve-conflicts](references/resolve-conflicts.md): Resolve Git merge or rebase conflicts by both sides' intent; verify the result.

<!-- guides:end -->
