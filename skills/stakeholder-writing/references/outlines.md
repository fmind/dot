# Outlines and Reader Lenses

Start from the outline matching the ask, then merge, drop, or add sections (such as a timeline, sensitivity table, or FAQ) for the reader. Formal outlines use an executive summary, bold section-opening conclusions, figures where visuals beat prose, and annexes; shorter ones open directly with the message.

## Document outlines

### Decision memo or proposal

Keep the main text near one page; move verification detail to annexes.

1. **Executive summary**: recommendation, decision needed with deadline, key figure, and 1–2 sentences of context.
1. **Options**: all options (including doing nothing) on shared criteria; use a table past two options.
1. **Recommendation and risks**: why it wins, main risks with mitigations, and what would flip the choice.
1. **Next steps**: action, owner, and date (marked as proposals when unstated).
1. **Annexes**: key terms, supporting figures, method, calculations, and sources.

### Cost estimate

1. **Executive summary**: monthly and yearly range per option, primary cost driver, and recommendation.
1. **Scope and assumptions**: workload, volumes, region, price date, currency, and labeled assumption ranges.
1. **Cost per option**: one table covering infrastructure, licenses/usage, staff time (ops, security, on-call), and setup.
1. **Sensitivity**: how totals move with the 2–3 most uncertain inputs, break-even points, and cost per completed task (not just unit price).
1. **What cost does not show**: security, lock-in, and time to value when decision-relevant.
1. **Annexes**: formulas and linked price sources with retrieval dates.

### Analysis or results report

1. **Executive summary**: finding, confidence, implication, and action.
1. **Question and method**: two sentences.
1. **Findings**: one section per finding with a short heading, bold conclusion sentence, and table or figure.
1. **Limits**: data gaps, bias, and untested cases.
1. **Recommendations and next steps**.

### Document for teammates

1. **Message**: 2–3 sentences stating purpose, conclusion, and ask.
1. **Details**: short paragraphs or a brief list with links.
1. **Next steps or open questions**: owner and date per item.
1. **Annexes**: optional background and evidence.

### Status update

1. **Status in one line**: main change, or on track / at risk / blocked when supported by facts.
1. **Progress**: completed since last update and next up.
1. **Needs**: decisions or help required, with dates.
1. **Changes**: risks or shifts in scope, cost, or dates.

### Incident or risk summary

1. **Impact**: who was affected, how, duration, and current state.
1. **Cause**: root cause and contributing factors in plain words.
1. **Actions**: mitigations applied and follow-ups with owners and dates.

### Email or chat message

1. **First sentence**: the answer or ask.
1. **Context**: 2–3 sentences.
1. **Next step**: one action with a date.

No headings; at most one short list.

### PR description

1. **Change**: user or operator impact and why.
1. **Verification**: how it was proved and where reviewers should start.
1. **Risks**: rollout and rollback.

Issue drafts follow the gh [draft contract](../../gh/references/issues/references/backlog.md#draft-contract).

## Reader lenses

Lead with the decider's questions; move secondary readers' details to annexes.

| Reader                 | First questions                                                                | Lead with                                                          |
| ---------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Executive or sponsor   | What do you need from me? What does it cost, earn, or risk? By when?           | Decision, cost, timeline, and business risk                        |
| Security leader        | What data goes where? Who has access? How are failures controlled and audited? | Data flows, threats/controls, residual risk, compliance, ownership |
| Finance or procurement | Total cost over time? Fixed vs variable? Commitments and exit costs?           | Cost ranges, drivers, commitments, and break-even                  |
| Engineering lead       | Does it work? How is it built and operated? Team cost?                         | Architecture, effort, operations, and dependencies                 |
| Operations or support  | What changes for us, when, and how do we recover?                              | Runbook changes, monitoring, and rollback                          |
