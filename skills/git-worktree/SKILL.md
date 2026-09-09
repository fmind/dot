---
name: git-worktree
description: Isolate development or validation with Git worktrees and exact dirty-candidate copies. Use when work must leave another checkout and its staged selection intact.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/git-worktree
  created: "2026-09-09"
  updated: "2026-09-09"
---

# Git Worktree

Create the smallest isolated workspace that contains the intended candidate. [feature-branch](../feature-branch/SKILL.md) owns branch naming; this skill owns isolation, candidate identity, and cleanup.

## Workflow

1. **Record the source**: inspect `git status --short`, `git diff`, `git diff --cached`, `git rev-parse HEAD`, and `git worktree list --porcelain`. Identify whether the candidate is a commit, the index, or selected working-tree changes.
1. **Choose isolation**: use a linked worktree for a committed revision or new branch. Use the [dirty candidate procedure](references/dirty-candidate.md) when validation must include uncommitted files, or when checks must not share Git refs or hooks with the source.
1. **Create a fresh destination**: choose a new sibling or temporary path outside the source. For a read-only review of committed code, use `git worktree add --detach <destination> <revision>`; for implementation, use `git worktree add -b <new-branch> <destination> <base>`.
1. **Inspect execution inputs**: read the destination's tasks and hooks before running them; isolate virtual environments, build output, coverage, ports, databases, and caches that tests mutate. Do not copy credentials or reuse a live database to make a fixture pass.
1. **Run the owning gate**: invoke the project's commands from the destination. Formatter output changes the tested candidate; compare it with the intended source before transferring proof or applying any resulting edits.
1. **Return only intended changes**: review the destination diff, transfer task-owned changes when authorized, and preserve the source index. Commits, pushes, and merges follow the user's requested delivery flow.
1. **Clean up deliberately**: inspect destination status and recover useful artifacts first. Use `git worktree remove <destination>` for an owned clean linked worktree; retain a dirty one until its changes are accounted for. Remove only the recorded disposable clone for a copied candidate.
1. **Report identity**: revision, included dirty changes, executed gate, source-versus-tested differences, and any retained workspace.

## Gotchas

- **A clean HEAD is a different candidate**: a passing worktree does not validate uncommitted edits in the source.
- **Shared Git state**: linked worktrees have separate indexes but share objects, refs, and usually repository configuration and hooks. They are not a security sandbox; do not run untrusted code merely because it is in a worktree.
- **No forced reuse**: do not use force, stash, reset, or broad clean commands to make a busy branch or dirty destination available.
- **External symlinks**: inspect and replace writable links into the source with safe fixture data or stop that test; a copied symlink can defeat isolation.

## Documentation

- [Git worktree](https://git-scm.com/docs/git-worktree) · [Git clone](https://git-scm.com/docs/git-clone)
- Companion skills: [mise](../mise/SKILL.md) (gates), [resolve-conflicts](../resolve-conflicts/SKILL.md) (integration conflicts).
