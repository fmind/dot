---
name: runbook-postmortem
description: "Write Day-2 operational runbooks, safe cutover plans, SLO alerts, and blameless incident postmortems."
---

# Runbooks, Cutovers & Postmortems

Author Day-2 operational runbooks, production cutover checklists, and blameless incident postmortems that an unfamiliar on-call engineer can execute under pressure without tribal context. Pair executive incident updates with [humanize](../../humanize/SKILL.md) and architecture trade-offs with [adr-rfc](adr-rfc.md).

## Operational Runbooks (`docs/runbooks/<service>.md`)

Keep each runbook scannable in under 2 minutes with verified, copy-pasteable commands:

1. **Service card & blast radius**: owner/escalation path, runtime/region/project, critical upstream/downstream dependencies, and links to live dashboards/logs (never embed secrets or internal tokens in public repos).
1. **User-symptom triggers**: organize playbooks around user-facing SLO symptoms (availability, latency, freshness, queue backlog)—not noisy cause alerts like transient CPU spikes.
1. **Bounded read-only diagnostics first**: provide pinned commands (`--project`, `--context`, time window, `--limit`) across [gcloud](../../gcloud/SKILL.md), [pup](../../cloud-ops/references/pup.md), [kubernetes](../../containers/references/kubernetes/GUIDE.md), or [postgres](../../sql/references/postgres.md) to isolate scope and capture evidence before changing state.
1. **Safe mitigations & minute-scale rollback**: document exact reversible steps (traffic shift, feature flag, image pin, worker scale-down), `N-1` compatibility constraints, and post-mitigation verification checks.

## Cutover & Migration Plans

Before executing a risky rollout, schema migration, or provider cutover:

- **Pre-flight**: record backups/snapshots, verify rollback permissions, confirm expand-contract `N-1` safety, and freeze a baseline metric snapshot.
- **Phased steps & abort gates**: list numbered steps with explicit verification checks (`exit 0`, SLO green) and quantitative abort triggers after each phase.
- **Rehearsed rollback**: write the exact undo commands before starting, verified on staging or a snapshot.

## Blameless Postmortems (`docs/postmortems/YYYY-MM-DD-<slug>.md`)

Focus strictly on system design, observability, and guardrail gaps—never individual blame:

1. **Executive summary**: UTC start/detection/mitigation/recovery times, user/SLO blast radius, severity, and primary mitigation.
1. **UTC timeline**: concise chronological log linking alerts, dashboards, PRs, and operator decisions (no raw terminal dumps).
1. **Root cause & contributing factors**: why the failure occurred, why automated gates/alerts missed or delayed detection, and what worked well.
1. **Bounded follow-ups**: each action item needs a type (`prevent`, `detect`, or `mitigate`), single owner, linked issue, and target date—prefer deterministic checks, quotas, timeouts, and circuit breakers over _"be more careful"_ notes.

## Boundaries & Review

- **Live incidents**: preserve evidence before containment; never mutate production, rotate keys, or send external comms/ETAs without explicit owner authority.
- **Audit**: review operational readiness with `fmind-review-sre`, clarity with `fmind-review-docs` / `fmind-review-human`, and security incidents with `fmind-review-security` ([subagent](../../subagent/SKILL.md)).

## Documentation

- [Google SRE Workbook — Postmortem Culture](https://sre.google/workbook/postmortem-culture/) · [Google SRE — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- Companions: [adr-rfc](adr-rfc.md), [humanize](../../humanize/SKILL.md), [python/observability](../../python/references/observability.md), [full-review](../../full-review/SKILL.md).
