---
name: git-add-commit-push
description: Stage, commit (Conventional Commits), and push in one flow, healing lefthook pre-commit and pre-push failures. Use when committing and pushing work end-to-end.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-add-commit-push
  created: "2026-06-23"
  updated: "2026-09-08"
---

# Git Add, Commit, and Push

Stage, commit, and push the authorized change, preserving existing work and repairing hook failures within that scope. [conventional-commit](../conventional-commit/SKILL.md) owns the subject grammar.

## Workflow

1. **Resolve scope and branch**: inspect `git status --short --branch`, `git diff`, and `git diff --cached`. Direct work on `main` is allowed for `github.com/fmind/*`; follow an explicitly requested PR flow or the repository's branch policy through [feature-branch](../feature-branch/SKILL.md).
1. **Preserve the index**: retain an existing staged selection. When staging is requested, add only the intended files or hunks; a dirty tree or an empty index does not authorize `git add -A`. Stop when there is no authorized change to commit.
1. **Write the subject** with the [conventional-commit](../conventional-commit/SKILL.md) rules, then run `git commit -m "<subject>"` once.
1. **Heal pre-commit**: read the failure, fix its cause, and rerun the affected check through `mise run check`. Format only the intended paths; use an isolated candidate for a whole-tree formatter when unrelated work exists. Review and restage only the authorized fixes before retrying.
1. **Push the candidate**: verify the destination, then `git push -u origin "$(git branch --show-current)"`. A push to another repository or branch needs its own scope.
1. **Heal pre-push**: reproduce the failing `mise run test` case and fix the cause without weakening assertions. Amend only the unpublished commit created by this flow when the authorized commit scope includes those fixes; otherwise make a separate authorized correction. Reconcile remote state before retrying an uncertain push.
1. **Verify and report**: compare the remote branch SHA with the committed SHA, then report subject, commit, and destination. CI for that commit is a separate result.

## Gotchas

- **Hooks remain enabled**: fix failures; do not bypass hooks or suppress failing checks.
- **Existing commits belong to the user**: never amend an earlier or published commit as routine hook healing.
- **Rejected push**: distinguish branch protection from a non-fast-forward race or authentication failure; use a PR for protection and preserve both histories when the remote advanced.

## Documentation

- [Git push](https://git-scm.com/docs/git-push) · [lefthook](../lefthook/SKILL.md)
- Companion skills: [conventional-commit](../conventional-commit/SKILL.md), [feature-branch](../feature-branch/SKILL.md), [github-pull-request](../github-pull-request/SKILL.md), [resolve-conflicts](../resolve-conflicts/SKILL.md).
