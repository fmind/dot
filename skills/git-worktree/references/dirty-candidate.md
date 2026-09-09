# Materialize a Dirty Candidate

Use a disposable local clone when the tested files must include uncommitted work. A linked worktree starts from a commit and does not copy that work automatically.

1. **Freeze the selection**: record HEAD, staged and unstaged diffs, and explicit untracked paths. For the complete working-tree candidate, inventory paths with `git ls-files --cached --others --exclude-standard -z`; consume NUL-delimited paths, not shell word splitting. For a staged-only candidate, use the index blobs and modes, not working-tree bytes.
1. **Create the clone**: `git clone --no-hardlinks --no-checkout <source> <fresh-destination>`, then `git -C <destination> checkout --detach <recorded-head>`. Keep Git metadata independent; do not copy the source `.git` directory. Inspect checkout hooks and local Git configuration before invoking project commands.
1. **Overlay the selection**: copy selected working-tree bytes, executable modes, and symlinks without following them. Apply tracked deletions in the destination. Preserve separate staged and unstaged evidence in the review record; a combined overlay alone cannot reproduce the original index selection.
1. **Handle special paths**: inspect submodules and LFS files explicitly. Ignored build output, environments, caches, and secrets are excluded by default; materialize only an explicitly needed safe fixture. Reject a destination path whose parent symlink escapes the disposable tree.
1. **Verify the snapshot**: compare selected path names, file bytes, executable modes, symlink targets, and deletions before execution. If the source changed during the copy, refresh the affected snapshot before claiming an exact candidate.
1. **Set the environment**: create dependencies in the clone through the native lockfile workflow. Remove inherited project-path overrides or point them at the clone. Preserve the real upstream URL only when a read-only check requires its metadata; do not redirect checks to a live deployment to satisfy them.
1. **Qualify and compare**: run the full gate, then compare the tested paths with the source again. If formatters changed files, review those edits before transferring them and rerun affected validation as needed. Concurrent source changes invalidate proof for those files.
1. **Finish**: preserve useful logs outside the source and verify the source index is unchanged. Dispose of only the clone created for this task once no unique work remains.

A filesystem copy is an execution workspace, not a backup of a running database. Use [data-migration](../../data-migration/SKILL.md) for consistent data snapshots.
