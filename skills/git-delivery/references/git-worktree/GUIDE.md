---
name: git-worktree
description: "Create Git branches, worktrees, or isolated snapshots of uncommitted work."
---

# Git Worktree

Create a local branch, linked worktree, or isolated dirty-tree clone and report the exact candidate tested.

## Workflow

1. **Branch in place when clean**: name `<type>/<slug>` (Conventional Commit type + lowercase kebab-case) and run `git switch -c <branch> <base>` (`HEAD` by default); stop if the branch exists and never stash or reset to switch.
1. **Choose isolation**: `git worktree add --detach <dest> <rev>` to inspect a commit, `git worktree add -b <branch> <dest> <base>` to build on a branch, or a disposable clone when uncommitted edits or independent refs/hooks are needed (in `agy` 1.5.5+, `invoke_subagent` with `Workspace="share"` or `"branch"` snapshots staged, unstaged, and untracked edits up to 100k entries / 4 GiB automatically; see [agy features](../../../agy/references/cli/references/features.md)).
1. **Snapshot a dirty tree**: `git clone --no-hardlinks --no-checkout <source> <dest>`, detach at recorded `HEAD`, and copy tracked/untracked bytes, modes, unfollowed symlinks, and deletions from `git ls-files --cached --others --exclude-standard -z` (excluding ignored caches, `.venv`, and secrets); diff against `<source>` before running checks.
1. **Gate in isolation**: isolate test ports, DBs, and mutable caches, and pass `MISE_TRUSTED_CONFIG_PATHS=<dest>` instead of persisting `mise trust`.
1. **Clean up**: inspect formatter diffs before copying back, preserve the source index, remove only task-created worktrees/clones with no unique work left, and report tested SHA, overlaid paths, gate results, and any kept workspace.

## Gotchas

- **Clean `HEAD` != dirty checkout**: passing in a clean worktree never proves uncommitted edits.
- **Linked worktrees are not sandboxes**: they share `.git` objects, refs, config, and hooks.
- **Never force reuse**: never force, stash, reset, or clean a busy branch or dirty path.
- **Replace external symlinks**: symlinks pointing back into `<source>` break isolation; swap in fixtures or stop that test.

## Documentation

- [Git worktree](https://git-scm.com/docs/git-worktree) · [Git clone](https://git-scm.com/docs/git-clone)
- Companion skills: [mise](../../../mise/SKILL.md), [resolve-conflicts](../resolve-conflicts.md).
