---
name: git-add-commit-push
description: "Stage, commit, push, and recover hook failures within the authorized scope."
---

# Git Add, Commit, and Push

Stage, commit, and push the authorized change, preserving existing work and repairing hook failures within that scope. The [commit message rules](../SKILL.md#commit-messages) own the subject.

## Workflow

1. **Resolve scope and branch**: inspect `git status --short --branch`, `git diff`, and `git diff --cached`; follow an explicitly requested PR flow or the repository's branch policy through [git-worktree](git-worktree/GUIDE.md).
1. **Preserve the index**: retain an existing staged selection. When staging is requested, add only the intended files or hunks; a dirty tree or an empty index does not authorize `git add -A`. Stop when there is no authorized change to commit.
1. **Commit once**: write the subject with the [commit message rules](../SKILL.md#commit-messages), then run `git commit -m "<subject>"` once.
1. **Heal pre-commit**: read the failure, fix its cause, and rerun the affected check or case. Format only the intended paths; use an isolated candidate for a whole-tree formatter when unrelated work exists. Review and restage only the authorized fixes before retrying.
1. **Push the candidate**: verify the destination, then `git push`; dot's gitconfig sets `push.autoSetupRemote` and `push.default=current`, so a new branch needs no `-u`. A push to another repository or branch needs its own scope.
1. **Heal pre-push**: reproduce the failing pre-push check (tests, network checks) and fix the cause without weakening assertions. Amend only the unpublished commit created by this flow when the authorized commit scope includes those fixes; otherwise make a separate authorized correction. Reconcile remote state before retrying an uncertain push.
1. **Verify and report**: compare the remote branch SHA with the committed SHA, then report subject, commit, and destination. CI for that commit is a separate result.

## Gotchas

- **Hooks own delivery checks**: keep hooks enabled (never `--no-verify` or `LEFTHOOK=0`) and let the authorized commit/push run their checks. When the repository has a lefthook config, `lefthook check-install` must exit 0; a fresh clone has no hooks and commits unchecked, so run the repository's install task first. Do not duplicate the same checks immediately beforehand unless diagnosing a failure or satisfying an additional repository requirement. Reuse passing results while relevant inputs remain unchanged; fix failures without suppressing them. CI qualification remains separate.
- **Split a mixed tree in a worktree**: when one dirty tree becomes several commits, partial staging in the checkout makes lefthook hide unstaged hunks and check a tree no commit contains. Snapshot the tree with `snap=$(git stash create)` (plus untracked paths), build the commits in order in a detached [worktree](git-worktree/GUIDE.md) at `HEAD` with hooks on, taking whole files with `git checkout "$snap" -- <paths>` and partial files as context patches from `git diff HEAD "$snap" -- <path>`; never `git apply --unidiff-zero`, which places a pure insertion by line number once an earlier hunk is skipped. Then `git reset <tip>` in the checkout and confirm `git diff` shows only unrelated work.
- **Keep commit signing on**: where the machine has a signing key, commits and annotated tags are signed (create tags with `git tag NAME -m MSG`; an explicit `-a` skips signing); never pass `--no-gpg-sign` or override `commit.gpgSign`, and report a signing failure with its cause instead.
- **Existing commits belong to the user**: never amend an earlier or published commit as routine hook healing.
- **Diagnose a rejected push**: distinguish branch protection from a non-fast-forward race or authentication failure; use a PR for protection and preserve both histories when the remote advanced.

## Documentation

- [Git push](https://git-scm.com/docs/git-push) · [lefthook](../../github-actions/references/lefthook.md)
- Companion skills: [git-worktree](git-worktree/GUIDE.md), [pull-request](../../gh/references/pull-request.md), [resolve-conflicts](resolve-conflicts.md).
