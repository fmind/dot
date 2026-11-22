---
name: full-review
description: "Review diffs, PRs, or repos for readiness, smoke tests, HTTP/DNS probing (xh/hurl/doggo), dead code, and ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-22"
---

# Full Review

Deliver a fixed, proven tree on whole-repo runs or a read-only report on diff/PR/smoke runs. Defer to repo qualification skills (e.g., `dot-release`) when present, covering only gaps.

## Scope & Mode

Ask only when ambiguity alters scope, cost, or reversibility:

- **Scope**: diffs/PRs → [diff-review](references/diff-review.md); smoke-only → [smoke](references/smoke.md); ignores → [update-ignores](references/update-ignores/GUIDE.md); whole-repo → [repo-audit](references/repo-audit.md) (`deep` default inspects all tracked files; `upkeep` skips full inventory).
- **Mode**: whole-repo defaults to `fix`; diff/PR/smoke default to read-only `report` (isolate mutating formatters in a [worktree](../git-delivery/references/git-worktree/GUIDE.md); never approve PRs, comment, or deploy).

## Workflow

1. **Baseline & deterministic gates**: check `git status --short`, diffs, latest tag, and `git fetch` (preserve uncommitted work); read `AGENTS.md`, `README.md`, and skills; run `mise run check`, tests, [smoke](references/smoke.md), and scanners before spawning reviewers.
1. **Audit & fan out reviewers** (name any skip): run [repo-audit](references/repo-audit.md) on whole-repo runs; pre-capture frozen diff, manifest, gate logs, `vale --output=JSON`, `--help`, and PNG/DOM renders ([headless-review](../agent-harnesses/references/headless-review/GUIDE.md)), then fan out `fmind-review-completeness` + matching `fmind-review-*` roles ([subagent](../subagent/SKILL.md)) and verify every `loc`/`evidence` claim.
1. **Fix, prove, report**: land root-cause fixes + tests for verified `P0`–`P2` findings and `DELETIONS` (hold irreversible/costly/architectural forks); rerun `mise run all`, renders, and reviewers (max `2` rounds per [subagent](../subagent/SKILL.md)). Emit verdict (`ready` | `ready with caveats` | `blocked`), highest proven rung (`#proof-ladder`), `path:line` evidence, decisions, and gaps.

## Proof ladder

Claim only the highest proven rung (`source-ready` → `local-green` → `exact-head-CI` → `runtime-proven` → `deployed` → `release-published`) with artifact ID, env, command, and timestamp; list unproven boundaries.

## Severity

- **P0** active breach/data loss/outage · **P1** correctness/security/availability blocker · **P2** material edge-case/perf/test gap · **P3** minor nit.
- Stop editing once gates are green and verified `P0`–`P2` findings plus `DELETIONS` reach `PASS` (defer `P3`/speculative ideas without mutating; never oscillate). Cite `path:line`, trigger, evidence, impact, and minimal fix (or `"none material"`).

## Task guides

<!-- guides:start -->

- [diff-review](references/diff-review.md): Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings.
- [http-probing](references/http-probing.md): Probe HTTP with xh, run hurl smoke checks, query DNS with doggo.
- [smoke](references/smoke.md): Smoke-test every repo task and CLI command; warnings count as failures.
- [update-ignores](references/update-ignores/GUIDE.md): Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack.

<!-- guides:end -->

## Documentation

- [Google Code Review](https://google.github.io/eng-practices/review/) · [Vulture](https://github.com/jendrikseipp/vulture) · [ast-grep](https://ast-grep.github.io/) · Companions: [pull-request](../github/references/pull-request.md), [issues](../github/references/issues/GUIDE.md), [cloud-run](../gcloud/references/cloud-run/GUIDE.md), [continuation](../agent-harnesses/references/task-prompts/references/continuation.md).
