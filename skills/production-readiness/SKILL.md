---
name: production-readiness
description: "Assess release go/no-go: operability, rollout, recovery, and support."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/production-readiness
  created: "2026-08-08"
  updated: "2026-10-07"
---

# Production Readiness

Decide whether the exact candidate can be operated safely. The audit produces a go/no-go recommendation; deployment, migration, and publication follow the user's existing authorization.

## Workflow

1. **Resolve the candidate**: record repository state, revision, artifact or image digest, configuration set, environment, dependency and schema versions, and the proposed rollout window; preserve dirty worktrees and never infer exact-head CI from another revision.
1. **Define working**: state critical user journeys, availability and correctness expectations, latency or capacity thresholds, data-loss tolerance, compliance constraints, owners, and explicit stop conditions.
1. **Inspect the release delta**: review code, dependency, configuration, infrastructure, identity, data, and operational changes; identify one-way doors, coupled releases, hidden manual steps, and compatibility windows.
1. **Audit security and identity**: use [threat-model](../threat-model/SKILL.md) for design risk and [code-security](../code-security/references/code-review/GUIDE.md) for repository evidence.
1. **Audit data and migrations**: verify forward and backward compatibility, rehearsal evidence, lock and duration risk, backup and restore, rollback semantics, data validation, and ownership of irreversible transitions. [data-migration](../data-migration/SKILL.md) owns implementation and rehearsal; this skill assesses its evidence.
1. **Audit capacity and cost**: compare measured demand and headroom with explicit thresholds and cost guardrails, without inventing traffic evidence.
1. **Audit rollout and recovery**: prefer the smallest reversible exposure; define preflight checks, canary or staged progression, health windows, stop signals (including SLO error-budget remaining and burn rate where an SLO exists), the rollback owner and mechanism (see [cloud-run](../cloud-run/SKILL.md) for revision rollback), and post-rollback verification.
1. **Audit observability and operations**: each critical journey and failure mode has an actionable alert, an owner, a tested runbook, and an escalation path.
1. **Gate the candidate**: run the repository's full gate (`mise run all` where defined) against the materialized candidate; when the tree carries unrelated changes, apply the [dirty-tree rule](../mise/SKILL.md#gotchas).
1. **Verify proportionally**: run only the authorized runtime or staging checks. Failed, stale, unavailable, or differently scoped evidence remains a gap.
1. **Place the candidate on the proof ladder**: never collapse these states; a candidate may be ready at one rung and blocked at the next, and every claim records artifact identity, environment, command or observation, timestamp, and source.
   - `source-ready`: the intended source and configuration are reviewable.
   - `local-green`: the repository-owned local checks pass for the candidate.
   - `exact-head-CI`: required CI passes for the exact immutable revision.
   - `runtime-proven`: the built artifact works across the authorized runtime boundary.
   - `deployed`: that artifact is running in the target environment.
   - `release-published`: the intended audience can obtain the released result (see [release](../git-delivery/references/release/GUIDE.md)).
1. **Record the gates**: for each material gate report its status (pass, fail, blocked, or not run), exact evidence, owner, and smallest next step; lead with blockers, then gaps, verified gates, rollback plan, highest proven rung, and recommendation.
1. **Decide**: return `GO`, `GO WITH CHANGES`, or `NO-GO`; authority, schedule pressure, and sunk cost cannot turn a failed hard gate into `GO`.

## Gotchas

- **Credentials alone grant no authority**: Reuse established authority for scoped runtime checks. Name missing authority for production mutation, external coordination, or spend; the presence of credentials alone supplies none.
- **Never borrow another revision's evidence**: A green run, probe, or deployment for a different revision or environment proves nothing about this candidate.

## Documentation

- Companion skills: [quality-assurance](../quality-assurance/SKILL.md) (test campaign), [release](../git-delivery/references/release/GUIDE.md) (publishing), [cloud-run](../cloud-run/SKILL.md) (deploy and rollback), [incident-response](../incident-response/SKILL.md) (active outage), [product-loop](../product-loop/SKILL.md) (audience, positioning, public rollout), [threat-model](../threat-model/SKILL.md) (design risk), [code-security](../code-security/references/code-review/GUIDE.md) (repository evidence).
- Adapted from [ECC production audit](https://github.com/affaan-m/ECC/blob/59a99d669f5466d99d5be8b6fce8c5f2677766d0/skills/production-audit/SKILL.md) and [agent-skills shipping and launch](https://github.com/addyosmani/agent-skills/blob/1401c8b8030e023baeebb31781a6653fe8e93026/skills/shipping-and-launch/SKILL.md).
