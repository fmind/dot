---
name: dot-release
description: "Qualify, publish, verify, and recover fmind/dot releases via mise run release."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-release
  created: "2026-07-08"
  updated: "2026-11-13"
---

# Dot Release

Qualify `fmind/dot` and ship releases through `mise run release`. Run **Qualification** standalone when asked to verify the tree without committing or releasing; run **Publish** only on `/dot-release` or an explicit release request. The global [release guide](../../../skills/git-delivery/references/release/GUIDE.md) owns generic versioning; [full-review](../../../skills/full-review/SKILL.md), [repository-docs](../../../skills/repository-docs/SKILL.md), [dot-development](../dot-development/SKILL.md), and [dot-skills](../dot-skills/SKILL.md) own domain checks.

## Qualification

1. **Capture baseline**: record `git status --short`, staged/unstaged diffs, untracked files, and `git fetch` vs `origin/main`. Include commits since the last tag and preserve unrelated work.
1. **Review changes**: inspect `git diff <tag>` plus uncommitted work (excluding generated locks), fanning out read-only subreviews by area (`dot/`, chezmoi/harnesses, docs/skills) on large sets. Verify findings against code or live data and add regression tests for behavior fixes.
1. **Sync docs & metadata**: align `README.md`, `AGENTS.md`, `dot_agents/AGENTS.md`, `.github/*.md`, `.agents/skills/`, and `skills/` with live `--help`, `mise tasks`, and JSON schemas; bump `updated:` on edited skills and run `mise run format:skills`.
1. **Run gates**: `mise run format` (isolated if unrelated edits exist), `mise run all`, `mise run check:completions`, and `mise run test:starters`; rerun anything invalidated by later fixes.
1. **Smoke-test `dot`** from repo root via `uv run --frozen --project dot dot` (`--directory dot` resolves `.` to `dot/`): `--help` on every top-level command, then `doctor`, `agent doctor`, `agent context --check`, `config show`, `status`, `orphan`, `cache`, `prune --dry-run`, `prune --aggressive --dry-run`, `pull --dry-run`, `trust --dry-run .`, and `agent stats --no-sync` (all exit 0 or explained).
1. **Check workstation** when dotfiles or tools changed: `mise run diff`, `dot orphan` (report only), and `mise run doctor` (installed `dot` showing `STALE` is expected before `deploy`/release). Stop here on qualification-only runs and report fixed/deferred items and gate results.

## Publish

1. **Confirm authority**: `/dot-release` or an explicit release request authorizes commits, pushing `main`, `mise run release`, and forward CI/CD fixes; stop if any qualification gate stays red or needs a user decision.
1. **Commit and sync `main`**: group work into logical [Conventional Commits](../../../skills/git-delivery/SKILL.md#commit-messages) (used by `git-cliff`), then `git fetch` and push `main` (pre-push runs network checks and tests). Integrate upstream moves without rewriting history only if commits are disjoint; otherwise stop.
1. **Check preconditions**: `dprint`, `git`, `git-cliff`, `mise`, and `uv` present; clean `main` matching fetched `origin/main`; next tag absent locally; at least one new Conventional Commit. Preserve unrelated work if preflight stops.
1. **Run from source** (`uv run --frozen --directory dot python -m dot_tasks.release` via `mise`):
   ```bash
   mise run release        # interactive
   mise run release -- -y  # non-interactive when authorized
   ```
   Updates `dot/pyproject.toml`, `CHANGELOG.md` (dprint-formatted), and `dot/uv.lock`, gates the bump (`check:network`, `test:starters`, `build`, `check:completions`), commits with visible Lefthook output, tags, runs `git push --atomic`, and runs `mise run deploy`.
1. **Verify CI/CD**: tag push triggers [cd.yml](../../../.github/workflows/cd.yml) (read-only `gate` + `publish` creating the release). Watch CI (including macOS) and CD via `gh run list --workflow cd.yml --branch <tag>` and `gh run watch <id> --exit-status`, then verify `gh release view <tag>`. On failure, inspect `gh run view <id> --log-failed`, fix forward on `main`, and cut the next release per [recovery](references/recovery.md).

## Gotchas

- **Scope scanner suppressions narrowly**: confirm resolved versions first; record confirmed false positives in a path-scoped `.trivyignore.yaml` (`statement` + `expired_at`, wired via `ignorefile:` in `dot_config/trivy/trivy.yaml`), never by lowering severity.
- **Fix upstream tool breaks at source**: update repo configs and skills rather than deployed copies when an upgraded CLI changes flags or completions.

## Task guides

<!-- guides:start -->

- [recovery](references/recovery.md): Recover failed fmind/dot release preflights, mid-bump gate failures, tags, or pushes.

<!-- guides:end -->

## Documentation

- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companions: [dot-development](../dot-development/SKILL.md), [commit messages](../../../skills/git-delivery/SKILL.md#commit-messages).
