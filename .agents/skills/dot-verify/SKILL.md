---
name: dot-verify
description: "Qualify the fmind/dot working tree before a release: review changes, sync docs, run every gate, and smoke-test the dot CLI."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-verify
  created: "2026-09-24"
  updated: "2026-09-24"
---

# Verify Dot

Prove that the current checkout (committed and uncommitted work) is correct, documented, and releasable. This skill sequences the owners; [repository-review](../../../skills/repository-review/SKILL.md), [repository-docs](../../../skills/repository-docs/SKILL.md), [dot-development](../dot-development/SKILL.md), and [dot-skills](../dot-skills/SKILL.md) own the details. Verification fixes findings in place but never commits, pushes, or releases; [dot-release](../dot-release/SKILL.md) owns that.

## Workflow

1. **Baseline**: record `git status --short`, staged and unstaged diffs, untracked files, and `git fetch` state against `origin/main`. Commits already on `main` since the last tag are part of the candidate; preserve unrelated work.
1. **Review the change set**: list what changed since the last tag (`git diff <tag>`) plus uncommitted work, excluding generated locks. For large sets, fan out read-only reviews by area (dot Python, chezmoi and host config, docs and skills) and verify each finding against code or real local data before fixing. Behavior fixes need regression tests per dot-development.
1. **Synchronize docs**: check `README.md`, `AGENTS.md`, `dot_agents/AGENTS.md`, `.agents/skills/`, and `skills/` against the code: removed or renamed files, commands and flags (`uv run --frozen --directory dot dot <command> --help`), tasks (`mise tasks`), and JSON fields. Bump `updated:` on changed skills; run `mise run format:skills` for guide indexes; follow dot-skills for catalog changes.
1. **Run the gates**: `mise run all`, then the host checks it omits: `mise run check:completions` and `mise run test:starters`. Check `dot agent context --source . --project . --check`. Rerun only what a later fix invalidates.
1. **Smoke-test the CLI** from the checkout: `--help` for every top-level command, then read-only commands: `doctor`, `agent doctor`, `agent context --check`, `config validate`, `status --stats`, `orphan`, `cache`, `prune all --dry-run`, `trust --dry-run .`, and `agent stats --no-sync`. Every exit code must be 0 or explained.
1. **Check the workstation** when tools or dotfiles changed: `chezmoi diff` preview, `dot orphan` for retired targets (report, never delete), and `mise run verify`. `STALE` for the installed `dot` is expected until release or `mise run deploy`.
1. **Report**: fixed findings, deliberately left items with reasons, each check and its result, and confirm the tested snapshot equals the candidate (the working tree after the last fix).

## Gotchas

- **Scanner hits in generated tool locks**: universal uv locks list versions for old Python markers. Confirm the installed environment's resolved version; record a false positive as a path-scoped `.trivyignore.yaml` entry with a `statement`, never by lowering severity.
- **Removal markers**: a new `remove_` source must be listed in the outstanding set of `test_python_only_owned_sources_and_retired_tool_cleanup` until it has shipped everywhere.
- **Upstream CLI changes**: an upgraded tool can drop its completion generator or tighten a pinned dependency; fix the source configuration and its skill, not the deployed copy.
