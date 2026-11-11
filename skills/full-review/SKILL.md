---
name: full-review
description: "Review diffs, PRs, or whole repos; check release readiness, incidents, smoke tests, dead code, config, and ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-11"
---

# Full Review

Handle "full review", "final check before release", "ready to ship", "review this diff or PR", "smoke-test everything", or repository upkeep. Whole-repo runs deliver a fixed, proven tree; diff/PR reviews deliver a read-only report. Defer to a repo-specific verify skill (such as `dot-verify`) when present, covering only what it omits.

## Arguments

State the parsed scope, exclusions, depth, mode, and requested follow-ups (release, commit, propagation—none by default) in one opening line; ask only when ambiguity alters scope, cost, or reversibility.

- **Scope**: diffs, patches, branches, PRs, and self-reviews run [diff-review](references/diff-review.md); smoke-only runs [smoke](references/smoke/GUIDE.md); ignore-only runs [update-ignores](references/update-ignores/GUIDE.md); everything else runs the whole-repo workflow below.
- **Depth**: `deep` (default) covers every in-scope tracked file; `upkeep` skips inventory and covers Current, Simple, Consistent, Documented, and security scans.
- **Mode**: whole-repo defaults to `fix`; diff, PR, and smoke-only default to read-only `report` (run mutating checks like `mise run format` only in a disposable [snapshot](../git-delivery/references/git-worktree/GUIDE.md), skip Fix/Prove and diff/PR Inventory, and rank by [severity](#severity)).

## Workflow

1. **Baseline**: inspect `git status --short`, staged/unstaged diffs, latest tag, and `git fetch` state (treat uncommitted work as part of the candidate—never discard or restage it), then run existing gates once to separate preexisting failures from regressions.
1. **Load decisions**: read `AGENTS.md`, `README.md`, skills, changelog, memory, `## Decisions`, and ADRs; revisit settled decisions only when new changes reopen them.
1. **Inventory**: group `git ls-files` (minus exclusions and generated/vendored paths) by area and track every area to reviewed—fan out read-only area passes to subagents on large repos, verifying every returned finding yourself.
1. **Audit dimensions** (name any out-of-scope skip):
   - **Works**: tasks and CLIs exit clean with zero warnings ([smoke](references/smoke/GUIDE.md)), deterministic failure/race tests pass, and authorized live endpoints respond read-only.
   - **Current**: check tools, deps, actions, and runtimes against latest stable ([upgrade-tools](../upgrade-tools/SKILL.md)), upgrading when requested.
   - **Simple**: delete dead code (vulture per [ruff](../python-stack/references/ruff.md#gotchas)), legacy paths, orphan files, stale config, unearned abstractions, and prose bloat ([trim](../trim/SKILL.md)).
   - **Consistent**: align metadata and versions across code, `pyproject.toml`, docs, GitHub ([repository](../gh/references/repository/GUIDE.md)), site, changelog, and tags; match stack/[bootstrap](../project-scaffolding/references/bootstrap.md) layout ([python-stack](../python-stack/SKILL.md)); route hooks and CI through [mise](../mise/SKILL.md); confirm locks/indexes/formatters regenerate cleanly; audit ignores ([update-ignores](references/update-ignores/GUIDE.md)).
   - **Secure and private**: audit secrets, permissions, dependencies, agent tools ([code-security](../code-security/SKILL.md)), repo visibility, and leak-free public content.
   - **Documented**: sync concise `README.md`, `AGENTS.md`, skills, and docs ([repository-docs](../repository-docs/SKILL.md)); extract recurring procedures via [skillify](../skillify/SKILL.md).
   - **Fast**: fix measured task, test, CI, or page bottlenecks ([performance](../python-stack/references/performance.md)).
1. **Fix**: land minimal, revertable fixes with regression tests for behavior defects; hold back irreversible, outward-facing, costly, or architectural changes as decisions.
1. **Prove**: rerun invalidated checks, then the full gate (`mise run all` or equivalent) on the exact candidate.
1. **Report**: verdict (`ready`, `ready with caveats`, or `blocked`), highest proven [proof ladder](#proof-ladder) rung, `path:line` fixes/findings with evidence, held-back decisions, and uncovered areas/services/credentials.
1. **Follow up on request**: commit/release via [git-delivery](../git-delivery/SKILL.md), propagate across repos, or resume at Fix on `"apply all"`.

## Proof ladder

Claim only the highest rung proven for this exact revision and environment (recording artifact ID, environment, command/observation, and timestamp; failed hard gates stay blocked, and list every gap above the rung):

- `source-ready`: source and config are reviewable.
- `local-green`: repository local gates pass.
- `exact-head-CI`: required CI passes on the exact commit.
- `runtime-proven`: built artifact passes across the authorized runtime boundary.
- `deployed`: artifact runs in the target environment.
- `release-published`: target audience can fetch the release ([release](../git-delivery/references/release/GUIDE.md)).

## Severity

- **P0**: active breach, irreversible data loss, or broad outage risk.
- **P1**: likely correctness, security, or availability defect blocking merge.
- **P2**: material edge-case, maintainability, performance, or test gap.
- **P3**: minor nit (include only on exhaustive review requests).

State `path:line`, reachable trigger, evidence, impact, and minimal fix (or `"none material"`), omitting style preferences and speculation.

## Task guides

<!-- guides:start -->

- [diff-review](references/diff-review.md): Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings.
- [smoke](references/smoke/GUIDE.md): Smoke-test every repo task and CLI command; warnings count as failures.
- [update-ignores](references/update-ignores/GUIDE.md): Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack.

<!-- guides:end -->

## Gotchas

- **Honor mode boundaries**: whole-repo fixes by default with full-tree coverage (never diff/sample-only); `report` mode never edits code, resolves/approves PRs, posts comments/issues, deploys, or publishes without approval.
- **Gate live targets & incidents**: staging, paid APIs, destructive fixtures, and customer data require approval. On live incidents, preserve evidence before containment, confirm authority before rotating/disclosing/mutating prod, prefer reversible mitigations, and leave external comms and ETAs to the owner.
- **Check concurrency & scale**: state the expected/assumed service load and check TOCTOU races, unshared per-process state, N+1 queries, and unbounded growth; never add layers, flags, or docs heavier than the bug they fix.

## Documentation

- Companion skills: [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md), [cloud-run](../cloud-run/SKILL.md), [continuation](../task-prompts/references/continuation.md).
