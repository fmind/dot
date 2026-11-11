---
name: threat-model
description: "Model attack paths, trust boundaries, abuse cases, and controls."
---

# Threat Model

Surface plausible design-level abuse paths that change architecture, plans, or tests; [code-review](code-review/GUIDE.md) owns scanner runs and point vulnerabilities.

## Rules

1. **Require concrete paths**: trace assets, actors, flows, and trust boundaries in code, keeping only full chains (attacker capability → entry point → missing control → impact). Turn critical unknowns into verification tasks, flag unverified owner claims, and route one-line bugs to [code-review](code-review/GUIDE.md).
1. **Stay read-only**: never probe live systems, run exploits, touch customer data, rotate keys, or alter controls without approval.
1. **Preserve intentional autonomy**: separate granted privileges from untrusted escalation—do not add approval prompts to bypass-by-choice harnesses; hand AI/retrieval/tool abuse paths (with paired legitimate controls) to [ai-red-team](ai-red-team/GUIDE.md).
1. **Drive design**: report ranked paths, fail-closed controls and their verification tests, residual risks, and owner decisions.

## Documentation

- Upstream: `codex-security` (`threat-model` in `openai/plugins`; preview per [vendor-skill policy](../../agent-project/references/vendor-skills.md#name-collisions)).
- Companion skills: [skill-security-review](skill-security-review/GUIDE.md), [full-review](../../full-review/SKILL.md).
- Adapted from [defending-code-reference-harness threat-model](https://github.com/anthropics/defending-code-reference-harness/blob/d3bea6b5793b5f3d59a75ebe69a58efa88383145/.claude/skills/threat-model/SKILL.md) (Apache-2.0), [Trail of Bits sharp-edges](https://github.com/trailofbits/skills/blob/7b9bd5f950f89a9ba71b249b9801c1a95be3928e/plugins/sharp-edges/skills/sharp-edges/SKILL.md), and [gstack CSO](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/cso/SKILL.md).
