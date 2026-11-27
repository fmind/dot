---
name: sre
description: "Design SLOs, rollouts, zero-downtime migrations, resilience defaults, runbooks, postmortems, and live incident triage."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sre
  created: "2026-11-24"
  updated: "2026-11-24"
---

# Site Reliability Engineering

Design operable production services, safe rollouts, zero-downtime migrations, resilience defaults, operational runbooks, and blameless postmortems. Scale rigor to runtime risk: skip distributed-tracing and circuit-breaker ceremony on local CLIs or cold paths (`N < 50`).

## Reliability & Rollout Defaults

1. **SLOs & multi-window burn-rate alerts**: define user-symptom SLIs/SLOs (availability, `p95`/`p99` latency, data freshness, queue lag) and multi-window error-budget burn-rate alerts instead of noisy raw-CPU triggers. Emit structured logs with request/trace correlation IDs and keep metric label cardinality bounded (never `user_id`, `request_id`, or raw URLs).
1. **Expand-contract N-1 zero-downtime migrations**: during rolling deploys and minute-scale rollbacks, `N-1` and `N` run concurrently against shared DBs, caches, and queues. Split breaking schema, cache, or wire changes into expand → backfill/dual-write → cutover → contract releases without hot table-locking DDL; validate required config upfront at boot and drain in-flight work on `SIGTERM`.
1. **Bounded resilience defaults**: set explicit connect + read/deadline timeouts on every outbound HTTP, DB, RPC, or subprocess call; bound exponential retries with jitter and retry budgets (idempotent operations only, never `4xx`); add circuit breakers, semaphore/worker backpressure, and DLQs with max-delivery caps on async consumers.
1. **Capacity & pool sizing**: reuse pooled HTTP/DB clients sized to upstream connection limits, eliminate N+1 hot loops and eager full-dataset loads, bound in-memory cache sizes/TTLs, and benchmark optimizations against a reproducible warmed baseline (`p95`/`p99`) before adding complexity.
1. **Live incident triage**: mitigate user impact first (rollback, traffic shift, feature flag, load shed) before root-cause deep dives. Run bounded read-only diagnostics (`--project`, `--context`, time window, `--limit`) and preserve logs/metrics/timelines before containment; **never** destructively mutate production state, rotate keys, or send external comms/ETAs without explicit owner approval.
1. **Audit readiness**: verify live endpoints via [http-probing](../full-review/references/http-probing.md) and review operational changes with `fmind-review-sre`, `fmind-review-security`, `fmind-review-finops`, and `fmind-review-docs` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [runbook-postmortem](references/runbook-postmortem.md): Write Day-2 operational runbooks, safe cutover plans, SLO alerts, and blameless incident postmortems.

<!-- guides:end -->

## Documentation

- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/) · [Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) · [Postmortem Culture](https://sre.google/workbook/postmortem-culture/)
- Companions: [http-probing](../full-review/references/http-probing.md), [cloud-run](../gcloud/references/cloud-run/GUIDE.md), [containers](../containers/SKILL.md), [postgres](../sql/references/postgres.md), [adr-rfc](../docs/references/adr-rfc.md), [humanize](../humanize/SKILL.md).
