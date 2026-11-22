---
name: finops
description: "Model cloud/AI unit economics, set billing budgets/quotas, and audit non-human spend."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/finops
  created: "2026-11-21"
  updated: "2026-11-22"
---

# Cloud & AI FinOps

Model, bound, and verify non-human technical spend across compute, warehouses, storage, egress, observability, CI/CD, and AI inference. Delegate human effort/SOW pricing to [proposal](../proposal/SKILL.md) and audit designs via `fmind-review-finops` ([subagent](../subagent/SKILL.md)).

## Workflow

1. **Enforce budgets, quotas & cost tags**: configure billing budgets with actual/forecast alerts (`50%`, `80%`, `100%` + anomaly alerts), hard quota ceilings, per-tenant circuit breakers, and mandatory labels (`env`, `service`, `owner`, `cost-center`) in [infra-as-code](../infra-as-code/SKILL.md).
1. **Cap compute & scale-to-zero**: keep `min-instances = 0` on [Cloud Run](../gcloud/references/cloud-run/GUIDE.md) and preview stacks unless a latency SLO justifies warm capacity; set `max-instances`, concurrency, preview TTLs, and spot/preemptible pools for fault-tolerant batch jobs.
1. **Bound warehouse, storage & egress**: enforce `maximum_bytes_billed` and partition/cluster pruning per [bigquery](../gcloud/references/bigquery.md); add lifecycle/archive/abort-multipart/TTL rules and image retention; prefer private endpoints over NAT gateways for storage/registry pulls and CDN for public assets.
1. **Control observability & CI burn**: block production `DEBUG` payload logs, ban high-cardinality metric labels (`user_id`, `request_id`, raw URLs), cap trace sampling/retention, cache CI layers, and skip heavy runners on doc-only diffs.
1. **Model AI/LLM unit economics in Python**: fetch current provider pricing from primary docs (never memory) and run a short `python3` (`Decimal`) script computing per-workload `$/1k requests`, `$/active user/month`, `P50` vs `P90` traffic spikes, and one-time vs run-rate totals. Apply five levers before scaling:
   - Route routine tasks to bulk/flash tiers ([request-contracts](../agent-frameworks/references/request-contracts.md) owns current model IDs and thinking flags).
   - Keep static instructions/schemas ahead of dynamic context for prompt-cache hits.
   - Set explicit `max_output_tokens` and thinking/reasoning effort.
   - Deduplicate embeddings by content hash.
   - Shift offline and non-interactive jobs to `50%`-discounted Batch APIs.
1. **Review adversarially**: freeze IaC/config/model sheets and run `fmind-review-finops` + `fmind-review-factcheck`.

## Gotchas

- **Uncapped autoscalers monetize bugs**: retry loops or traffic spikes without `max-instances`, per-tenant rate limits, and quota caps run up bills before budget emails fire.
- **Dynamic prefixes bust prompt caches**: putting `now()` or per-user metadata before system prompts/few-shots drops cache hits to zero ([system-prompts](../agent-frameworks/references/system-prompts.md)).
- **Separate one-time vs run-rate spend**: never blend backfill/re-embedding or migration costs into steady-state monthly unit cost.

## Documentation

- [FinOps Foundation Framework](https://www.finops.org/framework/) · [Google Cloud Billing Budgets](https://cloud.google.com/billing/docs/how-to/budgets) · [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- Companion skills: [gcloud](../gcloud/SKILL.md), [bigquery](../gcloud/references/bigquery.md), [agent-frameworks](../agent-frameworks/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md), [proposal](../proposal/SKILL.md).
