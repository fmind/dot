# Goals, prompts and continuation

The user supplies outcome, scope and bounds. The native goal drives persistence. A project prompt loads the owning skill. The skill chooses work from evidence; one-shot helpers handle mechanics. Files preserve the restart point. Keep these responsibilities separate without copying the full workflow into every layer.

## Choose a completion contract

| Goal type | Completion evidence | Boundary |
| --- | --- | --- |
| Objective | A stated observable acceptance condition verified in its authoritative system | Stop when achieved; record blocked or interrupted if required evidence is unavailable |
| Time window | Actual start/end and observed work, waits and interruptions across the window | Reaching the end closes the campaign, even if its aspirational outcome remains unmet |
| Objective with deadline | Objective verified before the deadline, or a terminal report when the deadline arrives | State which event ends the goal and how unmet success will be reported |

Avoid unbounded objectives whose outcome the agent cannot control. Separate “produce a reproducible candidate for owner review” from later third-party acceptance or payment, and local validation from a private leaderboard outcome. Use an ambitious aspiration to guide selection while retaining an achievable operational contract. Never mark an objective achieved merely because the token budget is nearly exhausted or a subtask returned successfully. Map blocked/completed states to the host's actual goal contract; do not invent fixed blocker counts across harnesses.

A new campaign records the actual UTC invocation time and a newly computed deadline. Preparing a prompt starts no clock. Resuming earlier project knowledge does not make a new campaign a resume of an old window. An explicit resume preserves its recorded deadline unless the user extends it; if expired, report the boundary instead of silently starting another week. Store UTC, display local time with an IANA timezone and offset, and compute relative delays at the time of each update.

## Thin project prompts

Example goal invocation in a harness that supports `/goal`:

```text
/goal Run a new seven-day campaign for only <work items>, in that priority order. Read and execute prompts/run.md. Report verified outcomes and interruptions at the deadline.
```

Example objective invocation:

```text
/goal Produce <reviewable result> meeting <observable acceptance criteria>, within <scope and budget>. Read and execute prompts/run.md.
```

Example `prompts/run.md` body (replace the owning skill with a real project path):

```markdown
# Run

Read AGENTS.md and the current checkpoint, then execute the project's campaign skill with the scope and completion contract from the user's goal. Preserve explicit restrictions and session assignments. Follow that skill's evidence, recovery, continuation and stop rules.
```

Example `prompts/improve.md` body:

```markdown
# Improve

Read AGENTS.md, then execute the project's meta-loop skill as one bounded review of the past week's evidence and the previous improvement's impact. Respect active owners before changing shared files. Apply supported reversible improvements, validate them and record the next observable comparison. Finish this review without starting a campaign.
```

Use `Read and execute prompts/<name>.md` within an active session when slash goals are unavailable. Do not guess slash-command syntax or assume one host's goal lifecycle exists in another. For exact startup flags, inspect installed help and the owning harness skill. A print/headless timeout controls one invocation's lifetime; increasing it is not proof of durable goal continuation.

## Decide work, then wait

1. On start/resume, read the short checkpoint and governing rules once; retrieve deeper evidence only for a named decision. Check current time, ownership, latest steering and uncertain external outcomes before launching anything.
1. Review landed results promptly. Refill eligible empty work slots before giving one item repeated attention; explicit `only` restricts scope, while focus ordinarily orders attention within owned scope. Respect admission gates and global capacity.
1. When a queue is empty, make a bounded research pass against a different mechanism or concrete prerequisite. Missing controls or execution errors are invalid/inconclusive evidence, not negative domain results.
1. If only a stable external condition remains, record its reopening signal and the next evidence review based on its likely rate of change. Do not repeat unchanged searches to refresh timestamps. Ask once for human-only prerequisites while continuing independent work.
1. Choose the earliest useful event: expected result, prerequisite revisit, due report or campaign end. Announce the reason and invoke an actual native wait or monitor. Use a bounded blocking wait of at most 60 seconds when that is the only supported mechanism; do not add a polling script or supervisor.
1. Continue in the active turn after reports, bounded actions and compaction while work or supported waits remain. Checkpoint before context turnover. A missing future callback does not prevent a current-turn wait.
1. Rely on post-turn resumption only when the native goal/continuation contract supports it; record an actual callback identity/target when applicable. A timer that completed inside the initiating turn proves a wait, not a future wake. Do not promise unattended work from a goal record, open TUI or running remote job.
1. On waking, recheck campaign identity, stop/end and ownership before refreshing relevant evidence. Explicit stop cancels owned waits/retries/successors; stale callbacks do no new work. At the deadline stop successor launches and reconcile, clean up within authority, or hand off remaining external work.

Keep status concise: as-of time, working/waiting/paused/stopped state, observed result or blocker, next action/time, and actual continuation mechanism. If the host cannot continue, report interruption with the exact session/checkpoint, remaining window and manual resume instruction. Claim neither continuous execution nor automatic reports without evidence.

## Improve the loop from outcomes

Keep meta-loop owner-invoked. Review the previous improvement before making another. Sample positive, negative, invalid, blocked and interrupted actions; trace each from prospective expectation through evidence to the next decision. Measure meaningful friction when records support it: result-to-review delay, empty-slot-to-research delay, repeated queries, unnecessary permission requests, report lateness and promised versus observed wakes. Missing measurements remain unknown.

Pick the largest evidenced constraint and implement a few reversible changes. Prefer deleting a redundant step, clarifying a decision rule or improving retrieval before adding helpers. Replay representative decisions using evidence available at the time. Record validation and one observable comparison for the next review; local replay is not proof of improved live outcomes. Do not change files an active owner is using or let a campaign change its own authority and evidence thresholds.
