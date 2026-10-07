---
name: incident-response
description: "Handle live incidents: triage, containment, recovery, and communication."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/incident-response
  created: "2026-08-08"
  updated: "2026-10-07"
---

# Incident Response

Coordinate diagnosis, containment, recovery, and learning during an active outage, breach, or degradation. Preserve evidence and operate within the incident's established authority.

## Rules

1. **Resolve authority before mutating**: a request for help does not authorize production mutation, credential rotation, customer or external communication, disclosure, or destructive containment. Before acting, present the exact target, expected signal, abort condition, and rollback, and get explicit approval.
1. **Prefer the safest reversible mitigation**: rank options by time to relief, reversibility, and secondary risk; preserve forensic evidence before containment changes it.
1. **Freeze unrelated work**: no unrelated changes or speculative fixes while the incident is active.
1. **Treat silence as a gap**: missing telemetry, stale dashboards, and a quiet alert are unknowns, not recovery. Recovery means critical journeys, data correctness, and queued work verified over a predeclared window.
1. **Never promise recovery times**: updates state impact, current state, actions, next checkpoint, and known unknowns; the responsible owner sends anything external.
1. **Keep one incident record**: severity, impact, roles, a UTC timeline separating facts from hypotheses, each mitigation with its authority and result, and residual risks with owners. Close only after sustained recovery, with temporary safeguards kept until an owner and test cover their removal; postmortems are blameless and stay inside the evidence.

## Documentation

- Companion skills: [cloud-run](../cloud-run/SKILL.md) (revision rollback), [gcloud](../gcloud/SKILL.md) (logs, audits, and IAM reads), [systematic-debugging](../systematic-debugging/SKILL.md) (root cause after stabilization), [threat-model](../threat-model/SKILL.md) (security design follow-up), [production-readiness](../production-readiness/SKILL.md) (pre-launch gate).
- Adapted from [agency-agents incident response](https://github.com/msitarzewski/agency-agents/blob/ebe9c99acb5c96f9468de368d8bead775387d1a7/engineering/engineering-incident-response-commander.md) and [gstack canary](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/canary/SKILL.md).
