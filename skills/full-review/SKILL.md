---
name: full-review
description: "Review a diff, PR, or whole repo, check release readiness, handle live incidents, smoke-test tasks, or run upkeep: fix tools, dead code, stale config, ignores."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-11-08"
---

# Full Review

Answer "perform a full review", "final check before release", "is this ready to ship", "make sure everything works and is up to date", "review this diff or PR", "smoke-test everything", or a routine upkeep request. A whole-repository run ends in a fixed, proven tree, not a findings list; a diff or PR review ends in a read-only report. When a repository ships its own verify skill (such as `dot-verify`), follow it and use this skill only for what it omits.

## Arguments

Parse the request into one line and state it before starting: scope, exclusions ("skip `data/`"), depth, mode, and follow-ups (release, commit, propagation; none unless requested). Ask only when an ambiguity changes scope, cost, or reversibility.

- **Scope selects the procedure**: a diff, patch, branch, PR, or self-review follows [diff-review](references/diff-review.md); a smoke-only request runs [smoke](references/smoke/GUIDE.md) alone; an ignore-only request runs [update-ignores](references/update-ignores/GUIDE.md) alone; anything else is a whole-repository run of the workflow below.
- **Depth**: default deep covers every tracked file in scope; `upkeep` skips the coverage inventory and covers the Current, Simple, Consistent, and Documented dimensions plus the adopted security scans.
- **Mode**: whole-repository runs default to fix. Diff, PR, and smoke-only scopes default to `report`. `report` stays read-only, runs writing tasks such as `mise run format` only in an isolated [snapshot](../git-delivery/references/git-worktree/GUIDE.md), skips the Inventory (for diff and PR scope), Fix, and Prove steps, and ranks findings by [severity](#severity).

## Workflow

1. **Baseline**: record `git status --short`, staged and unstaged diffs, the last tag, and `git fetch` state. Existing uncommitted work is part of the candidate unless the user says otherwise; never discard or restage it. Run the existing gates once to separate preexisting failures from regressions.
1. **Load decisions**: read `AGENTS.md`, `README.md`, skills, changelog, and stored decisions (agent memory, `## Decisions` notes, ADRs). Do not re-raise kept or declined choices; mention one only when a new change reopens it.
1. **Inventory coverage**: list tracked files by area with `git ls-files`, minus exclusions and generated or vendored files. Track each area to reviewed; "don't scratch the surface" means no unread area. For large trees, fan out read-only reviews by area to subagents or one session per area when the host supports it, then verify every returned finding yourself before acting.
1. **Review each dimension**; skip one only when it is out of scope, and name it in the report:
   - **Works**: every task and CLI entry point runs clean with no warnings ([smoke](references/smoke/GUIDE.md)); tests are deterministic and cover failure and race paths; production or deployed endpoints are probed read-only when authorized.
   - **Current**: tools, dependencies, actions, and runtimes against their latest releases ([upgrade-tools](../upgrade-tools/SKILL.md)); report drift and upgrade when the request says so.
   - **Simple**: dead code (Python: vulture per [ruff](../python-stack/references/ruff.md#gotchas)), legacy paths, orphan files, stale config, unearned abstractions, and verbose docs ([trim](../trim/SKILL.md)); prefer deletion and consolidation, never a heavier mechanism.
   - **Consistent**: names, descriptions, versions, and metadata match across code, `pyproject.toml`, docs, GitHub ([github-repository](../github-repository/SKILL.md)), and the website; the layout follows its stack owner (such as [python-stack](../python-stack/SKILL.md)) and the [bootstrap layer](../project-scaffolding/references/bootstrap.md); hooks and CI call the canonical [mise](../mise/SKILL.md) tasks; generated files (locks, indexes, formatted output) regenerate with no diff; version, changelog, and tags agree; ignore files fit the stack ([update-ignores](references/update-ignores/GUIDE.md)).
   - **Secure and private**: secrets, permissions, dependencies, and agent tools ([code-security](../code-security/SKILL.md)); private repositories stay private and public ones disclose nothing sensitive.
   - **Documented**: `README.md`, `AGENTS.md`, skills, and `*.md` match behavior, stay concise, and convince their audience ([repository-docs](../repository-docs/SKILL.md)); repeated instructions become skills ([skillify](../skillify/SKILL.md)).
   - **Fast**: slow tasks, tests, CI, or pages with a measured cause ([performance](../python-stack/references/performance.md)).
1. **Fix**: apply each verified finding with the smallest change; add a regression test for behavior fixes. Prefer one coherent change per finding so selective reverts stay easy. Hold back changes that are irreversible, outward-facing, costly, or that change a deliberate design, and list them as decisions.
1. **Prove**: rerun only the checks a fix invalidated, then the full gate (`mise run all` or the repository's equivalent) on a snapshot equal to the candidate.
1. **Report**: the verdict (ready, ready with caveats, or blocked) with the highest proven rung of the [proof ladder](#proof-ladder), each fix or finding with its `path:line` and evidence, held-back changes as decisions, and the areas, credentials, or services this pass did not cover.
1. **Follow up on request**: release or commit through [git-delivery](../git-delivery/SKILL.md) or the repository's release skill; propagate to dependent repositories by repeating this pass there; when the user says "apply all" after a report-mode run, resume at the Fix step.

## Proof ladder

Place the candidate on the highest rung its evidence proves, and never collapse rungs. Each claim records the artifact identity, environment, command or observation, and timestamp.

- `source-ready`: the intended source and configuration are reviewable.
- `local-green`: the repository-owned local checks pass for the candidate.
- `exact-head-CI`: required CI passes for the exact immutable revision.
- `runtime-proven`: the built artifact works across the authorized runtime boundary.
- `deployed`: that artifact is running in the target environment.
- `release-published`: the intended audience can obtain the released result ([release](../git-delivery/references/release/GUIDE.md)).

Never borrow another revision's or environment's evidence: a green run, probe, or deployment elsewhere proves nothing about this candidate. A failed hard gate stays blocked regardless of schedule or sunk cost. Report every material gap above the highest proven rung, such as paths that need unavailable services, paid or destructive end-to-end scenarios, a scanner that timed out or ran on an offline database, or a missing credential.

## Severity

- **P0**: immediate security breach, irreversible data loss, or broad outage risk.
- **P1**: likely correctness, security, or availability defect that should block merge.
- **P2**: material edge-case, maintainability, performance, or test defect worth fixing before or soon after merge.
- **P3**: minor issue, reported only when the user asked for an exhaustive review.

Give each finding its location, reachable trigger, evidence, impact, and smallest correction. Drop preferences and speculation, and say "none material" when that is true.

## Task guides

<!-- guides:start -->

- [diff-review](references/diff-review.md): Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings.
- [smoke](references/smoke/GUIDE.md): Smoke-test every repo task and CLI command; warnings count as failures.
- [update-ignores](references/update-ignores/GUIDE.md): Audit and fix .gitignore, .ignore, .dockerignore, and tool excludes for the stack.

<!-- guides:end -->

## Gotchas

- **Fix by default on whole-repository runs**: findings without fixes were the most frequent complaint; report-only is opt-in there.
- **Shallow passes do not count on whole-repository runs**: diff-only or sampled reviews do not satisfy a full review; the inventory proves coverage.
- **Report mode is review only**: inspection, bounded validation, and local reports are in scope. Editing code, resolving threads, approving PRs, posting remote issues or comments, deploying, or publishing needs explicit authorization.
- **Live targets need explicit authorization**: run nothing against staging, paid APIs, destructive fixtures, or customer data without it. When a review uncovers an incident (a leaked credential, a breach, an outage), resolve authority before rotating credentials, disclosing, or mutating production. During a live incident, freeze unrelated work, preserve evidence before containment changes it, prefer the safest reversible mitigation, treat missing telemetry as unknown rather than recovered, and never promise a recovery time; the responsible owner sends anything external.
- **State the assumed load**: for a service, find the expected load (README, deployment configuration), state the load you assumed, and check defects that appear only with many users or instances: check-then-write races, per-process state that must be shared, a query per item, and collections that only grow.
- **Avoid complexity creep**: a fix that adds a layer, option, or document needs a stronger reason than the finding it solves.

## Documentation

- Companion skills: [github-pull-request](../github-pull-request/SKILL.md) (open and update PRs), [github-issues](../github-issues/SKILL.md) (findings to issue drafts), [cloud-run](../cloud-run/SKILL.md) (deploy and revision rollback), [continuation](../task-prompts/references/continuation.md) (continue in a fresh session).
