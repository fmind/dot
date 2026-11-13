---
name: full-review
description: "Review diffs, PRs, or whole repos; check release readiness, incidents, smoke tests, dead code, config, and ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-13"
---

# Full Review

Handle "full review", "final check before release", "ready to ship", "review this diff or PR", "smoke-test everything", or repo upkeep. Whole-repo runs deliver a fixed, proven tree; diff/PR reviews deliver a read-only report. Defer to a repo qualification skill (e.g., `dot-release` in `fmind/dot`) when present, covering only gaps.

## Arguments

State scope, exclusions, depth, mode, and follow-ups (none by default) in one opening line; ask only when ambiguity alters scope, cost, or reversibility.

- **Scope**: diffs/PRs run [diff-review](references/diff-review.md); smoke-only runs [smoke](references/smoke.md); ignores run [update-ignores](references/update-ignores/GUIDE.md); otherwise run whole-repo below.
- **Depth**: `deep` (default) reviews every tracked file; `upkeep` skips inventory.
- **Mode**: whole-repo defaults to `fix`; diff, PR, and smoke default to read-only `report` (run mutating formatters in a [worktree](../git-delivery/references/git-worktree/GUIDE.md), skip Fix/Prove and Inventory, rank by [severity](#severity)).

## Workflow

1. **Baseline & inventory**: inspect `git status --short`, diffs, latest tag, and `git fetch` state (preserve uncommitted work); run existing gates once to separate regressions. Read `AGENTS.md`, `README.md`, skills, changelog, and `## Decisions`, then fan out read-only `git ls-files` area reviews on large trees (verifying all findings).
1. **Audit dimensions** (name any skip):
   - **Works**: tasks/CLIs exit zero cleanly ([smoke](references/smoke.md)), failure/race tests pass, authorized endpoints respond.
   - **Current & Simple**: upgrade outdated deps on request ([upgrade-tools](../upgrade-tools/SKILL.md)); delete dead code (`vulture src --exclude .venv,tests`), structural clones (`ast-grep`), orphan files, stale config, and prose bloat ([trim](../trim/SKILL.md)).
   - **Consistent & Secure**: align versions, metadata, [repo settings](../gh/references/repository/GUIDE.md), and [bootstrap](../project-scaffolding/references/bootstrap.md); wire CI/hooks via [mise](../mise/SKILL.md); audit ignores ([update-ignores](references/update-ignores/GUIDE.md)); scan secrets/deps (`code-security`, `sonar analyze`); sync [docs](../repository-docs/SKILL.md) and fix bottlenecks ([performance](../python-stack/references/performance.md)).
1. **Fix, prove, report**: land minimal fixes + regression tests (hold irreversible, costly, or architectural calls as decisions); rerun full gates (`mise run all`); report verdict (`ready`, `ready with caveats`, `blocked`), highest [proof ladder](#proof-ladder) rung, `path:line` evidence, held decisions, and gaps. Follow up via [git-delivery](../git-delivery/SKILL.md) only on request.

## Proof ladder

Claim only the highest proven rung (recording artifact ID, environment, command, timestamp; failed gates stay blocked, and list every unproven boundary):

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
- [smoke](references/smoke.md): Smoke-test every repo task and CLI command; warnings count as failures.
- [update-ignores](references/update-ignores/GUIDE.md): Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack.

<!-- guides:end -->

## Gotchas

- **Honor mode boundaries**: whole-repo fixes by default with full-tree coverage (never diff/sample-only); `report` mode never edits code, resolves/approves PRs, posts comments/issues, deploys, or publishes without approval.
- **Gate live targets & incidents**: staging, paid APIs, destructive fixtures, and customer data require approval. On live incidents, preserve evidence before containment, confirm authority before rotating/disclosing/mutating prod, prefer reversible mitigations, and leave external comms and ETAs to the owner.
- **Check concurrency & scale**: state the expected/assumed service load and check TOCTOU races, unshared per-process state, N+1 queries, and unbounded growth; never add layers, flags, or docs heavier than the bug they fix.

## Documentation

- Companions: [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md), [cloud-run](../cloud-run/SKILL.md), [continuation](../task-prompts/references/continuation.md).
