---
name: agents-md
description: "Write concise AGENTS.md instructions grounded in repository commands, constraints, and layout. Use when creating or restructuring agent guidance and its conventions."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agents-md
  created: "2026-09-05"
  updated: "2026-09-05"
---

# Write AGENTS.md

Give an agent the repository-specific information needed to make the requested change correctly. [agent-project](../agent-project/SKILL.md) owns host setup; [update-docs](../update-docs/SKILL.md) reconciles instructions with current code.

## Workflow

1. **Inspect the contract**: read ancestor and local instructions, manifests, mise tasks, hooks, CI, and the relevant source tree; identify rules that differ from global defaults.
1. **State identity and scope**: a short project purpose, supported stack, and links to human setup documentation; explain which subtree a nested instruction file governs.
1. **Document verified commands**: setup, focused checks, complete gate, build, and watch using the repository's actual task names; separate workstation checks and consequential release/deploy operations.
1. **Record local invariants**: architecture seams, generated-file ownership, source versus deployed paths, private-data constraints, and known validation requirements. Explain non-obvious rules briefly.
1. **Map the layout**: list the important top-level paths with one sentence each; link multi-step workflows to `.agents/skills/<name>/SKILL.md` or the relevant shared skill.
1. **Verify and trim**: run safe documented commands and link/format checks; remove stale advice, copied global rules, and commands the repository does not provide.

## Gotchas

- **One instruction body**: keep shared rules in `AGENTS.md`; use host bridges from agent-project instead of maintaining diverging copies.
- **Defaults and authority**: distinguish hard repository invariants from recommendations; preserve authorization already granted by the user and ask only when a concrete boundary requires it.
- **Progressive disclosure**: use [skillify](../skillify/SKILL.md) for reusable procedures; keep rules, command entry points, and navigation in the root.
- **Portable prose**: use repository-relative or `~`-relative paths, unwrapped paragraphs, `1.` lists, and language-tagged fences; never include credentials or transient session state.

## Documentation

- [AGENTS.md conventions](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification)
- Companion skills: [readme-md](../readme-md/SKILL.md), [agent-project](../agent-project/SKILL.md), [skillify](../skillify/SKILL.md), [update-docs](../update-docs/SKILL.md).
