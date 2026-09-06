---
name: production-readiness
description: "Audit production operability and operational fitness: go/no-go, rollback, migrations, observability, recovery, support and halt thresholds; separate local, exact-head CI, runtime, deployed, and public release proof."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/production-readiness
  created: "2026-08-08"
  updated: "2026-09-05"
---

# Production Readiness

Decide whether the exact candidate can be operated safely. The audit produces a go/no-go recommendation; deployment, migration, and publication follow the user's existing authorization.

## Workflow

1. **Identify the candidate**: immutable revision/artifact, configuration, environment, schema/dependency versions, proposed rollout, and dirty-tree boundary.
1. **Define acceptance**: critical journeys, correctness/availability, capacity/cost, data-loss tolerance, owners, and hard stop conditions.
1. **Review the delta**: inspect security, identity, migrations, observability, recovery, support, and one-way transitions using the [detailed procedure](references/procedure.md) for the relevant risks.
1. **Qualify**: run `mise run all` against the materialized candidate and only authorized runtime checks; preserve exact evidence, failed gates, and unavailable proof.
1. **Plan recovery**: smallest reversible exposure, observation window, halt thresholds, rollback owner/mechanism, and verification after rollback.
1. **Decide**: GO, GO WITH CHANGES, or NO-GO; report blockers, evidence, remaining actions, and the highest proven state below.

## Proof Boundaries

Keep source readiness, local checks, CI for the exact commit, runtime behavior, target deployment, and published availability distinct. Every claim names the artifact, environment, observation, time, and source; a pass at one boundary does not establish the next.

## Gotchas

- **Implicit authority**: Name any action that needs credentials, production access, external coordination, spend, or human approval instead of performing it.
- **Borrowed evidence**: A green run, probe, or deployment for a different revision or environment proves nothing about this candidate.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- Companion skills: [quality-assurance](../quality-assurance/SKILL.md) (test campaign), [release](../release/SKILL.md) (publishing), [cloud-run](../cloud-run/SKILL.md) (deploy and rollback), [incident-response](../incident-response/SKILL.md) (active outage), [product-loop](../product-loop/SKILL.md) (audience, positioning, public rollout), [threat-model](../threat-model/SKILL.md) (design risk), [secure](../secure/SKILL.md) (repository evidence).
