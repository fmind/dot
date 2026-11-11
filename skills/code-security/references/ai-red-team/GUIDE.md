---
name: ai-red-team
description: "Red-team AI apps and agents with PyRIT: prompt injection, tool misuse, and agent authority."
---

# AI Red Team

Turn concrete AI attack paths into reproducible PyRIT assessments and regression tests inside a project-local `uv` environment. [threat-model](../threat-model.md) owns design analysis, [code-review](../code-review/GUIDE.md) owns source/dependency audits, and [evaluation](../../../agent-frameworks/references/evaluation/GUIDE.md) owns multi-trial comparisons.

## Workflow

1. **Record the boundary**: fill [assessment.md](templates/assessment.md) with app revision, model, retrieval, actors, tools, and granted authority; stay within authorized targets/data/budget and keep customer evidence in-project.
1. **Select cases** from [attack-cases.md](references/attack-cases.md), pairing each attacker surface, access level, asset, and forbidden outcome with the legitimate action that must still pass.
1. **Target the real enforcement boundary** (never a bare model endpoint), capturing attempted tool calls and resulting state with disposable records, controlled sinks, and synthetic markers (never real secrets).
1. **Configure PyRIT** per [pyrit.md](references/pyrit.md), freezing package, prompt, dataset, converter, scorer, and app versions before comparative runs.
1. **Validate the harness**: confirm inputs reach the target and outcome checks fail on a deliberately broken fixture, separating target, scorer, and security failures.
1. **Verify and retest**: reproduce hits (`confirmed`, `refuted`, or `unresolved`); on authorized fixes, add a deterministic regression and re-run the attack, variants, and legitimate control cases under identical budgets.

## Gotchas

- **Autonomy is intentional**: findings require untrusted input exceeding declared authority—powerful tools or absent per-action prompts are not findings, and assessments never alter harness permissions.
- **Grade state, not claims**: a refusal followed by a forbidden call fails, while hallucinated secret reads are not exfiltration; log attempted, blocked, and completed actions separately.
- **Scoring is not containment**: enforce tool, data, and spend caps in the app and environment; client timeouts do not stop remote runs.

## Documentation

- [PyRIT](https://microsoft.github.io/PyRIT/latest/) · [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [MITRE ATLAS](https://atlas.mitre.org/)
- Releases: [PyRIT](https://github.com/microsoft/PyRIT/releases)
- Companion skill: [agent-frameworks](../../../agent-frameworks/SKILL.md).
