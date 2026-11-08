---
name: resolve-conflicts
description: "Resolve Git merge or rebase conflicts by both sides' intent; verify the result."
---

# Resolve Conflicts

Finish a stopped `git merge` or `git rebase` by combining both sides' intent, not by picking a side. Aborting can discard resolution work, so report a wrong base or unsafe state before an authorized abort.

## Workflow

1. **Map the state**: `git log --merge --oneline -- <file>` lists both sides' commits, and covers a rebase since Git 2.45.
1. **Continue**: regenerate lockfiles and generated code with their owner (`uv lock`) instead of merging them by hand, stage the result, then `GIT_EDITOR=true git rebase --continue` (or `merge --continue`) to keep the prepared message.
1. **Prove it**: run the repository's owning gate (e.g. `mise run all`); when the tree carries unrelated changes, apply the [dirty-tree rule](../../mise/SKILL.md#gotchas).
1. **Push only when already authorized**: a rewritten private branch may need `git push --force-with-lease`; resolving conflicts alone does not authorize that history update. Never force-push a shared branch (`main`, or one others build on); merge into it instead.

## Gotchas

- **Rely on the managed Git config**: dot's gitconfig enables `merge.conflictStyle=zdiff3` (markers show the base) and `rerere` globally; on another machine, never persist those settings without consent.

## Documentation

- [git merge](https://git-scm.com/docs/git-merge#_how_to_resolve_conflicts) · [git rebase](https://git-scm.com/docs/git-rebase)
- Adapted from [mattpocock/skills resolving-merge-conflicts](https://github.com/mattpocock/skills/blob/321658273cb1d20b76026717d027d505790106d4/skills/engineering/resolving-merge-conflicts/SKILL.md) (removed upstream in `daa01d8`).
- Companion skills: [git-add-commit-push](git-add-commit-push.md) (commit and push), [mise](../../mise/SKILL.md) (the gate).
