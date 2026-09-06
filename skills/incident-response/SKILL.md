---
name: incident-response
description: Coordinate a live outage, breach, or degradation affecting users. Establish incident command; triage, contain harm, bound blast radius, preserve evidence, communicate, roll back, verify restoration.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/incident-response
  created: "2026-08-08"
  updated: "2026-09-05"
---

# Incident Response

Coordinate diagnosis, containment, recovery, and learning during an active outage, breach, or degradation. Preserve evidence and operate within the incident's established authority.

## Workflow

1. **Establish control**: scope, severity, affected users/systems, incident owner, authorized responders, communication channel, and decision log.
1. **Triage from evidence**: timeline, last known good state, symptoms, recent changes, logs/metrics/traces, and explicit hypotheses.
1. **Contain**: choose the smallest reversible action that reduces harm; preserve forensic evidence and confirm destructive or consequential steps against the actual incident authority.
1. **Restore and verify**: execute the selected mitigation/rollback, test critical journeys, and observe stability through the agreed window.
1. **Communicate and learn**: give factual updates through authorized channels, distinguish observations from hypotheses, and record causes, residual risk, and concrete follow-up work.

## Gotchas

- **Authority**: A request for help does not itself authorize production mutation, credential rotation, customer communication, disclosure, or destructive containment; resolve target, blast radius, rollback, and authority before any mutation.
- **Freeze the rest**: Stop unrelated changes and speculative fixes for the duration of the incident.
- **Silence is a gap**: Missing telemetry, stale dashboards, and quiet alerts are unknowns, not reassurance.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- Companion skills: [cloud-run](../cloud-run/SKILL.md) (revision rollback), [gcloud](../gcloud/SKILL.md) (logs, audits, and IAM reads), [systematic-debugging](../systematic-debugging/SKILL.md) (root cause after stabilization), [threat-model](../threat-model/SKILL.md) (security design follow-up), [production-readiness](../production-readiness/SKILL.md) (pre-launch gate).
