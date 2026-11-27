---
name: full-review
description: "Code review and readiness audits for diffs, PRs, or repos: smoke tests, HTTP/DNS probing (xh/hurl/doggo), dead code, and ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-25"
---

# Full Review

Deliver a fixed, proven tree on whole-repo runs or a read-only report on diff/PR/smoke runs. Defer to repo qualification skills (e.g., `dot-release`), covering only gaps.

## Scope & Mode

- **Scope**: diffs/PRs → [diff-review](references/diff-review.md); smoke → [smoke](references/smoke.md); ignores → [update-ignores](references/update-ignores/GUIDE.md); whole-repo → [repo-audit](references/repo-audit.md) (`deep` checks all tracked files; `upkeep` skips inventory).
- **Mode**: whole-repo defaults to `fix`; diff/PR/smoke default to `report` (isolate formatters in a [worktree](../git-delivery/references/git-worktree/GUIDE.md); never approve PRs, comment, or deploy).

## Workflow

1. **Baseline & gates**: inspect `git status --short`, diffs, tag, `git fetch` (keep dirty work); read `AGENTS.md`/`README.md`/skills; run repo gates (e.g., `mise run check` / `all`), tests, [smoke](references/smoke.md), scanners.
1. **Audit & review**: run [repo-audit](references/repo-audit.md) on whole-repo runs, then run the [subagent](../subagent/SKILL.md) critic loop aligned with optional project `Priorities` (name skips).
1. **Fix & prove**: fix verified `P0`–`P1`s + tests balanced per [balancing](../subagent/references/balancing.md) (quick `P2`/`DELETIONS` once; hold architectural forks), then rerun repo gates and reviewers only for fixed `P0`–`P1` blockers ([subagent](../subagent/SKILL.md)).
1. **Report & ratchet**: emit verdict (`ready` | `ready with caveats` | `blocked`), [proof ladder](#proof-ladder) rung, `path:line` evidence, a compact `Trade-Offs` table whenever `>= 2` reviewers collide or a `P0`/`P1` is downgraded/deferred, decisions, gaps; ratchet recurring `P1`s (`>= 2`) via [lesson-learned](../skillify/references/lesson-learned.md).

## Supagent Routing

Pick `1–2` targeted roles on diffs (up to `3` on whole-repo runs) aligned with optional `AGENTS.md` `Priorities` ([subagent](../subagent/SKILL.md)): `fmind-review-code` plus peers (`fmind-review-python`, `fmind-review-shell`, `fmind-review-test`, `fmind-review-sre`, `fmind-review-simplicity`). Anchor with `fmind-review-completeness` on multi-surface changes; isolate `fmind-review-factcheck` on secret-bearing repos ([cross-harness-agents](../agent-harnesses/references/cross-harness-agents.md#permission-limits)).

## Proof ladder

Claim only the highest proven rung (`source-ready` → `local-green` → `exact-head-CI` → `runtime-proven` → `deployed` → `release-published`) with artifact ID, env, command, and timestamp.

## Severity

- Use the canonical **`P0` / `P1` / `P2`** severity scale and arbitration rules in [balancing](../subagent/references/balancing.md) (omit nits; no `P3` tier).
- Cite `path:line`, trigger, evidence, impact, and minimal fix (or `"none material"`).

## Task guides

<!-- guides:start -->

- [diff-review](references/diff-review.md): Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings.
- [http-probing](references/http-probing.md): Probe HTTP with xh, run hurl smoke checks, query DNS with doggo.
- [smoke](references/smoke.md): Smoke-test every repo task and CLI command; warnings count as failures.
- [update-ignores](references/update-ignores/GUIDE.md): Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack.

<!-- guides:end -->

## Documentation

- [Google Code Review](https://google.github.io/eng-practices/review/) · [Vulture](https://github.com/jendrikseipp/vulture) · [ast-grep](https://ast-grep.github.io/) · [pull-request](../github/references/pull-request.md) · [issues](../github/references/issues/GUIDE.md) · [cloud-run](../gcloud/references/cloud-run/GUIDE.md) · [continuation](../agent-harnesses/references/task-prompts/references/continuation.md).
