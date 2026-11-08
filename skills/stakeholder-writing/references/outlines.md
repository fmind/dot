# Outlines and Reader Lenses

Pick the outline that matches what you need from the reader. Formal outlines (decision memo, cost estimate, analysis) use short section names as headings, open each section with a bold sentence that states its conclusion, open the document with an executive summary, and end with annexes for key terms, diagrams, and evidence. Shorter outlines open with the message itself and skip all of this. These outlines are starting points: merge, reorder, drop, or add sections, such as a timeline, a sensitivity table, or a FAQ, when the request or the reader calls for it.

## Document outlines

### Decision memo or proposal

Fit the main text on about one page; everything a reader may want to check goes to the annexes.

1. **Executive summary**: the recommendation, the decision needed and its deadline, the key figure, and the context in one or two sentences.
1. **Options**: every option, including doing nothing, compared on the same few criteria, in a table when there are more than two.
1. **Recommendation and risks**: in a few sentences, why it wins, its main risks with their mitigations, and what would change it.
1. **Next steps**: action, owner, and date, as proposals when the user gave none.
1. **Annexes**: key terms, diagrams, method, calculations, and sources.

### Cost estimate

1. **Executive summary**: the monthly and yearly cost range of each option, the main cost driver, and the recommendation.
1. **Scope and assumptions**: workload, volumes, region, price date, and currency; each assumption labeled and given a range.
1. **Cost per option**: one table with infrastructure, licenses or usage fees, people time (operations, security, on-call), and one-off setup.
1. **Sensitivity**: how the total moves with the two or three most uncertain inputs, and the break-even point between options. For usage-priced services, compare cost per completed task, not only price per unit.
1. **What cost does not show**: security, lock-in, and time to value, when they change the decision.
1. **Annexes**: formulas and price sources with links and retrieval dates.

### Analysis or results report

1. **Executive summary**: the finding, the confidence in it, the implication, and the action.
1. **Question and method**: two sentences.
1. **Findings**: one section per finding, each with a conclusion heading and its evidence as a table or chart.
1. **Limits**: data gaps, possible bias, and what was not tested.
1. **Recommendations and next steps**.

### Document for teammates

1. **Message**: two or three sentences: what this is, the conclusion, and what you need from them.
1. **Details**: only the points they need, each a short paragraph or a short list, with links.
1. **Next steps or open questions**: who does what, by when.
1. **Annexes**: background and evidence they may want to check.

### Status update

1. **Status in one line**: the main change, or on track, at risk, or blocked when the user says so or the facts show it.
1. **Progress**: what is done since the last update and what comes next.
1. **Needs**: decisions or help needed, with dates.
1. **Changes**: risks and changes to scope, cost, or dates.

### Incident or risk summary

1. **Impact**: who was affected, how, for how long, and the current status.
1. **Cause**: in plain words, with contributing factors.
1. **Actions**: what was done, and follow-ups with owners and dates.

### Email or chat message

1. **First sentence**: the answer or the ask.
1. **Context**: two or three sentences.
1. **Next step**: one, with a date.

Use no headings, and at most one short list.

### PR description

1. **Change**: what changes for users or operators, and why.
1. **Verification**: how it was verified and what reviewers should check first.
1. **Risks**: rollout and rollback.

Issue drafts follow the github-issues [draft contract](../../github-issues/references/backlog.md#draft-contract).

## Reader lenses

Lead with the questions of the person who decides; move the other readers' details to annexes.

| Reader                 | First questions                                                                                   | Lead with                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Executive or sponsor   | What do you need from me? What does it cost, earn, or risk? By when?                              | The decision, cost, timeline, and risk in business terms                                   |
| Security leader        | What data goes where? Who can access it? What can go wrong, and how is it controlled? Compliance? | Data flows, threats and controls, residual risk, compliance, auditability, and who owns it |
| Finance or procurement | What is the total cost over time? Fixed or variable? Which commitments and exit costs?            | Cost ranges, cost drivers, commitments, and break-even                                     |
| Engineering lead       | Does it work? How is it built and run? What does it cost the team?                                | Architecture, effort, operations, and dependencies                                         |
| Operations or support  | What changes for us, when, and how do we recover?                                                 | Runbook changes, monitoring, and rollback                                                  |
