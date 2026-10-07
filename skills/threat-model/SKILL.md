---
name: threat-model
description: "Model attack paths, trust boundaries, abuse cases, and controls."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/threat-model
  created: "2026-08-08"
  updated: "2026-10-07"
---

# Threat Model

Identify the few plausible abuse paths that should change the design, plan, or verification strategy; [code-security](../code-security/references/code-review/GUIDE.md) runs the scanners, whose output supports but never replaces attack-path reasoning, and [incident-response](../incident-response/SKILL.md) handles a live breach.

## Rules

1. **Model only what changes decisions**: scope the system and the decision the model informs; map assets, actors, flows, and trust boundaries from evidence, then keep only abuse cases with a concrete path (attacker capability → entry point → missing control → asset impact). Drop category-only concerns.
1. **Default to read-only analysis**: never probe live systems, run exploit code, access customer data, rotate credentials, or change security controls without explicit authorization.
1. **Ground the model in facts**: never invent endpoints, attackers, compliance obligations, or exploitability; promote high-impact unknowns to verification tasks, not confirmed vulnerabilities.
1. **Respect intended autonomy**: distinguish an actor's authorized capabilities from an attacker gaining them. Do not prescribe permission prompts or rewrite harness settings merely because execution is powerful (this workstation runs agents in bypass mode by choice). Hand agent, retrieval, and model abuse cases to [ai-red-team](../ai-red-team/SKILL.md) with both the legitimate operation and the boundary the attacker must not cross.
1. **Prefer design over warnings**: misuse-resistant types, secure defaults, least privilege, isolation, and fail-closed behavior beat rules every caller must remember.
1. **Feed delivery**: report ranked abuse paths, existing and required controls with how each is verified, residual risks, and owner decisions; add required controls and tests to the plan or spec.

## Documentation

- Upstream: the `codex-security` plugin in `openai/plugins` ships a same-name `threat-model`; preview it, never install it beside this skill ([vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)).
- Companion skills: [sops-secrets](../sops-secrets/SKILL.md) (secret design), [system-prompts](../system-prompts/SKILL.md) (prompt-injection boundaries for agents), [skill-security-review](../skill-security-review/SKILL.md) (third-party skill supply chain), [production-readiness](../production-readiness/SKILL.md) (launch gate).
- Adapted from [Trail of Bits sharp-edges](https://github.com/trailofbits/skills/blob/7b9bd5f950f89a9ba71b249b9801c1a95be3928e/plugins/sharp-edges/skills/sharp-edges/SKILL.md), [gstack CSO](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/cso/SKILL.md).
