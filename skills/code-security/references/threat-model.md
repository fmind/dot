---
name: threat-model
description: "Model attack paths, trust boundaries, abuse cases, and controls."
---

# Threat Model

Identify the few plausible abuse paths that should change the design, plan, or verification strategy. [code-review](code-review/GUIDE.md) runs the scanners, whose output supports but never replaces attack-path reasoning.

## Rules

1. **Keep only concrete paths**: map assets, actors, flows, and trust boundaries from the code, then keep abuse cases with a full path (attacker capability → entry point → missing control → asset impact). Turn high-impact unknowns into verification tasks, list owner statements the code could not confirm as open questions, and send anything a one-line patch would remove to [code-review](code-review/GUIDE.md) as a vulnerability, not a threat.
1. **Default to read-only analysis**: never probe live systems, run exploit code, access customer data, rotate credentials, or change security controls without explicit authorization.
1. **Respect intended autonomy**: distinguish an actor's authorized capabilities from an attacker gaining them. Do not prescribe permission prompts or rewrite harness settings merely because execution is powerful (this workstation runs agents in bypass mode by choice). Hand agent, retrieval, and model abuse cases to [ai-red-team](ai-red-team/GUIDE.md) with both the legitimate operation and the boundary the attacker must not cross.
1. **Feed delivery**: report ranked abuse paths, existing and required controls with how each is verified, residual risks, and owner decisions; prefer secure defaults and fail-closed design over rules every caller must remember, and add required controls and tests to the plan or spec.

## Documentation

- Upstream: the `codex-security` plugin in `openai/plugins` ships a `threat-model` skill; preview it before installing ([vendor-skill policy](../../agent-project/references/vendor-skills.md#name-collisions)).
- Companion skills: [skill-security-review](skill-security-review/GUIDE.md) (third-party skill supply chain), [full-review](../../full-review/SKILL.md) (release readiness).
- Threat-versus-vulnerability test adapted from [defending-code-reference-harness threat-model](https://github.com/anthropics/defending-code-reference-harness/blob/d3bea6b5793b5f3d59a75ebe69a58efa88383145/.claude/skills/threat-model/SKILL.md) (Apache-2.0).
- Adapted from [Trail of Bits sharp-edges](https://github.com/trailofbits/skills/blob/7b9bd5f950f89a9ba71b249b9801c1a95be3928e/plugins/sharp-edges/skills/sharp-edges/SKILL.md), [gstack CSO](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/cso/SKILL.md).
