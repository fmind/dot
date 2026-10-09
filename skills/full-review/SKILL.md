---
name: full-review
description: "Full review: read every repo area, apply verified fixes, and prove all checks pass."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/full-review
  created: "2026-10-04"
  updated: "2026-10-09"
---

# Full Review

Answer "perform a full review", "final check before release", or "make sure everything works and is up to date" with one deep pass that ends in a fixed, proven tree. The default outcome is applied verified fixes, not a findings list. [repository-review](../repository-review/SKILL.md) owns read-only audits and severity. Unlike the recurring [repository-maintenance](../repository-maintenance/SKILL.md) upkeep pass, this skill inventories and reads every tracked area across all dimensions below, then fixes and proves the result with the full gate. When a repository ships its own verify skill (such as `dot-verify`), follow it and use this skill only for what it omits.

## Arguments

Parse the request into one line and state it before starting: scope (paths, other repositories), exclusions ("skip `data/`"), depth (default deep: every tracked file in scope), mode (default fix; `report` stays read-only, skips the Fix and Prove steps, and lists findings under **Fixed** renamed **Findings**, ranked by [repository-review severity](../repository-review/SKILL.md#severity)), and follow-ups (release, commit, propagation; none unless requested). Ask only when an ambiguity changes scope, cost, or reversibility.

## Workflow

1. **Baseline**: record `git status --short`, staged and unstaged diffs, the last tag, and `git fetch` state. Existing uncommitted work is part of the candidate unless the user says otherwise; never discard or restage it. Run the existing gates once to separate preexisting failures from regressions.
1. **Load decisions**: read `AGENTS.md`, `README.md`, skills, changelog, and stored decisions (agent memory, `## Decisions` notes, ADRs). Do not re-raise kept or declined choices; mention one only when a new change reopens it.
1. **Inventory coverage**: list tracked files by area with `git ls-files`, minus exclusions and generated or vendored files. Track each area to reviewed; "don't scratch the surface" means no unread area. For large trees, fan out read-only reviews by area to subagents or one session per area when the host supports it, then verify every returned finding yourself before acting.
1. **Review each dimension** in the [review matrix](../repository-review/references/review-matrix.md), plus what reviews here repeatedly request:
   - **Works**: every task and CLI entry point runs clean with no warnings ([smoke](../smoke/SKILL.md)); production or deployed endpoints are probed read-only when they exist.
   - **Current**: tools, dependencies, actions, and runtimes against their latest releases ([upgrade-tools](../upgrade-tools/SKILL.md)); report drift and upgrade when the request says so.
   - **Simple**: dead code, legacy paths, orphan files, stale config, unearned abstractions, and verbose docs ([trim](../trim/SKILL.md)); prefer deletion and consolidation, never a heavier mechanism.
   - **Consistent**: names, descriptions, versions, and metadata match across code, `pyproject.toml`, docs, GitHub ([github-repository](../github-repository/SKILL.md)), and the website; ignore files fit the stack ([update-ignores](../repository-maintenance/references/update-ignores/GUIDE.md)).
   - **Secure and private**: secrets, permissions, dependencies, and agent tools ([code-security](../code-security/SKILL.md)); private repositories stay private and public ones disclose nothing sensitive.
   - **Documented**: `README.md`, `AGENTS.md`, skills, and `*.md` match behavior, stay concise, and convince their audience ([repository-docs](../repository-docs/SKILL.md)).
   - **Fast**: slow tasks, tests, CI, or pages with a measured cause ([benchmark](../benchmark/SKILL.md)).
1. **Fix**: apply each verified finding with the smallest change; add a regression test for behavior fixes. Prefer one coherent change per finding so selective reverts stay easy. Hold back changes that are irreversible, outward-facing, costly, or that change a deliberate design, and list them as decisions.
1. **Prove**: rerun only the checks a fix invalidated, then the full gate (`mise run all` or the repository's equivalent) on the final tree. Confirm the tested snapshot equals the candidate.
1. **Report**: per the template below. Keep it short; evidence goes in file:line references, not narration.
1. **Follow up on request**: release or commit through [git-delivery](../git-delivery/SKILL.md) or the repository's release skill; propagate to dependent repositories by repeating this pass there; when the user says "apply all" after a report-mode run, resume at the Fix step.

## Report template

```text
**Result**: <one line: ready / ready with caveats / blocked, and the proven rung>
**Fixed** (<n>): <finding> — `path:line` — <check that proves it>
**Decisions for you** (<n>): <numbered, each with options and a recommendation>
**Suggestions** (<n>): <numbered improvements beyond defects, ranked by value>
**Checks**: <command> pass/fail/blocked/not run
**Not covered**: <areas, credentials, or services outside this pass>
```

Number decisions and suggestions so the user can answer "do 2, 3" or "all but 1".

## Gotchas

- **Fix by default**: findings without fixes were the most frequent complaint; report-only is opt-in.
- **Shallow passes do not count**: diff-only or sampled reviews do not satisfy a full review; the inventory proves coverage.
- **Avoid complexity creep**: a fix that adds a layer, option, or document needs a stronger reason than the finding it solves.
- **Report progress at phase boundaries**: post one line at each phase boundary in long runs; silent stalls read as stuck work.

## Documentation

- Companion skills: [repository-review](../repository-review/SKILL.md) (severity and evidence), [production-readiness](../production-readiness/SKILL.md) (proof ladder), [quality-assurance](../quality-assurance/SKILL.md) (user-journey campaigns), [handoff](../handoff/SKILL.md) (continue in a fresh session).
