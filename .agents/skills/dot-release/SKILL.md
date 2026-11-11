---
name: dot-release
description: "Prepare, publish, verify, and recover fmind/dot releases via mise run release."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-release
  created: "2026-07-08"
  updated: "2026-11-11"
---

# Dot Release

Ship releases through the repository task; the global [release guide](../../../skills/git-delivery/references/release/GUIDE.md) owns generic versioning, while this skill owns `fmind/dot` preconditions and recovery.

## Workflow

1. **Confirm authority**: `/dot-release` or an explicit release request authorizes verification fixes, commits, pushing `main`, `mise run release`, and forward CI/CD fixes; reading this skill for review or audit does not.
1. **Qualify first**: run [dot-verify](../dot-verify/SKILL.md) and fix findings. Stop if any gate stays red or needs a user decision.
1. **Commit and sync `main`**: group work into logical [Conventional Commits](../../../skills/git-delivery/SKILL.md#commit-messages) (used by `git-cliff`), then `git fetch` and push `main` (pre-push runs network checks and tests). Integrate upstream moves without rewriting history only if commits are disjoint; otherwise stop.
1. **Check preconditions**: `dprint`, `git`, `git-cliff`, `mise`, and `uv` present; clean `main` matching fetched `origin/main`; next tag absent locally; at least one new Conventional Commit. Preserve unrelated work if preflight stops.
1. **Run from source** (`uv run --frozen --directory dot python -m dot_tasks.release` via `mise`):
   ```bash
   mise run release        # interactive (after dot-verify)
   mise run release -- -y  # non-interactive when authorized
   ```
   The task updates only `dot/pyproject.toml`, `CHANGELOG.md` (dprint-formatted), and `dot/uv.lock`, gates the bump (`check:network`, `test:starters`, `build`, `check:completions`), commits with visible Lefthook output, tags, runs `git push --atomic`, and runs `mise run deploy`.
1. **Verify CI/CD**: tag push triggers [cd.yml](../../../.github/workflows/cd.yml) (read-only `gate` runs `mise run all` + `git-cliff`; checkout-free `publish` with `contents: write` creates the GitHub release). Watch both CI (including macOS) and CD via `gh run list --workflow cd.yml --branch <tag>` and `gh run watch <id> --exit-status`, then confirm `gh release view <tag>`. On failure, inspect `gh run view <id> --log-failed`, fix forward on `main` (never rerun to mask flakes), and cut the next release per [Recovery](#recovery) if CD failed.

## Recovery

Inspect `git status --short`, local commit/tag, and remote state before retrying ([release.py](../../../dot/dot_tasks/release.py), [test_release.py](../../../dot/tests/test_release.py)).

| Failure boundary                | Next action                                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Preflight failed                | Worktree and index remain intact; inspect `git status --short`, fix cause, rerun.                                             |
| Gate failed after prepare       | Revert prepared bump with `git restore --staged --worktree -- CHANGELOG.md dot/pyproject.toml dot/uv.lock`, fix cause, rerun. |
| Local tag already exists        | Confirm tag never reached remote, run `git tag -d <tag>`, rerun.                                                              |
| Commit created, tagging failed  | Nothing reached remote; fix cause and run the printed tag, push, and deploy commands.                                         |
| Atomic push failed              | Check remote state; reconcile upstream divergence without losing the release commit, then retry.                              |
| Push succeeded, `deploy` failed | Confirm remote commit, tag, and CD first, then rerun `mise run deploy`.                                                       |
| CD `gate` failed on pushed tag  | No release published; fix forward on `main` and cut the next version (never move tags or force-push).                         |

## Documentation

- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companions: [dot-verify](../dot-verify/SKILL.md), [dot-development](../dot-development/SKILL.md), [commit messages](../../../skills/git-delivery/SKILL.md#commit-messages).
