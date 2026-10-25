# Catalog Growth and Usage Review

Maintain a small discovery surface without losing useful specialist guidance. This is a bounded maintenance procedure, not a background collector or a new scheduled job.

## Review

1. **Measure discovery cost first**: run `dot agent context --source . --project . --details` in the dot source checkout and compare global/local counts, on-demand file costs, and the combined portable index estimate with the previous reviewed revision. Add `--check` to gate the global/local limits that [context budgets](../../dot-cli/references/context.md) define; omit `--source` to inspect installed shared roots. Keep body-load costs separate from startup metadata. Compare parent-plus-guide costs and necessary resource loads for the same explicit, implicit, and neighboring tasks; keep actual host/plugin discovery outside the portable estimate until measured.
1. **Bound the evidence scope**: choose a bounded observation window, such as the last 30 days, and the hosts whose local records are actually available. Record the window, host coverage, and missing evidence before drawing conclusions. Start with a small sample of completed tasks; expand only when the decision needs more evidence.
1. **Count observed loads only**: where records expose explicit skill invocations or tool reads of a `SKILL.md`, inspect those events and aggregate counts by current owning skill. Exclude injected catalog text, quoted prompts, bulk audits, migration reads, and repeated loads within the same request. A read is an observed load, not proof of successful application; keep unverifiable cases unknown. Do not export raw transcripts, prompts, paths, or account data.
1. **Weigh loads against usefulness**: compare observed loads with concrete usefulness: changed decisions, avoided failures, and successful task outcomes. A rarely used recovery or security procedure can justify its place; frequent generic reads can still be wasteful. Do not automatically delete skills with zero observed loads.
1. **Shrink before adding owners**: prefer shortening weak descriptions, moving niche instructions to a reference, or project placement; any new global owner must pass the [admission rule](package-rules.md#categories-and-scope). Preserve discovery cues and essential authorization boundaries when merging.
1. **Validate behavior** per the [adoption check](adoption-check.md); for a broad reorganization, probe roughly 12–20 representative requests spanning explicit tools, unnamed tasks, neighboring owners, and no-skill work, and also record instructions actually read and unnecessary reads.

## Adoption record

Use the task's existing report or PR description: observation window and coverage; before/after index cost; proposed owner and trigger; behavioral benefit; neighboring task; activation evidence or its absence; validation and remaining limits. No permanent per-skill tracking database is required.
