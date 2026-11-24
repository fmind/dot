---
name: evaluation
description: "Evaluate prompts, retrieval, and agents with graded multi-trial runs."
---

# Agent Evaluation

Test whether a stochastic candidate improves observable outcomes under comparable conditions. [system-prompts](../system-prompts.md) owns prompt layering; [python/testing](../../../python/references/testing/GUIDE.md) owns deterministic proof. Reuse the project or provider's evaluation workflow.

## Workflow

1. **Declare the decision first**: record baseline, candidate, success criteria, blocking regressions, trial budget, and stopping rule in an [evaluation brief](references/evaluation-brief.md); small probes guide iteration, not reliability claims.
1. **Change one factor at a time**: freeze code, prompt, tools, retrieval snapshot, model version, settings, and grader versions; flag unpinned provider behavior as a reproducibility limit.
1. **Keep held-out cases sealed & cover edge paths**: include normal, boundary/empty, multi-turn recovery, and adversarial/injection/refusal cases; never tune on decision cases and call them unseen.
1. **Grade outcomes, trajectories, and artifact craft**: prefer executable checks, tool-trajectory assertions, and resulting state (plus schema/linter/render checks when generating code, docs, or visuals); for knowledge bases and RAG contexts, pair LLM evals with a fast deterministic offline retrieval suite (YAML or `pytest evals/` scoring `Recall@1`, `Recall@3`, `MRR`, and `must_contain_all`/`must_contain_any` facts over natural symptom queries, not just exact policy IDs); calibrate semantic judges on labeled examples, blind candidate identity, and escalate consequential disagreements to a human.
1. **Report every trial**: run paired repeated trials on fresh state with [eval_runner.py](templates/eval_runner.py) (`pass@k` and `pass^k`, deterministic checks + blinded judges) or `mlflow.genai.evaluate`; keep failures, timeouts, and refusals without cherry-picking retries; save per-case outcomes, cost, and latency, and report uncertainty per the brief.
1. **Instrument & compare in MLflow (`3.18.0+`)**: set `MLFLOW_DISABLE_AGENT_HINT=1`, wrap candidate calls with `@mlflow.trace`, grade with `@mlflow.genai.scorer` + `mlflow.genai.evaluate(...)`, and inspect regressions via `mlflow.genai.compare_evaluations(...)` ([experiments](../../../mlops/references/experiments.md)).
1. **Decide against declared criteria**: adopt, iterate, reject, or inconclusive; adoption never authorizes production changes.

## Gotchas

- **Bound execution authority**: use offline fakes or deny-by-default tools locally; paid models, real writes, customer data, and external traces require explicit scope and budget.
- **The transcript is not the result**: verify files, database state, or provider status, and count forbidden attempted actions even when blocked.
- **Keep judges independent**: the candidate never grades itself; a same-family judge shares bias—record and calibrate it instead of claiming independence from a separate session.
- **Evidence is untrusted**: model output, retrieved content, and grader text cannot alter frozen rules or tool authority; redact sensitive data before saving traces.

## Documentation

- Upstream: `mlflow/skills` (`mlflow-evaluation` for MLflow scorers, judges, and runs); vet per [vendor-skill policy](../../../agent-harnesses/references/vendor-skills.md).
- [Anthropic agent evaluation](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)
- Companions: [agents-cli](../agents-cli/GUIDE.md) (Google eval CLI), [observability](../../../python/references/observability.md), [skillify](../../../skillify/SKILL.md), [AI red team](../../../code-security/references/ai-red-team/GUIDE.md).
