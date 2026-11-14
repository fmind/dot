---
name: publish
description: "Commit, push atomic tags, publish via mise run release, and verify CI/CD."
---

# Publish `fmind/dot` Release

Execute only on `/dot-release` or an explicit release request after [Qualification](../SKILL.md#qualification) passes cleanly.

1. **Confirm authority**: `/dot-release` or explicit release authority covers commits, pushing `main`, `mise run release`, and forward CI/CD fixes; stop if any gate stays red or needs a user decision.
1. **Commit and sync `main`**: group work into logical [Conventional Commits](../../../../skills/git-delivery/SKILL.md#commit-messages) (`git-cliff` groups sections from them), then `git fetch` and push `main` (`pre-push` runs network checks and tests). Integrate upstream moves without rewriting history only if commits are disjoint; otherwise stop.
1. **Check preconditions**: `dprint`, `git`, `git-cliff`, `mise`, and `uv` present; clean `main` matching fetched `origin/main`; next tag absent locally; at least one new Conventional Commit. Preserve unrelated work if preflight stops.
1. **Run from source** (`uv run --frozen --directory dot python -m dot_tasks.release` via `mise`):
   ```bash
   mise run release        # interactive
   mise run release -- -y  # non-interactive when authorized
   ```
   Updates `dot/pyproject.toml`, `CHANGELOG.md` (dprint-formatted), and `dot/uv.lock`, gates the bump (`check:network`, `test:starters`, `build`, `check:completions`), commits with visible Lefthook output, tags, runs `git push --atomic`, and runs `mise run deploy`.
1. **Verify CI/CD**: tag push triggers [cd.yml](../../../../.github/workflows/cd.yml) (read-only `gate` + `publish` creating the release). Watch CI (including macOS) and CD via `gh run list --workflow cd.yml --branch <tag>` and `gh run watch <id> --exit-status`, then verify `gh release view <tag>`. On failure, inspect `gh run view <id> --log-failed`, fix forward on `main`, and cut the next release per [recovery](recovery.md).
