---
name: git-worktree
description: "Create Git branches, worktrees, or isolated snapshots of uncommitted work."
---

# Git Worktree

Choose a branch in the current checkout or an isolated workspace according to the task, and report exactly which candidate was tested.

## Workflow

1. **Branch in place when that is all**: name it `<type>/<slug>` (commit type, lowercase kebab-case slug), start from `HEAD` unless a base is named, and run `git switch -c <branch> <base>`. Stop if the branch exists; never stash or reset to switch.
1. **Pick the isolation**: use `git worktree add --detach <dest> <rev>` to review a commit, or `git worktree add -b <branch> <dest> <base>` to implement. Use a disposable clone when the candidate includes uncommitted files or must not share refs and hooks with the source.
1. **Materialize a dirty candidate**: `git clone --no-hardlinks --no-checkout <source> <dest>`, check out the recorded `HEAD` detached, then overlay the selected bytes, modes, symlinks (not followed), and deletions from `git ls-files --cached --others --exclude-standard -z`. Leave ignored caches, environments, and secrets out, and compare the snapshot with the source before running anything.
1. **Run the gate in the destination**: read its tasks and hooks first, and isolate environments, ports, databases, and caches the tests mutate. For mise, prefix commands with `MISE_TRUSTED_CONFIG_PATHS=<dest>` instead of `mise trust`, which outlives the clone.
1. **Return and clean up**: review formatter edits before transferring them, preserve the source index, then remove only the worktree or clone this task created once no unique work remains. Report the revision, included dirty changes, gate, and any retained workspace.

## Gotchas

- **A clean HEAD is a different candidate**: a passing worktree does not validate uncommitted edits in the source.
- **Worktrees share Git state**: linked worktrees share objects, refs, configuration, and hooks; they are not a sandbox for untrusted code.
- **No forced reuse**: never use force, stash, reset, or broad clean commands to free a busy branch or dirty destination.
- **Neutralize external symlinks**: a copied link into the source defeats isolation; replace it with fixture data or stop that test.

## Documentation

- [Git worktree](https://git-scm.com/docs/git-worktree) · [Git clone](https://git-scm.com/docs/git-clone)
- Companion skills: [mise](../../../mise/SKILL.md) (gates), [resolve-conflicts](../resolve-conflicts.md) (integration conflicts).
