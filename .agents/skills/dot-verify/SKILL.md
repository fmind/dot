---
name: dot-verify
description: "Qualify fmind/dot before release: review changes, sync docs, run gates, and smoke-test dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-verify
  created: "2026-09-24"
  updated: "2026-11-11"
---

# Verify Dot

Prove the checkout (committed and uncommitted work) is correct, synced, and releasable. Delegates domain rules to [full-review](../../../skills/full-review/SKILL.md), [repository-docs](../../../skills/repository-docs/SKILL.md), [dot-development](../dot-development/SKILL.md), and [dot-skills](../dot-skills/SKILL.md); fixes findings in place without committing, pushing, or releasing ([dot-release](../dot-release/SKILL.md)).

## Workflow

1. **Capture baseline**: record `git status --short`, staged/unstaged diffs, untracked files, and `git fetch` vs `origin/main`. Include commits since the last tag; preserve unrelated work.
1. **Review changes**: inspect `git diff <tag>` plus uncommitted work (excluding generated locks), fanning out read-only subreviews by area (`dot/`, chezmoi/harnesses, docs/skills) on large sets. Verify every finding against code or live data and add regression tests for behavior fixes.
1. **Sync docs & metadata**: align `README.md`, `AGENTS.md`, `dot_agents/AGENTS.md`, `.github/*.md`, `.agents/skills/`, and `skills/` with live `--help`, `mise tasks`, and JSON schemas; bump `updated:` on edited skills and run `mise run format:skills`.
1. **Run gates**: `mise run format` (isolated if unrelated edits exist), `mise run all`, `mise run check:completions`, and `mise run test:starters`; rerun anything invalidated by later fixes.
1. **Smoke-test `dot`** from repo root via `uv run --frozen --project dot dot` (`--directory dot` would resolve `.` to `dot/`): `--help` on every top-level command, then `doctor`, `agent doctor`, `agent context --check`, `config show`, `status`, `orphan`, `cache`, `prune --dry-run`, `prune --aggressive --dry-run`, `pull --dry-run`, `trust --dry-run .`, and `agent stats --no-sync` (all exit 0 or explained).
1. **Check workstation** when dotfiles or tools changed: `mise run diff`, `dot orphan` (report only), and `mise run doctor` (installed `dot` showing `STALE` is expected before `deploy`/release).
1. **Report**: fixed issues, deferred items with reasons, gate results, and confirmation that the verified snapshot matches the final tree.

## Gotchas

- **Scope scanner suppressions narrowly**: confirm resolved versions first; record confirmed false positives in a path-scoped `.trivyignore.yaml` (`statement` + `expired_at`, wired via `ignorefile:` in `dot_config/trivy/trivy.yaml`), never by lowering severity.
- **Fix upstream tool breaks at source**: update repo configs and skills rather than deployed copies when an upgraded CLI changes flags or completions.
