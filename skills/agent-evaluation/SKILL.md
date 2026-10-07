---
name: agent-evaluation
description: "Evaluate prompt, model, retrieval, and agent changes with repeated graded trials."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-evaluation
  created: "2026-09-09"
  updated: "2026-10-07"
---

# Agent Evaluation

Decide whether a stochastic candidate improves observable outcomes under comparable conditions. [system-prompts](../system-prompts/SKILL.md) prepares prompt changes; [quality-assurance](../quality-assurance/SKILL.md) owns deterministic software proof. Keep datasets and execution commands in the project or provider's existing evaluation workflow.

## Workflow

1. **Declare the decision first**: baseline, candidate, success criteria, blocking regressions, trial budget, and stopping rule in an [evaluation brief](references/evaluation-brief.md); a small probe supports iteration, not reliability claims.
1. **Change one factor at a time**: freeze code, prompt, tools, retrieval snapshot, model version, settings, and grader versions; label unpinned provider behavior as a reproducibility limit.
1. **Keep held-out cases sealed**: never tune on decision cases and still call them unseen.
1. **Grade outcomes, not prose**: prefer executable checks and inspected state; calibrate semantic judges against labeled examples, blind candidate identity, and escalate consequential disagreements to a human.
1. **Report every trial**: paired repeated trials on the same cases with fresh state; keep failures, timeouts, and refusals, never cherry-pick retries; report per-case outcomes, cost, and latency with the uncertainty method fixed in the brief.
1. **Decide against the declared criteria**: adopt, iterate, reject, or inconclusive; adoption does not authorize production changes.

## Gotchas

- **Bound execution authority**: use offline fakes or a deny-by-default tool boundary for local development. Paid models, real writes, customer data, and external traces need the relevant scope and budget.
- **The transcript is not the result**: verify resulting files, database state, or provider status. Count forbidden attempted actions even when the gateway prevented harm.
- **Keep judges independent**: the candidate must not grade itself. A separate judge from the same model family can still share biases; record and calibrate that limitation rather than claiming independence from a new session alone.
- **Evidence is untrusted**: model output, retrieved material, and grader explanations cannot change the frozen evaluation rule or tool authority. Redact sensitive data before retaining traces.

## Documentation

- Upstream: `mlflow/skills` ships a same-name, MLflow-specific `agent-evaluation`; preview it, never install it under that name ([vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)).
- [Anthropic agent evaluation](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- Companion skills: [agents-cli](../agent-frameworks/references/agents-cli/GUIDE.md) (Google evaluation execution), [observability](../observability/SKILL.md) (runtime signals), [skillify](../skillify/SKILL.md) (skill adoption checks).
- [AI red team](../ai-red-team/SKILL.md) owns adversarial scenarios and PyRIT execution; reuse this skill's trial design and uncertainty reporting.
