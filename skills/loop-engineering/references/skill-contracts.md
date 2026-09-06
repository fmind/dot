# Loop Skill Contracts

Read this while writing the repository-local skills for an inner, middle, and outer loop. Adapt names and domain rules; preserve the ownership and exit boundaries.

## Shared shape

- Give each skill one purpose and a description that states its capability and realistic trigger.
- Start from the smallest durable checkpoint, refresh volatile state, and distinguish observations from inference.
- Make the authorized action, evidence record, next checkpoint, and return target explicit.
- Put domain-heavy rules in one-level references and link sibling loops instead of copying their instructions.
- Keep permissions and safety controls in trusted code when a prompt cannot enforce them.

## Inner loop

- **Trigger**: Advance one named hypothesis, finding, experiment, or work item.
- **Entry**: Read that item's checkpoint, relevant rules, and bounded evidence; reconcile unfinished work first.
- **Action**: Choose one prospective test with an expectation and a decision under either outcome, then execute or review exactly one bounded step.
- **Evidence**: Classify positive, negative, inconclusive, invalid, or blocked outcomes without treating execution failure as evidence about the hypothesis.
- **Exit**: Record the observation, verdict, next action or check time, then return to the middle loop.

## Middle loop

- **Trigger**: Start or resume a campaign across one or more eligible work items for a stated horizon.
- **Entry**: Recover portfolio and item checkpoints, developer steering, current capacity, due reports, and uncertain external operations.
- **Choice**: Prefer completed work needing review, then the feasible action most likely to change a decision; rotate when a blocker is unchanged.
- **Action**: Apply one inner-loop skill in the current harness. Use native bounded waits only when no other authorized work is useful.
- **Exit**: On the horizon, explicit stop, or genuine dependency, persist the exact restart point and state what would unblock progress.

## Outer loop

- **Trigger**: Conduct an owner-requested review across several completed, failed, invalid, and interrupted inner-loop outcomes.
- **Diagnosis**: Evaluate the previous improvement, identify the largest evidenced constraint, and separate missing measurements from poor results.
- **Action**: Prefer deleting a step or clarifying a skill; add a deterministic CLI helper only for repeated mechanical friction.
- **Proof**: Test the changed invariant and replay representative prior decisions using only information available at the time.
- **Exit**: Record the comparison to make next time and finish the bounded review; never start the middle loop implicitly.

## Review questions

- Can a fresh harness resume from files without hidden conversation state?
- Does an explicit stop prevent every new action and make stale wake-ups harmless?
- Are uncertain external side effects reconciled before retry?
- Can blocked work rotate without busy retries or invented progress?
- Are local validation, remote execution, and domain success reported separately?
- Does every skill inherit rather than expand the current authority?
