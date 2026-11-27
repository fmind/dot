---
name: git-add-commit-push
description: "Stage, commit, push, and recover hook failures within the authorized scope."
---

# Git Add, Commit, and Push

Stage, commit, and push authorized changes while preserving unrelated work and healing hook failures within scope ([commit messages](../SKILL.md#commit-messages)).

## Workflow

1. **Inspect scope and branch**: check `git status --short --branch`, `git diff`, and `git diff --cached`; apply requested PR or branch rules via [git-worktree](git-worktree/GUIDE.md).
1. **Preserve the index**: keep existing staged selections; when staging, add only intended files/hunks (never `git add -A`), and stop if nothing authorized remains.
1. **Validate before committing**: ensure affected tests, static gates, secret scans (`betterleaks`), and required `fmind-review-*` reviews have passed on the exact candidate (skipping redundant reruns when unchanged).
1. **Commit**: run `git commit -m "<subject>"` (adding `-m "<body>"` when root-cause or trade-off context helps future readers) following [Conventional Commits](../SKILL.md#commit-messages).
1. **Heal pre-commit**: fix the root cause, format only intended paths (use an isolated candidate for whole-tree formatters on dirty trees), restage authorized fixes, and retry.
1. **Push**: confirm the remote target and run `git push` (dot's `push.autoSetupRemote` and `push.default=current` handle new branches without `-u`).
1. **Heal pre-push**: fix failing tests or `check:network` checks without weakening assertions; amend only the unpublished commit just created when those fixes belong to its scope (else make a separate authorized commit), and reconcile remote refs before retrying uncertain pushes.
1. **Verify**: confirm the remote ref matches the local SHA and report subject, SHA, and destination (hosted CI is separate).

## Gotchas

- **Keep hooks enabled**: never pass `--no-verify` or `LEFTHOOK=0`; if a Lefthook config exists, verify `lefthook check-install` exits 0 (run `mise run install` on fresh clones), and note commit-only workflows still require running affected test/review gates explicitly because `pre-commit` hooks only run fast format/lint checks while full suites live in `pre-push`.
- **Split mixed dirty trees in a detached worktree**: partial staging hides unstaged hunks during Lefthook runs, testing a tree no commit holds.
  1. **Snapshot state**: save unrelated staged hunks (`git diff --cached -- <unrelated> > "$tmp/unrelated.patch"`), run `snap=$(git stash create)`, and guard `[ -n "$snap" ]` because `git stash create` returns empty when only untracked files changed; copy intended untracked files separately.
  1. **Commit in isolation**: open a detached [worktree](git-worktree/GUIDE.md) at `HEAD` with hooks active, apply tracked files via `git checkout "$snap" -- <paths>` or context patches from `git diff HEAD "$snap" -- <path>` (never `git apply --unidiff-zero`, which misplaces insertions after skipped hunks), copy intended untracked files, and commit sequentially to `<tip>`.
  1. **Reconcile safely**: verify clean hunk separation (diffing `<tip>` against `"$snap"` when non-empty confirms only unrelated tracked edits remain) before running `git reset <tip>` in the source checkout, restore unrelated staged hunks (`git apply --cached`), and verify `git diff` holds only unrelated edits.
- **Preserve commit/tag signing**: never pass `--no-gpg-sign` or override `commit.gpgSign`, create signed tags via `git tag NAME -m MSG` (explicit `-a` skips signing), and report signing errors directly.
- **Never amend user or published commits** during hook recovery.
- **Classify rejected pushes**: separate branch protection (open a PR), non-fast-forward races (preserve both histories), and auth failures.

## Documentation

- [Git push](https://git-scm.com/docs/git-push) · [lefthook](lefthook.md)
- Companion skills: [git-worktree](git-worktree/GUIDE.md), [pull-request](../../github/references/pull-request.md), [resolve-conflicts](resolve-conflicts.md).
