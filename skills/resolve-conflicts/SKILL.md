---
name: resolve-conflicts
description: Resolve git merge or rebase conflicts by reading both sides, keeping the intent of each change, then continuing and re-running the gate. Use when a merge or rebase conflicts.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/resolve-conflicts
  created: "2026-09-03"
  updated: "2026-09-11"
---

# Resolve Conflicts

Finish a stopped `git merge` or `git rebase` by understanding what each side meant, not by picking a side. Do not abort merely to hide a conflict; abort and report when the operation itself targets the wrong base or cannot safely continue. Never "take ours" unless history shows the incoming change is obsolete. Branch naming lives in [Git branch preparation](../git-worktree/SKILL.md); committing and pushing in [git-add-commit-push](../git-add-commit-push/SKILL.md).

## Workflow

1. **Map the state**: identify which operation stopped, the current and incoming commits, and every conflicted file before editing.
   ```bash
   git status --short                    # UU both modified; AU, UA, DU, UD: added or deleted on one side
   git diff --name-only --diff-filter=U
   git rev-parse -q --verify MERGE_HEAD  # merge only
   git rev-parse -q --verify REBASE_HEAD # rebase only
   ```
1. **Read both intents**: inspect the three index stages and operation-specific history before touching a hunk. During a rebase, `ours` is the branch being rebased onto and `theirs` is the commit being replayed.
   ```bash
   git show :1:<file>                    # common ancestor
   git show :2:<file>                    # ours; rebase target during a rebase
   git show :3:<file>                    # theirs; replayed commit during a rebase
   git log --merge --oneline -- <file>   # merge: commits from both heads touching the file
   git show REBASE_HEAD -- <file>        # rebase: the commit currently being replayed
   ```
1. **Resolve semantically**: write the code that satisfies both intents (renamed function plus new caller, both new tests, merged config keys). When intents are incompatible, keep the one matching the merge's goal and record the trade-off in the commit body. Do not invent new behavior, and remove every `<<<<<<<`, `=======`, `>>>>>>>` marker.
1. **Continue**: stage the resolved files and resume; repeat per commit during a rebase.
   ```bash
   git add <file>...
   git rebase --continue   # or: git merge --continue
   ```
1. **Prove it**: Run the full gate (`mise run all`); if the tree carries unrelated changes and the gate write-formats, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)). Fix what the merge broke before pushing.
1. **Push only when already authorized**: a rewritten private branch may need `git push --force-with-lease`; resolving conflicts alone does not authorize that history update, and never force-push a shared branch (`main`, or one others build on), merge into it instead.

## Gotchas

- **Show the ancestor**: `git config merge.conflictStyle zdiff3` puts the base version inside the markers so both sides' edits are visible.
- **Lockfiles and generated code**: resolve source manifests first, use either generated side only as a starting point, then run `uv lock` or the owning generator and review the regenerated diff.
- **Deleted on one side**: `DU` or `UD` means one side removed the file; find out why before restoring it.
- **Rebase repeats**: the same hunk can conflict on several commits; `git config rerere.enabled true` replays a recorded resolution.
- **Stop when unsure**: if intent cannot be recovered from history, ask the author instead of guessing.

## Documentation

- [git merge](https://git-scm.com/docs/git-merge#_how_to_resolve_conflicts) · [git rebase](https://git-scm.com/docs/git-rebase) · [git rerere](https://git-scm.com/docs/git-rerere)
- Adapted from [mattpocock/skills resolving-merge-conflicts](https://github.com/mattpocock/skills/blob/321658273cb1d20b76026717d027d505790106d4/skills/engineering/resolving-merge-conflicts/SKILL.md).
- Companion skills: [git-add-commit-push](../git-add-commit-push/SKILL.md) (commit and push), [repository-history](../repository-history/SKILL.md) (why a change exists), [mise](../mise/SKILL.md) (the gate).
