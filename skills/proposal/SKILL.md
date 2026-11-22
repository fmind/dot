---
name: proposal
description: "Draft commercial proposals, ROI/steering memos, SOWs, and WBS/P10-P90 effort estimates with verified math."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/proposal
  created: "2026-11-21"
  updated: "2026-11-22"
---

# Proposals, SOWs & Effort Sizing

Deliver executive-ready proposals, SOWs, steering memos, and effort estimates without optimism bias, missing overhead, or arithmetic drift. Pair prose with [humanize](../humanize/SKILL.md), delivery format with [draft](../draft/SKILL.md), cloud/AI TCO with [finops](../finops/SKILL.md), and audit via `fmind-review-proposal` ([subagent](../subagent/SKILL.md)).

## Workflow

1. **Classify commitment tier**: internal steering memo, commercial pitch, T&M capacity plan, or fixed-price SOW (skip formal WBS ceremony on 1–2 day spikes). Never invent client metrics, logos, case studies, or baselines; use explicit placeholders when data is missing.
1. **Frame decision & options**: open paragraph one with recommendation, cost/value headline, and target pain. Show 2–3 credible options including **Do nothing** (or bounded pilot), separating one-time migration from run-rate TCO, and mark one `(Recommended)`. Address top 2–3 deal-breakers upfront (data residency, IAM/compliance, lock-in, Day-2 ownership).
1. **Build WBS & `P10`/`P50`/`P90` effort model**:
   - Keep leaf packages `<= 10` ideal person-days and budget `>= 20%` of SOW delivery for non-coding/AI overhead (access/discovery, CI/IaC, security/privacy, eval curation, tests, handover, UAT, rollback).
   - Match percentile to tier (`>= P80` fixed-price; `P50` + contingency for T&M), cap utilization at `<= 75%`–`80%`, and place external waits (access, InfoSec, legal, procurement) on the critical path.
1. **Lock scope boundaries & CTA**: state explicit `In Scope`, `Out of Scope`, measurable acceptance criteria, dated client prerequisites (`T+N` access/SMEs), change-control triggers, burn-aligned payment milestones, and **one** dated next step matched to buyer authority.
1. **Verify math deterministically in Python**: write a short `python3` script using `decimal.Decimal` (`ROUND_HALF_UP` to `0.01` per commercial line so `subtotal - discount + contingency == grand_total` reconciles exactly) checking leaf caps, overhead share, phase subtotals, rate conversions, taxes, and prose headlines. Rerun after any scope, rate, or discount edit before exporting.
1. **Review adversarially**: run `vale` per [humanize](../humanize/SKILL.md#pre-send-gate) and fan out `fmind-review-proposal`, `fmind-review-human`, `fmind-review-factcheck`, and `fmind-review-finops` (when cloud/AI TCO appears).

## Gotchas

- **Fixed-price R&D trap**: never commit fixed-price on unverified data, legacy schema archaeology, or uncurated AI evals; gate delivery with a time-boxed discovery/pilot phase.
- **Headcount division fallacy**: dividing person-days by headcount ignores review slack, serialization, PTO, and client approvals; derive calendar weeks from the critical path.

## Documentation

- [NASA Systems Engineering Handbook](https://www.nasa.gov/reference/systems-engineering-handbook/)
- Companion skills: [humanize](../humanize/SKILL.md), [draft](../draft/SKILL.md), [finops](../finops/SKILL.md), [extract](../extract/SKILL.md), [adr-rfc](../docs/references/adr-rfc.md), [subagent](../subagent/SKILL.md).
