---
name: orphans
description: "Find files chezmoi deployed but no longer manages, then decide per path whether to keep, remove, or forget them."
---

# Orphaned Targets

Deleting or renaming a chezmoi source never removes what an earlier apply deployed. `dot orphan` lists those leftovers from chezmoi's persistent state; it only reports, and every cleanup decision stays with you or the user.

## Workflow

1. **List**: run `dot orphan` (or `dot orphan --json` for `path`, `type`, `status`) after removing or renaming sources, after a release that retired files, or when a machine behaves as if an old config is still active. It needs `chezmoi` and reads `chezmoi state dump` plus `chezmoi managed`; it prints paths only, never contents.
1. **Read the status**:
   - `unchanged`: the file or symlink still holds chezmoi's last write, so nothing else has claimed it. Usually a safe leftover.
   - `modified`: changed since chezmoi wrote it. Another owner may now manage the path (a tool's own state file, a brain's timer, a `dot trust` target); inspect before touching it.
   - `replaced`: now a different type (for example, a file became a directory).
   - `empty` / `not-empty`: a formerly managed directory; a non-empty one may hold live data.
   - `unreadable`: permission denied; report it rather than escalating.
1. **Find the reason**: search the source history with `git -C ~/.local/share/chezmoi log --oneline --diff-filter=DR -- '*<name>*'` and the release notes. A path can be orphaned on purpose (ownership moved to a tool or a machine-local file).
1. **Decide per path**, within the task's authority:
   - Leftover no longer used: delete it (a secret seed, an old hook duplicating a new one, a retired unit), after confirming nothing else reads it. Unload services first (`systemctl --user disable --now`, `launchctl bootout`).
   - Now owned elsewhere or intentionally kept: leave it and forget it with `chezmoi state delete --bucket=entryState --key=<absolute path>` so it stops being reported.
   - To clean every machine: add a `remove_` source marker instead of deleting locally; the contract test lists outstanding markers until each has shipped.
1. **Recheck**: rerun `dot orphan` and report what was removed, kept, or forgotten, and why.

## Boundaries

Treat `dot orphan` as evidence, not authorization: never bulk-delete its output, and never delete credentials, brain data, or a `modified` path without confirming its current owner. `chezmoi state delete` changes only chezmoi's bookkeeping; the file stays in place.
