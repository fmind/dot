---
name: git-add-commit-push
description: "Stage, commit, push, and recover hook failures within the authorized scope."
---

# Git Add, Commit, and Push

Stage, commit, and push authorized changes while preserving unrelated work and healing hook failures within scope ([commit messages](../SKILL.md#commit-messages)).

## Workflow

1. **Inspect scope and branch**: check `git status --short --branch`, `git diff`, and `git diff --cached`; apply requested PR or branch rules via [git-worktree](git-worktree/GUIDE.md).
1. **Preserve the index**: keep existing staged selections; when staging, add only intended files/hunks (never `git add -A`), and stop if nothing authorized remains.
1. **Commit**: run `git commit -m "<subject>"` with a [Conventional Commits](../SKILL.md#commit-messages) subject.
1. **Heal pre-commit**: fix the root cause, format only intended paths (use an isolated candidate for whole-tree formatters on dirty trees), restage authorized fixes, and retry.
1. **Push**: confirm the remote target and run `git push` (dot's `push.autoSetupRemote` and `push.default=current` handle new branches without `-u`).
1. **Heal pre-push**: fix failing tests or `check:network` checks without weakening assertions; amend only the unpublished commit just created when those fixes belong to its scope (else make a separate authorized commit), and reconcile remote refs before retrying uncertain pushes.
1. **Verify**: confirm the remote ref matches the local SHA and report subject, SHA, and destination (hosted CI is separate).

## Gotchas

- **Keep hooks enabled**: never pass `--no-verify` or `LEFTHOOK=0`; if a Lefthook config exists, verify `lefthook check-install` exits 0 (run `mise run install` on fresh clones) and let hooks run checks once rather than duplicating them beforehand.
- **Split mixed dirty trees in a detached worktree**: partial staging hides unstaged hunks during Lefthook runs, testing a tree no commit holds. Capture `snap=$(git stash create)` (plus untracked files), build commits sequentially in a detached [worktree](git-worktree/GUIDE.md) at `HEAD` with hooks active using `git checkout "$snap" -- <paths>` or context patches from `git diff HEAD "$snap" -- <path>` (never `git apply --unidiff-zero`, which misplaces insertions after skipped hunks), then `git reset <tip>` in the source checkout and verify `git diff` holds only unrelated edits.
- **Preserve commit/tag signing**: never pass `--no-gpg-sign` or override `commit.gpgSign`, create signed tags via `git tag NAME -m MSG` (explicit `-a` skips signing), and report signing errors directly.
- **Never amend user or published commits** during hook recovery.
- **Classify rejected pushes**: separate branch protection (open a PR), non-fast-forward races (preserve both histories), and auth failures.

## Documentation

- [Git push](https://git-scm.com/docs/git-push) · [lefthook](../../github-actions/references/lefthook.md)
- Companion skills: [git-worktree](git-worktree/GUIDE.md), [pull-request](../../gh/references/pull-request.md), [resolve-conflicts](resolve-conflicts.md).
