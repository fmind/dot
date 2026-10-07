---
name: product-management
description: "Run product discovery, PRDs, launches, and learning; decide build or stop."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/product-management
  created: "2026-08-09"
  updated: "2026-10-07"
---

# Product Management

Move a product bet through discovery, specification, launch, and learning. Enter at the phase supported by the evidence and make the next decision; [implementation-plan](../implementation-plan/SKILL.md) owns repository execution planning.

## Workflow

1. **Recover the bet**: user, painful job, proposed outcome, constraints, current evidence, and the decision being made; enter at the phase the evidence supports.
1. **Challenge the premise**: separate observations, supplied evidence, inference, and assumptions; always keep doing nothing, a manual service, or a smaller change among the alternatives.
1. **Predeclare the test**: behavioral outcome, segment, time box, success and kill thresholds, and guardrails before observing results; prefer commitments over compliments ([demand tests](references/demand-tests.md)).
1. **Close the phase with its verdict**: apply its [checks and brief](references/briefs.md), scaled to the change:

| Phase                                        | Verdict                                                   |
| -------------------------------------------- | --------------------------------------------------------- |
| Discover: problem, demand, or wedge unproven | `BUILD`, `TEST FIRST`, `PARK`, or `STOP`                  |
| Specify: validated intent needs a PRD        | Requirements with acceptance scenarios and open decisions |
| Launch: built capability needs an audience   | `LAUNCH`, `LIMIT EXPOSURE`, or `HOLD`                     |
| Learn: an experiment or launch has results   | `CONTINUE`, `ITERATE`, `PIVOT`, `STOP`, or `EXTEND TEST`  |

## Gotchas

- **Ground every claim in evidence**: never invent quotes, metrics, demand, customer research, availability, or support capacity; effort, code volume, merges, stars, and traffic do not prove customer value.
- **Gate external effects on authorization**: drafts and local artifacts are reviewable work. Customer contact, CRM changes, publication, advertising, and spend require authorization for those effects; a launch plan authorizes none of them.
- **Require readiness before customer exposure**: a customer-facing rollout needs a current [production-readiness](../production-readiness/SKILL.md) result, with its blockers carried forward.
- **Judge against the predeclared design**: keep the original hypothesis, baseline, denominators, segment, and thresholds; explain deviations after observing results instead of moving the goalposts.
- **Never omit unresolved risk**: compact changes get compact briefs, but trust boundaries, edge cases, and open risks always stay visible.

## Documentation

- Companion skills: [implementation-plan](../implementation-plan/SKILL.md) (repository execution after approval), [research-brief](../implementation-plan/references/research-brief.md), [product-design-review](../product-design-review/SKILL.md), [github-issues](../github-issues/SKILL.md) (issue drafts only on request).
- Adapted from [gstack](https://github.com/garrytan/gstack/tree/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df) (office-hours, spec, ship, retro), [Spec Kit](https://github.com/github/spec-kit/blob/684b3d8e05263a7c1948d3d0699ab1cb4f77c3d5/templates/spec-template.md), [pm-skills](https://github.com/phuryn/pm-skills/tree/18468a95b427e70e258b51389796367c6f684e7d), and [marketingskills](https://github.com/coreyhaines31/marketingskills/tree/7868cb9251fad80a73d26e488a5ad5f6c4a9f335).
