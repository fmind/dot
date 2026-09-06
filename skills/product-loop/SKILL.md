---
name: product-loop
description: Run the product loop — discover, specify, launch, learn — with build-or-stop calls, MVP, demand tests, PRDs, journeys, acceptance, positioning, onboarding, rollout, pricing, pivots. Use when deciding, launching, or reviewing a product bet.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/product-loop
  created: "2026-08-09"
  updated: "2026-09-05"
---

# Product Loop

Move a product bet through discovery, specification, launch, and learning. Enter at the phase supported by the evidence and make the next decision; [implementation-plan](../implementation-plan/SKILL.md) owns repository execution planning.

## Workflow

1. **Recover the bet**: identify the user, painful job, proposed outcome, constraints, current evidence, and the decision being made.
1. **Select one phase** from the table; read its procedure and the relevant [brief](references/briefs.md), omitting sections that add no useful information.
1. **Test the premise**: distinguish observations, supplied evidence, inference, and assumptions; compare a smaller change and a credible no-build path.
1. **Define the decision**: choose a behavioral outcome, segment, time box, success threshold, guardrails, and evidence that would stop or reverse the plan.
1. **Close the phase** with the decision, its evidence, remaining uncertainty, and the smallest next step within the user's scope.

| Situation                                  | Read when needed                                                                         | Decision                                     |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- | -------------------------------------------- |
| Problem, demand, or wedge is unproven      | [Discover](references/discover.md), [demand tests](references/demand-tests.md)           | Build, test first, park, or stop             |
| Validated intent needs observable behavior | [Specify](references/specify.md)                                                         | Requirements, acceptance, and open decisions |
| Built capability needs a bounded audience  | [Launch](references/launch.md), [production-readiness](../production-readiness/SKILL.md) | Launch, limit exposure, or hold              |
| An experiment or launch produced results   | [Learn](references/learn.md)                                                             | Continue, iterate, pivot, stop, or extend    |

## Gotchas

- **Evidence**: never invent quotes, metrics, demand, customer research, availability, or support capacity; effort and traffic alone do not prove customer value.
- **Authority**: drafts and local planning artifacts are reviewable work. Customer contact, CRM changes, publication, advertising, and spend require authorization for those effects.
- **Learning**: retain the original hypothesis, baseline, denominators, segment, thresholds, and uncertainty; explain deviations after observing results.
- **Scope**: compact changes need compact briefs; preserve material trust boundaries, edge cases, and unresolved risks.

## Documentation

- [Source methods](references/sources.md)
- Companion skills: [technical-research](../technical-research/SKILL.md), [product-design-review](../product-design-review/SKILL.md), [project-backlog](../project-backlog/SKILL.md).
