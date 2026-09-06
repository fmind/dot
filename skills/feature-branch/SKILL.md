---
name: feature-branch
description: Create and switch to a new git branch with conventional <type>/<slug> naming. Use when starting work that needs its own branch.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/feature-branch
  created: "2026-06-23"
  updated: "2026-09-05"
---

# Feature Branch

Create and switch to a `<type>/<slug>` branch from the selected base for the work the user described; [conventional-commit](../conventional-commit/SKILL.md) owns the commits that follow.

## Workflow

1. **Ask when the work is undescribed**: without a description, an issue reference, or a desired branch name, ask and stop.
1. **Inspect the tree**:

   ```bash
   git branch --show-current   # current branch
   git status --short          # uncommitted changes
   ```

1. **Derive the name** as `<type>/<slug>`:
   - `<type>`: a commit type from [conventional-commit](../conventional-commit/SKILL.md), usually `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, or `ci`.
   - `<slug>`: lowercase ASCII kebab-case, under 50 characters, no trailing punctuation.
1. **Reuse a valid name**: when the user's input already is a valid branch name, use it as is.
1. **Resolve the base**: use the user-specified base; otherwise state that the new branch starts at the current commit. Ask only if competing branch histories make the intended base unclear.
1. **Preserve a dirty tree**: record existing changes and let them stay in place when branching from the current commit. Do not stash, reset, or overwrite work to switch bases; resolve a conflicting target with the user.
1. **Create and switch**; if the branch already exists, stop and report it:

   ```bash
   git switch -c <branch>
   ```

1. **Report** only these two lines after success:

   ```text
   Branch: <branch>
   From: <parent-branch>
   ```

## Gotchas

- **No push**: the branch stays local; [github-pull-request](../github-pull-request/SKILL.md) pushes it with `-u` when the PR is opened.

## Documentation

- [Conventional Branch](https://conventionalbranch.org/)
- Companion skills: [conventional-commit](../conventional-commit/SKILL.md) (commit on the branch), [github-pull-request](../github-pull-request/SKILL.md) (open the PR).
