# Evaluation Brief

Store this record with the project's evaluation artifacts; do not add a separate evaluation service or global task database.

| Field         | Record before execution                                                                                          |
| ------------- | ---------------------------------------------------------------------------------------------------------------- |
| Decision      | Change hypothesis, development or adoption scope, and accountable owner                                          |
| Identity      | Baseline/candidate revisions, prompts, model, tools, data snapshot, settings, and grader versions                |
| Cases         | Versioned development and held-out case IDs, expected outcomes, risk segments, and coverage gaps                 |
| Grading       | Deterministic checks, semantic rubric if needed, calibration examples, blinding, and disagreement handling       |
| Trial plan    | Repetitions, ordering, fresh-state reset, time/token/cost limits, and allowed external effects                   |
| Decision rule | Primary measure, uncertainty method, unacceptable regressions, early-stop criteria, and what yields inconclusive |

After execution, mark every planned trial completed, failed, or not run with its reason. Summarize by task and risk segment, keeping quality, attempted unsafe actions, latency, and cost separate; link only privacy-safe artifacts fit for the audience.

State the verdict, plan deviations, judge limits, and whether decision cases leaked during iteration. A critical regression overrides an improved average; if the budget cannot resolve the threshold, return inconclusive with the smallest follow-up instead of moving the bar.
