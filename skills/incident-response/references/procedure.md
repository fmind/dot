# Incident Response Procedure

Read for the detailed campaign, protocol, or reporting requirements when the task needs them.

1. **Open the incident**: Record UTC start, reporter, affected service and environment, candidate artifact or configuration, first symptom, known user impact, and the incident channel; name one commander, one operator, and one communicator even when one person holds all three, and set the next update time.
1. **Classify severity**: Rank actual and plausible harm across availability, integrity, confidentiality, safety, money, legal exposure, scope, duration, and reversibility; escalate on impact, not noise volume.
1. **Keep a timeline**: Append observations, hypotheses, decisions, commands, actors, and outcomes with timestamps; keep facts apart from interpretation and preserve original evidence references.
1. **Bound the blast radius**: Determine affected tenants, regions, versions, data, workflows, dependencies, and time window; check whether it is still expanding and pick the fastest reliable user-impact signal.
1. **Generate mitigations**: Compare rollback, traffic reduction, feature disablement, isolation, capacity increase, dependency bypass, and safe degraded mode; rank by time to relief, reversibility, secondary risk, and proof quality, and prefer the safest reversible mitigation.
1. **Authorize and stabilize**: Present the recommended action, exact target, expected signal, abort condition, and rollback before executing; act only within explicit authority, then watch the predeclared health window.
1. **Verify recovery**: Confirm critical user journeys, error and saturation signals, data correctness, queued work, security posture, and no continued spread; a quiet alert alone is not recovery.
1. **Communicate**: Send concise updates with impact, current state, actions, next checkpoint, and known unknowns. Do not promise recovery times or send external communications without the responsible owner.
1. **Close carefully**: End active response only after sustained recovery, cleanup ownership, evidence retention, residual-risk review, and handoff; keep temporary safeguards until their removal has a named test and owner.
1. **Run the postmortem**: Hold a blameless review with causal analysis, control gaps, concrete owners, and verification dates; keep the narrative inside the evidence and route security design follow-ups to [threat-model](../threat-model/SKILL.md).
1. **Maintain the record**: Keep one incident document with:
   - severity, impact, scope, current state, role owners, and next update time;
   - the timestamped timeline and working hypotheses with confirming and disconfirming evidence;
   - each mitigation with its authority, target, abort condition, and result, plus recovery checks and observation window;
   - customer, security, legal, and disclosure coordination gaps, and residual risks with owners and due dates.

## Sources

- Adapted from [agency-agents incident response](https://github.com/msitarzewski/agency-agents/blob/ebe9c99acb5c96f9468de368d8bead775387d1a7/engineering/engineering-incident-response-commander.md), [gstack canary](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/canary/SKILL.md).
