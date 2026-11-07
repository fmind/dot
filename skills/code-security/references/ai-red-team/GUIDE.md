---
name: ai-red-team
description: "Red-team AI apps and agents with PyRIT: prompt injection, tool misuse, and agent authority."
---

# AI Red Team

Turn a concrete AI attack path into a reproducible assessment and regression test. [threat-model](../threat-model.md) owns architectural analysis, [code-review](../code-review/GUIDE.md) owns source and dependency review, and [agent-evaluation](../../../agent-evaluation/SKILL.md) owns repeated-trial comparisons. PyRIT is the runner, installed in a project-local `uv` environment.

## Workflow

1. **Record the boundary**: fill the [assessment record](templates/assessment.md) with the application revision, model, retrieval sources, actors, tools, and granted authority. Reuse established target, data, action, and cost authorization, and proceed autonomously within it. Keep customer evidence in the assessment project.
1. **Choose plausible cases**: select from [attack cases](references/attack-cases.md). For each case, name the attacker-controlled surface, required access, protected asset, and forbidden outcome, plus the legitimate action that must still succeed.
1. **Exercise the real enforcing boundary**: drive the application, not a bare model endpoint, and capture attempted tool calls and resulting state. Use disposable records, synthetic markers, and controlled destinations; never use a real secret as a marker.
1. **Prepare PyRIT**: follow [PyRIT execution](references/pyrit.md) for the released API, target adapter, local smoke, and campaign limits. Freeze package, prompt, dataset, converter, scorer, and application identities before comparative runs.
1. **Validate before the campaign**: prove the input reaches the target and that the outcome check catches a deliberately broken control in a fixture. Keep target, evaluator, and security failures separate.
1. **Verify and retest**: reproduce suspicious results and label them confirmed, refuted, or unresolved. When a fix is authorized, add a deterministic regression, then repeat the original attack, nearby variants, and legitimate tasks under the same budgets.

## Gotchas

- **Autonomy is intentional**: a finding is untrusted content gaining authority beyond the declared contract. Powerful tools or missing per-action prompts are not findings, and an assessment never changes the user's harness permissions.
- **Judge by state, not by the model**: a refusal followed by a forbidden tool call is a failure, and a model claiming it read a secret is not exfiltration. Record attempted actions, blocked actions, and completed effects separately, as the template's columns do.
- **Scoring is not containment**: PyRIT generates and scores tests; the environment and application enforce tool, data, and spending limits. A request timeout does not prove a remote run stopped.

## Documentation

- [PyRIT](https://microsoft.github.io/PyRIT/latest/) · [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [MITRE ATLAS](https://atlas.mitre.org/)
- Releases: [PyRIT](https://github.com/microsoft/PyRIT/releases)
- Companion skill: [agent-frameworks](../../../agent-frameworks/SKILL.md) (agent and prompt layering).
