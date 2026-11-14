---
name: git-delivery
description: "Commit, push, and release with Conventional Commits and git-cliff; branches, worktrees, conflicts, and hook fixes."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-delivery
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Git Delivery

Deliver only authorized changes while preserving the index, branch state, and enabled hooks across branching, commits, pushes, and releases.

## Workflow

1. **Confirm authority and target branch**: inspect the active branch and unmerged work before switching; never overwrite existing branches or move unrelated commits. History investigation stays read-only (fetch into an isolated clone and bisect in a disposable worktree); pulling or rewriting history requires authority.
1. **Match the requested boundary**: commit-only requests keep the staged selection and stop at `git commit`; delivery requests stage and push only intended changes without publishing a release.
1. **Select branch, PR, or release mode**: follow [git-worktree](references/git-worktree/GUIDE.md) and [pull-request](../gh/references/pull-request.md) when requested; for releases, prefer the repository's native release task over manual steps.
1. **Verify delivery**: confirm the exact SHA, remote ref, and publication level while keeping published tags immutable and hooks enabled.

## Commit messages

- **Write one Conventional Commits subject**: `<type>(<scope>): <description>` using `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, or `revert` — imperative, `<72` chars, `!` before `:` for breaking changes, and zero AI attribution or `Co-authored-by` trailers.
- **Commit only staged changes**: never auto-stage unrelated files; report hook failures or empty indexes without amending.
- **Keep `git lfs` and tags explicit**: never run `git lfs install` globally or auto-fetch/upload LFS blobs without repo confirmation; avoid `push.followTags=true` or `--follow-tags` (push explicit `"refs/tags/$tag"` only when releasing).

## Task guides

<!-- guides:start -->

- [git-add-commit-push](references/git-add-commit-push.md): Stage, commit, push, and recover hook failures within the authorized scope.
- [git-worktree](references/git-worktree/GUIDE.md): Create Git branches, worktrees, or isolated snapshots of uncommitted work.
- [release](references/release/GUIDE.md): Prepare, publish when requested, or verify versioned releases.
- [resolve-conflicts](references/resolve-conflicts.md): Resolve Git merge or rebase conflicts by both sides' intent; verify the result.

<!-- guides:end -->
