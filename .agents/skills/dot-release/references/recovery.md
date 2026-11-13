---
name: recovery
description: "Recover failed fmind/dot release preflights, mid-bump gate failures, tags, or pushes."
---

# Release Recovery

Inspect `git status --short`, local commit/tag, and remote state before retrying ([release.py](../../../../dot/dot_tasks/release.py), [test_release.py](../../../../dot/tests/test_release.py)).

| Failure boundary                | Next action                                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Preflight failed                | Worktree and index remain intact; inspect `git status --short`, fix cause, rerun.                                             |
| Gate failed after prepare       | Revert prepared bump with `git restore --staged --worktree -- CHANGELOG.md dot/pyproject.toml dot/uv.lock`, fix cause, rerun. |
| Local tag already exists        | Confirm tag never reached remote, run `git tag -d <tag>`, rerun.                                                              |
| Commit created, tagging failed  | Nothing reached remote; fix cause and run the printed tag, push, and deploy commands.                                         |
| Atomic push failed              | Check remote state; reconcile upstream divergence without losing the release commit, then retry.                              |
| Push succeeded, `deploy` failed | Confirm remote commit, tag, and CD first, then rerun `mise run deploy`.                                                       |
| CD `gate` failed on pushed tag  | No release published; fix forward on `main` and cut the next version (never move tags or force-push).                         |
