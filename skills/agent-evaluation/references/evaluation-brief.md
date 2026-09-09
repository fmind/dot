# Evaluation Brief

Keep this record with the project's existing evaluation artifacts; do not create a second evaluation service or global task database.

| Field | Record before execution |
| --- | --- |
| Decision | Change hypothesis, development or adoption scope, and accountable owner |
| Identity | Baseline/candidate revisions, prompts, model, tools, data snapshot, settings, and grader versions |
| Cases | Versioned development and held-out case IDs, expected outcomes, risk segments, and known coverage gaps |
| Grading | Deterministic checks, semantic rubric if needed, calibration examples, blinding, and disagreement handling |
| Trial plan | Repetitions, ordering, fresh-state reset, time/token/cost limits, and allowed external effects |
| Decision rule | Primary measure, uncertainty method, unacceptable regressions, early-stop criteria, and what yields inconclusive |

After execution, record every planned trial as completed, failed, or not run, with its reason. Summarize outcomes by task and risk segment; keep quality, attempted unsafe actions, latency, and cost distinct. Link only privacy-safe artifact locations appropriate for the audience.

State the verdict, deviations from the plan, judge limitations, and whether the decision cases were exposed during iteration. An improved average does not override a declared critical regression. If the budget cannot distinguish the acceptance threshold, return inconclusive with the smallest useful follow-up instead of moving the threshold.
