---
name: resolve-conflicts
description: "Resolve Git merge or rebase conflicts by both sides' intent; verify the result."
---

# Resolve Conflicts

Finish a stopped `git merge` or `git rebase` by understanding what each side meant, not by picking a side. If the operation targets the wrong base or cannot safely continue, preserve existing resolutions and report the problem before an authorized abort; aborting can discard conflict-resolution work. Never "take ours" unless history shows the incoming change is obsolete.

## Workflow

1. **Map the state**: list every conflicted file (`git diff --name-only --diff-filter=U`) and the commits on both sides (`git log --merge --oneline -- <file>`, which also covers a rebase since Git 2.45) before editing.
1. **Resolve semantically**: write the code that satisfies both intents (renamed function plus new caller, both new tests, merged config keys). When intents are incompatible, keep the one matching the merge's goal and record the trade-off in the commit body. Do not invent new behavior, and remove every conflict marker.
1. **Continue**: stage the resolved files, then `GIT_EDITOR=true git rebase --continue` (or `merge --continue`) to keep the prepared message; repeat per commit during a rebase.
1. **Prove it**: run the repository's owning gate (e.g. `mise run all`); when the tree carries unrelated changes, apply the [dirty-tree rule](../../mise/SKILL.md#gotchas). Fix what the merge broke before pushing.
1. **Push only when already authorized**: a rewritten private branch may need `git push --force-with-lease`; resolving conflicts alone does not authorize that history update. Never force-push a shared branch (`main`, or one others build on); merge into it instead.

## Gotchas

- **Rely on the managed Git config**: dot's gitconfig enables `merge.conflictStyle=zdiff3` (markers show the base) and `rerere` globally; on another machine, never persist those settings without consent.
- **Regenerate lockfiles and generated code**: resolve source manifests first, use either generated side only as a starting point, then run `uv lock` or the owning generator and review the regenerated diff.
- **Investigate one-sided deletions first**: `DU` or `UD` means one side removed the file; find out why before restoring it.
- **Stop when unsure**: if intent cannot be recovered from history, ask the user for the decision; contacting the author requires authorization.

## Documentation

- [git merge](https://git-scm.com/docs/git-merge#_how_to_resolve_conflicts) · [git rebase](https://git-scm.com/docs/git-rebase)
- Adapted from [mattpocock/skills resolving-merge-conflicts](https://github.com/mattpocock/skills/blob/321658273cb1d20b76026717d027d505790106d4/skills/engineering/resolving-merge-conflicts/SKILL.md) (removed upstream in `daa01d8`).
- Companion skills: [git-add-commit-push](git-add-commit-push.md) (commit and push), [mise](../../mise/SKILL.md) (the gate).
