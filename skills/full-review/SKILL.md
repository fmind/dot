---
name: full-review
description: "Review diffs, PRs, or whole repos; check release readiness ('ready to ship'), smoke tests, dead code, config, and ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-17"
---

# Full Review

Deliver a fixed, proven tree on whole-repo runs or a read-only report on diff/PR/smoke runs. Defer to a repo qualification skill (e.g., `dot-release` in `fmind/dot`) when present, covering only gaps.

## Scope & Mode

Ask only when ambiguity alters scope, cost, or reversibility; note non-default scope/exclusions briefly:

- **Scope**: diffs/PRs run [diff-review](references/diff-review.md); smoke-only runs [smoke](references/smoke.md); ignores run [update-ignores](references/update-ignores/GUIDE.md); otherwise run whole-repo below.
- **Depth**: `deep` (default) inventories every tracked file; `upkeep` skips full inventory.
- **Mode**: whole-repo defaults to `fix`; diff, PR, and smoke default to read-only `report` (run mutating formatters in a [worktree](../git-delivery/references/git-worktree/GUIDE.md), skip Fix/Prove, rank by [severity](#severity)).

## Workflow

1. **Baseline & deterministic gates**: inspect `git status --short`, diffs, latest tag, and `git fetch` (preserving uncommitted work); read `AGENTS.md`, `README.md`, skills, and changelog, and run deterministic gates (`mise run check`, tests, [smoke](references/smoke.md), scanners) first to isolate baseline regressions before spawning subagents.
1. **Audit dimensions & fan out reviewers** (name any skip):
   - **Works**: tasks/CLIs exit zero cleanly ([smoke](references/smoke.md)), failure/race tests pass, authorized endpoints respond.
   - **Current & Simple**: upgrade outdated deps on request ([upgrade-tools](../upgrade-tools/SKILL.md)); enforce `< 500`-line modular files and flag net LOC/flag/dependency creep; find dead code (`vulture src tests --exclude '*/.venv/*' --ignore-decorators '@*_validator,@*.command,@*.callback'`), structural clones (`ast-grep`), orphan files, stale config, and prose bloat ([trim](../trim/SKILL.md), `vale`).
   - **Consistent & Secure**: align versions, metadata, [repo settings](../gh/references/repository/GUIDE.md), and [bootstrap](../project-scaffolding/references/bootstrap.md); wire CI/hooks via [mise](../mise/SKILL.md); audit ignores ([update-ignores](references/update-ignores/GUIDE.md)); scan secrets/deps (`code-security`, `sonar analyze`); sync [docs](../repository-docs/SKILL.md) and fix bottlenecks ([performance](../python-stack/references/performance.md)).
   - **Adversarial review**: fan out clean-context read-only `fmind-review-*` or project reviewers (pairing `fmind-review-completeness` with domain roles and explicit paths; [subagent](../subagent/SKILL.md)) plus `git ls-files` slices on large trees, verifying every `file:line` claim.
1. **Fix, prove, report**: land root-cause fixes + regression tests (holding irreversible, costly, or architectural calls as decisions); rerun `mise run all`, visual/browser renders on UI/docs/figure edits, and `fmind-review-*` checks; report verdict (`ready`, `ready with caveats`, `blocked`), [proof ladder](#proof-ladder) rung, `path:line` evidence, decisions, and gaps ([git-delivery](../git-delivery/SKILL.md) on request).

## Proof ladder

Claim only the highest proven rung (artifact ID, env, command, timestamp; failed gates stay blocked; list unproven boundaries):

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

- **Honor mode boundaries**: whole-repo fixes the full tree (never diff/sample-only); `report` never edits code, resolves/approves PRs, posts comments/issues, deploys, or publishes unapproved.
- **Gate live targets & incidents**: staging, paid APIs, destructive fixtures, and customer data need approval. On incidents, preserve evidence before containment, confirm authority before rotating/disclosing/mutating prod, prefer reversible mitigations, and leave external comms/ETAs to the owner.
- **Check concurrency & scale**: state expected/assumed load and check TOCTOU races, unshared process state, N+1 queries, and unbounded growth; never add layers, flags, or docs heavier than the fix.

## Documentation

- [Google Code Review](https://google.github.io/eng-practices/review/) · [Vulture](https://github.com/jendrikseipp/vulture) · [ast-grep](https://ast-grep.github.io/)
- Companions: [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md), [cloud-run](../cloud-run/SKILL.md), [continuation](../task-prompts/references/continuation.md).
