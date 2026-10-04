---
name: incident-response
description: "Handle live incidents: triage, containment, recovery, and communication."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/incident-response
  created: "2026-08-08"
  updated: "2026-10-04"
---

# Incident Response

Coordinate diagnosis, containment, recovery, and learning during an active outage, breach, or degradation. Preserve evidence and operate within the incident's established authority.

## Workflow

1. **Open the incident**: record UTC start, reporter, affected service and environment, candidate artifact or configuration, first symptom, known user impact, and the incident channel; name one commander, one operator, and one communicator even when one person holds all three, and set the next update time.
1. **Classify severity**: rank actual and plausible harm across availability, integrity, confidentiality, safety, money, legal exposure, scope, duration, and reversibility; escalate on impact, not noise volume.
1. **Keep a timeline**: append observations, hypotheses, decisions, commands, actors, and outcomes with timestamps; anchor it on the last known good state and recent changes, draw on logs, metrics, and traces, keep facts apart from interpretation, and preserve original evidence references.
1. **Bound the blast radius**: determine affected tenants, regions, versions, data, workflows, dependencies, and time window; check whether it is still expanding and pick the fastest reliable user-impact signal.
1. **Generate mitigations**: compare rollback, traffic reduction, feature disablement, isolation, capacity increase, dependency bypass, and safe degraded mode; rank by time to relief, reversibility, secondary risk, and proof quality, and prefer the safest reversible mitigation.
1. **Authorize and stabilize**: present the recommended action, exact target, expected signal, abort condition, and rollback before executing; preserve forensic evidence and act only within explicit authority, then watch the predeclared health window.
1. **Verify recovery**: confirm critical user journeys, error and saturation signals, data correctness, queued work, security posture, and no continued spread; a quiet alert alone is not recovery.
1. **Communicate**: send concise updates with impact, current state, actions, next checkpoint, and known unknowns. Do not promise recovery times or send external communications without the responsible owner.
1. **Close carefully**: end active response only after sustained recovery, cleanup ownership, evidence retention, residual-risk review, and handoff; keep temporary safeguards until their removal has a named test and owner.
1. **Run the postmortem**: hold a blameless review with causal analysis, control gaps, concrete owners, and verification dates; keep the narrative inside the evidence and route security design follow-ups to [threat-model](../threat-model/SKILL.md).
1. **Maintain the record**: keep one incident document with:
   - severity, impact, scope, current state, role owners, and next update time;
   - the timestamped timeline and working hypotheses with confirming and disconfirming evidence;
   - each mitigation with its authority, target, abort condition, and result, plus recovery checks and observation window;
   - customer, security, legal, and disclosure coordination gaps, and residual risks with owners and due dates.

## Gotchas

- **Authority**: A request for help does not itself authorize production mutation, credential rotation, customer communication, disclosure, or destructive containment; resolve target, blast radius, rollback, and authority before any mutation.
- **Freeze the rest**: Stop unrelated changes and speculative fixes for the duration of the incident.
- **Silence is a gap**: Missing telemetry, stale dashboards, and quiet alerts are unknowns, not reassurance.

## Documentation

- Companion skills: [cloud-run](../cloud-run/SKILL.md) (revision rollback), [gcloud](../gcloud/SKILL.md) (logs, audits, and IAM reads), [systematic-debugging](../systematic-debugging/SKILL.md) (root cause after stabilization), [threat-model](../threat-model/SKILL.md) (security design follow-up), [production-readiness](../production-readiness/SKILL.md) (pre-launch gate).
- Adapted from [agency-agents incident response](https://github.com/msitarzewski/agency-agents/blob/ebe9c99acb5c96f9468de368d8bead775387d1a7/engineering/engineering-incident-response-commander.md) and [gstack canary](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/canary/SKILL.md).
