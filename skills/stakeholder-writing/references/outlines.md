# Outlines and Reader Lenses

Pick the outline that matches the decision you need from the reader, then turn each section name into a heading that states its conclusion. Every outline opens with the executive summary and ends with annexes when there is evidence to show.

## Document outlines

### Decision memo or proposal

1. **Executive summary**: the recommendation, the decision needed, its deadline, and the key figure.
1. **Context**: the problem and why it matters now, in the reader's terms.
1. **Options**: one table that compares every option on the same criteria, including doing nothing.
1. **Recommendation**: why it wins and under which assumptions.
1. **Risks**: each risk with its mitigation, and what would change the recommendation.
1. **Next steps**: owner, action, and date.
1. **Annexes**: method, calculations, sources, and glossary.

### Cost estimate

1. **Executive summary**: the monthly and yearly cost range of each option, the main cost driver, and the recommendation.
1. **Scope and assumptions**: workload, volumes, region, price date, and currency; each assumption labeled and given a range.
1. **Cost per option**: one table with infrastructure, licenses or usage fees, people time (operations, security, on-call), and one-off setup.
1. **Sensitivity**: how the total moves with the two or three most uncertain inputs, and the break-even point between options.
1. **What cost does not show**: security, lock-in, and time to value, when they change the decision.
1. **Annexes**: formulas and price sources with links and retrieval dates.

### Analysis or results report

1. **Executive summary**: the finding, the confidence in it, the implication, and the action.
1. **Question and method**: two sentences.
1. **Findings**: one section per finding, each with a conclusion heading and its evidence as a table or chart.
1. **Limits**: data gaps, possible bias, and what was not tested.
1. **Recommendations and next steps**.

### Status update

1. **Status in one line**: on track, at risk, or blocked, and why.
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

### PR or issue description

1. **Change**: what changes for users or operators, and why.
1. **Verification**: how it was verified and what reviewers should check first.
1. **Risks**: rollout and rollback.

## Reader lenses

Lead with the questions of the person who decides; move the other readers' details to annexes.

| Reader                 | First questions                                                                                   | Lead with                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Executive or sponsor   | What do you need from me? What does it cost, earn, or risk? By when?                              | The decision, cost, timeline, and risk in business terms                                   |
| Security leader        | What data goes where? Who can access it? What can go wrong, and how is it controlled? Compliance? | Data flows, threats and controls, residual risk, compliance, auditability, and who owns it |
| Finance or procurement | What is the total cost over time? Fixed or variable? Which commitments and exit costs?            | Cost ranges, cost drivers, commitments, and break-even                                     |
| Engineering lead       | Does it work? How is it built and run? What does it cost the team?                                | Architecture, effort, operations, and dependencies                                         |
| Operations or support  | What changes for us, when, and how do we recover?                                                 | Runbook changes, monitoring, and rollback                                                  |
