# Skill Adoption Check

Package validation proves structure. Test a substantial skill addition or routing change with a small set of realistic tasks to check whether it is discoverable and useful. Keep the procedure manual and bounded unless repetition demonstrates a need for automation.

1. Choose a natural request that should load the skill, a neighboring request that should load another owner, and an observable successful outcome. Define these before examining execution results; avoid putting the skill name into the natural routing prompt.
1. Register the ownership expectations in the catalog's existing routing fixture. The lexical report is a diagnostic, not evidence of the host's actual selection.
1. Use a fresh host session with the final catalog discoverable, raw fixtures, and the minimum project context. Observe which skills it selects. An explicit `$skill-name` test checks execution but cannot prove automatic discovery.
1. Exercise the skill on a safe isolated task, including the failure boundary that motivated it. Check files, exit status, data, or attempted actions rather than accepting the agent's completion statement.
1. Compare against the prior skill or baseline workflow under comparable conditions when claiming improvement. Record success, required corrections, unnecessary operations, completion time, and token/cost data if available; one trial is an anecdote, not a reliability estimate.
1. Record host/model version, catalog revision or dirty-candidate identity, selected skills, outcome, deviations, and untested boundaries in the task's existing report. Redact private prompts and artifacts before any public summary.

Use an independent evaluator when available and authorized, without handing it the intended answer. Reuse the active task's scope; paid calls or external effects need the relevant authority. When fresh-host execution is unavailable, report static and local example validation separately and leave behavioral discovery unverified.

Correct a demonstrated routing ambiguity or failure narrowly; do not tune descriptions to a single probe or accumulate instructions for hypothetical mistakes. [agent-evaluation](../../agent-evaluation/SKILL.md) owns repeated stochastic comparisons when the adoption decision needs stronger evidence.
