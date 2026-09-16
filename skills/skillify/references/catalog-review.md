# Catalog Growth and Usage Review

Maintain a small discovery surface without losing useful specialist guidance. This is a bounded maintenance procedure, not a background collector or a new scheduled job.

## Review

1. Run `mise run report:skills` in the dot source checkout. Compare global/local counts, description average, and combined portable index estimate with the previous reviewed revision using the same renderer. Use `dot agent context --source . --project . --check` for the independent global/local AGENTS.md + skill discovery limits (each below 5,000 estimated tokens), combined informational total, and separate body estimates; omit `--source` to inspect installed shared roots. Keep body-load costs separate from startup metadata. Compare parent-plus-guide costs and necessary resource loads for the same explicit, implicit, and neighboring tasks; keep actual host/plugin discovery outside the portable estimate until measured.
1. Choose a bounded observation window, such as the last 30 days, and the hosts whose local records are actually available. Record the window, host coverage, and missing evidence before drawing conclusions. Start with a small sample of completed tasks; expand only when the decision needs more evidence.
1. Where records expose explicit skill invocations or tool reads of a `SKILL.md`, inspect those events and aggregate counts by current owning skill. Exclude injected catalog text, quoted prompts, bulk audits, migration reads, and repeated loads within the same request. A read is an observed load, not proof of successful application; keep unverifiable cases unknown. Do not export raw transcripts, prompts, paths, or account data.
1. Compare observed loads with concrete usefulness: changed decisions, avoided failures, and successful task outcomes. A rarely used recovery or security procedure can justify its place; frequent generic reads can still be wasteful. Do not automatically delete skills with zero observed loads.
1. Prefer shortening weak descriptions, moving niche instructions to a reference, or project placement. A new global owner requires a distinct recurring trigger and a demonstrated benefit that cannot fit an existing owner. Preserve discovery cues and essential authorization boundaries when merging.
1. Validate contracts, links, realistic routing cases, and installed discovery in a fresh host session. For a broad reorganization, choose roughly 12–20 representative requests spanning explicit tools, unnamed tasks, neighboring owners, and no-skill work. Observe selected owners, instructions actually read, unnecessary reads, corrections, outcomes, and task tokens/time; include the prerequisite or failure that motivated the guidance. Record what was measured and which behavioral checks remain unverified; a lexical ranking is not host selection evidence.

## Adoption record

Use the task's existing report or PR description: observation window and coverage; before/after index cost; proposed owner and trigger; behavioral benefit; neighboring task; activation evidence or its absence; validation and remaining limits. No permanent per-skill tracking database is required.
