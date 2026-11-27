---
name: finops
description: "Model cloud/AI TCO and token unit economics, set billing budgets/quotas, and audit non-human spend."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/finops
  created: "2026-11-21"
  updated: "2026-11-24"
---

# Cloud & AI FinOps

Model, bound, and verify non-human technical spend across compute, warehouses, storage, egress, observability, CI/CD, and AI inference. Delegate human effort/SOW pricing to [proposal](../proposal/SKILL.md) and audit designs via `fmind-review-finops` ([subagent](../subagent/SKILL.md)).

## Workflow

1. **Audit live spend first**: measure baselines across billing exports and ingest meters via [gcloud/bigquery](../gcloud/references/bigquery.md) (billing exports & dry-run scan bytes), [cloud-ops/databricks](../cloud-ops/references/databricks/GUIDE.md) (warehouse/job DBU spend), and [cloud-ops/pup](../cloud-ops/references/pup.md) (log/trace/metric ingest).
1. **Separate alert-only budgets from hard ceilings**: billing budgets (`50%`, `80%`, `100%` actual/forecast + anomaly alerts) notify only and never stop spend. Pair them with hard service quotas, Cloud Billing spend caps, per-tenant circuit breakers, and mandatory labels (`env`, `service`, `owner`, `cost-center`) in [infra-as-code](../infra-as-code/SKILL.md).
1. **Cap compute & scale-to-zero**: keep `min-instances = 0` on [Cloud Run](../gcloud/references/cloud-run/GUIDE.md) and preview stacks unless a latency SLO justifies idle spend; set `max-instances`, concurrency, preview TTLs, and spot/preemptible batch pools.
1. **Bound warehouse, storage & egress**: enforce `maximum_bytes_billed` and partition/cluster pruning per [bigquery](../gcloud/references/bigquery.md); add lifecycle/archive/abort-multipart/TTL rules and image retention; prefer private endpoints over NAT gateways and CDN for public assets.
1. **Control observability & CI burn**: block prod `DEBUG` payload logs, ban high-cardinality metric labels (`user_id`, `request_id`, raw URLs), cap trace sampling/retention, cache CI layers, and skip heavy runners on doc-only diffs.
1. **Model cloud & AI TCO deterministically**: fetch current pricing from primary docs (never memory) and run [tco_model.py](scripts/tco_model.py) (`python3 -I ~/.agents/skills/finops/scripts/tco_model.py scenario.json --json`) for exact `Decimal` monthly/annual totals, `$/1k requests`, `P50`/`P90` spikes, and one-time vs run-rate splits. Apply AI levers before scaling:
   - Route routine work to bulk/flash tiers ([request-contracts](../agent-frameworks/references/request-contracts.md)).
   - Place static instructions/schemas before dynamic context for prompt-cache hits.
   - Check cache-write vs TTL breakeven (`reads/write >= (write_mult - 1) / (1 - read_mult)`): low-reuse prefixes with paid cache writes cost more than uncached calls.
   - Cap multi-turn $O(T^2)$ transcript growth via rolling summaries or compaction caps.
   - Set explicit `max_output_tokens`/thinking effort, deduplicate embeddings by content hash, and shift offline jobs to `50%`-off Batch APIs.
1. **Review adversarially**: freeze IaC/config/model sheets and run `fmind-review-finops` + `fmind-review-factcheck`.

## Gotchas

- **Uncapped autoscalers monetize bugs**: retry loops without `max-instances`, per-tenant rate limits, and hard quotas spike bills before budget alerts fire.
- **Dynamic prefixes bust prompt caches**: putting `now()` or per-user metadata before system prompts drops cache hits to zero ([system-prompts](../agent-frameworks/references/system-prompts.md)).
- **Separate one-time vs run-rate spend**: never blend backfill or migration costs into steady-state monthly unit cost.

## Documentation

- [FinOps Framework](https://www.finops.org/framework/) · [GCP Billing Budgets](https://cloud.google.com/billing/docs/how-to/budgets) · [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- Companions: [gcloud](../gcloud/SKILL.md), [bigquery](../gcloud/references/bigquery.md), [cloud-ops](../cloud-ops/SKILL.md), [agent-frameworks](../agent-frameworks/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md), [proposal](../proposal/SKILL.md).
