---
name: orphans
description: "Audit files chezmoi deployed but no longer manages; decide per path to keep, delete, or forget."
---

# Orphaned Targets

Deleting or renaming a chezmoi source leaves previously deployed files on disk. `dot orphan` reports them from `chezmoi state dump` and `chezmoi managed` without reading contents or deleting anything.

## Workflow

1. **List**: `dot doctor` warns with a count (`mise run full` already retires old `~/.config/mise/locks` graphs); run `dot orphan` or `dot orphan --json` (`dot.orphan/v1` `.targets[]`: `path`, `type`, `status`) after source renames/removals, releases retiring files, or stale-config symptoms.
1. **Classify `status`**:
   - `unchanged`: still matches chezmoi's last write; usually safe to remove.
   - `modified`: edited since deploy; another tool, timer, or `dot trust` may own it — inspect first.
   - `replaced`: file type changed (e.g. file → directory).
   - `empty` / `not-empty`: former managed directory; `not-empty` may hold live state.
   - `unreadable`: permission denied; report without escalating.
1. **Trace history**: check `git -C ~/.local/share/chezmoi log --oneline --diff-filter=DR -- '*<name>*'` and release notes for intentional handoffs to machine-local state.
1. **Act per path** within task authority:
   - **Obsolete leftover**: confirm no consumer remains, unload active units (`systemctl --user disable --now`, `launchctl bootout`), and delete; use `.chezmoiremove` when every machine should drop it.
   - **Intentionally kept or handed off**: run `chezmoi state delete --bucket=entryState --key=<absolute path>` (updates chezmoi bookkeeping only; keeps the file).
1. **Verify**: rerun `dot orphan` and report each removed, kept, or forgotten path.

## Boundaries

Treat `dot orphan` as evidence, never authorization: never bulk-delete, and never remove credentials, brain data, or `modified` paths without verifying their owner.
