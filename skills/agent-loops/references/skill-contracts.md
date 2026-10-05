# Loop Skill Contracts

Read this while writing the repository-local skills for an inner, middle, and outer loop, or a helper CLI they call. Adapt names and domain rules; preserve the ownership and exit boundaries.

## Shared shape

- **Keep skills single-purpose**: give each one a description that states its capability and realistic trigger.
- **Resume from the smallest checkpoint**: start from the smallest durable checkpoint, refresh volatile state, and distinguish observations from inference.
- **Make action and return explicit**: make the authorized action, evidence record, next checkpoint, and return target explicit.
- **Link rather than copy**: put domain-heavy rules in one-level references and link sibling loops instead of copying their instructions.
- **Enforce safety in trusted code**: keep permissions and safety controls in trusted code when a prompt cannot enforce them.

## Inner loop

- **Trigger**: advance one named hypothesis, finding, experiment, or work item.
- **Entry**: read that item's checkpoint, relevant rules, and bounded evidence; reconcile unfinished work first.
- **Action**: choose one prospective test with an expectation and a decision under either outcome, then execute or review exactly one bounded step.
- **Evidence**: classify positive, negative, inconclusive, invalid, or blocked outcomes without treating execution failure as evidence about the hypothesis.
- **Exit**: record the observation, verdict, next action or check time, then return to the middle loop.

## Middle loop

- **Trigger**: A native goal or direct invocation starts or resumes a campaign across eligible work items with an objective, time window, or combined completion contract; an entry prompt forwards scope to this skill.
- **Entry**: recover portfolio and item checkpoints, developer steering, session ownership, current capacity, due reports, and uncertain external operations. Distinguish a new campaign clock from an explicit resume.
- **Choice**: prefer completed work needing review, then the feasible action most likely to change a decision; rotate when a blocker is unchanged.
- **Action**: apply one inner-loop skill in the current harness. Use native bounded waits only when no other authorized work is useful.
- **Exit**: on verified objective completion or the time boundary defined by the goal, stop successors and reconcile remaining work. On explicit stop or unavoidable interruption, persist the exact restart point, remaining scope/window and actual resume mechanism; keep temporary blockers inside the active campaign when independent work or a supported evidence wait remains.

## Outer loop

- **Trigger**: conduct an owner-requested review across several completed, failed, invalid, and interrupted inner-loop outcomes.
- **Diagnosis**: evaluate the previous improvement, identify the largest evidenced constraint, and separate missing measurements from poor results.
- **Action**: prefer deleting a step or clarifying a skill; add a deterministic CLI helper only for repeated mechanical friction.
- **Proof**: test the changed invariant and replay representative prior decisions using only information available at the time.
- **Exit**: record the comparison to make next time and finish the bounded review; never start the middle loop implicitly.

## Deterministic helpers

- **Build a small typed CLI**: run it through `uv` with [cli-contracts](../../cli-development/references/cli-contracts.md) and [typer](../../cli-development/references/typer/GUIDE.md).
- **Helpers handle record mechanics**: useful commands validate scope and records, enforce transitions, append atomically, deduplicate launches, reconcile uncertain external operations, verify source or artifact identity, expose status, and render report context.
- **One operation, no judgment**: each command performs one explicit operation and exits. It must not select hypotheses, allocate the portfolio, launch agent harnesses, schedule itself, interpret unchanged blockers as progress, or decide whether evidence merits promotion.

## Review questions

- Can a fresh harness resume from files without hidden conversation state?
- Does an explicit stop prevent every new action and make stale wake-ups harmless?
- Are uncertain external side effects reconciled before retry?
- Can blocked work rotate without busy retries or invented progress?
- Are local validation, remote execution, and domain success reported separately?
- Does every skill inherit rather than expand the current authority?
- Do new start, resume, expired deadline and compaction preserve the intended completion contract?
- Are entry prompts thin, concurrent scopes disjoint, and shared writers explicit?
