---
name: resolve-conflicts
description: "Resolve Git merge or rebase conflicts by both sides' intent; verify the result."
---

# Resolve Conflicts

Complete a paused `git merge` or `git rebase` by preserving both sides' intent rather than blindly taking `--ours` or `--theirs`; report wrong bases or unsafe states before aborting.

## Workflow

1. **Inspect both sides**: `git log --merge --oneline -- <file>` (supports rebase since Git 2.45).
1. **Resolve and continue**: regenerate lockfiles and generated outputs via their owners (`uv lock`) rather than hand-merging, stage resolved files, and run `GIT_EDITOR=true git rebase --continue` (or `merge --continue`).
1. **Gate**: run `mise run all` (apply the [dirty-tree rule](../../mise/SKILL.md#gotchas) if unrelated edits exist).
1. **Push only when authorized**: rewritten private branches require explicit authority for `git push --force-with-lease`; never force-push `main` or shared branches.

## Gotchas

- **Managed Git config**: `fmind/dot` enables `merge.conflictStyle=zdiff3` and `rerere` globally; never persist those settings on external machines without consent.

## Documentation

- [git merge](https://git-scm.com/docs/git-merge#_how_to_resolve_conflicts) · [git rebase](https://git-scm.com/docs/git-rebase)
- Adapted from [mattpocock/skills resolving-merge-conflicts](https://github.com/mattpocock/skills/blob/321658273cb1d20b76026717d027d505790106d4/skills/engineering/resolving-merge-conflicts/SKILL.md) (removed upstream in `daa01d8`).
- Companion skills: [git-add-commit-push](git-add-commit-push.md), [mise](../../mise/SKILL.md).
