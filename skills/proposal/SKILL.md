---
name: proposal
description: "Draft commercial proposals, ROI/steering memos, SOWs, RFP pricing, roadmaps, and WBS/P10-P90 effort estimates with verified math."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/proposal
  created: "2026-11-21"
  updated: "2026-11-25"
---

# Proposals, SOWs & Effort Sizing

Deliver executive-ready proposals, SOWs, RFP pricing tables, steering memos, roadmaps, and effort estimates without optimism bias, missing overhead, or arithmetic drift. Own commercial framing, WBS sizing, and pricing reconciliation here; delegate prose/visual craft to [humanize](../humanize/SKILL.md), technical system design to [adr-rfc](../docs/references/adr-rfc.md), channel plumbing to [draft](../draft/SKILL.md), and cloud/AI infra TCO to [finops](../finops/SKILL.md).

## Workflow

1. **Pick the lightest tier that fits**:
   - **Default — 1-page executive brief or early pitch (`~250–400`w)**: open with the recommendation, rough cost/value headline, and target pain in plain language; compare `2`–`3` options (including **Do nothing** or a bounded pilot), name the top `1`–`2` risks, put shared date/pricing assumptions in one bottom note, and close with **one** dated next step (park detailed breakdowns in an optional `Annex`).
   - **Opt-in — Formal SOW, RFP, or binding fixed-price quote** (only when explicitly requested or committing contractual scope/pricing): run steps 2–5 below. Never invent client metrics, logos, case studies, or baselines; mark missing inputs as explicit placeholders.
1. **Frame options & deal-breakers (formal tier)**: separate one-time build/migration from run-rate TCO, mark one option `(Recommended)`, and address top `2`–`3` objections upfront (data residency, IAM/compliance, vendor lock-in, Day-2 ownership).
1. **Build WBS & right-skewed `P10`/`P50`/`P90` model (formal tier)**:
   - Keep leaf packages `<= 10` ideal person-days and budget `>= 20%` of SOW delivery for non-coding overhead (access/discovery, CI/IaC, security/privacy, tests, handover, UAT, rollback); on AI/legacy migrations, explicitly size eval curation, retrieval/guardrail loops, and data cleaning.
   - Use right-skewed ranges (`0 < P10 < P50 < P90`, `(P90 - P50) >= (P50 - P10)`) matched to tier (`>= P80` fixed-price; `P50–P70` + contingency for T&M). Cap utilization at `<= 75%`–`80%`, compute FTEs net of PTO/holidays (`working_days_per_year`), and put external waits (access, InfoSec, legal, procurement) on the critical path.
1. **Lock scope boundaries & CTA (formal tier)**: state `In Scope`, `Out of Scope`, measurable acceptance criteria, dated client prerequisites (`T+N` access/SMEs), change-control triggers, explicit currency and tax labels (`HT` / excl. tax vs incl. tax), burn-aligned payment milestones, and **one** dated next step matched to buyer authority.
1. **Verify math deterministically (whenever tables/estimates exist)**: run [`check_estimate.py`](scripts/check_estimate.py) (exact `Decimal` `ROUND_HALF_UP` reconciliation, leaf caps, skew, `>= 20%` overhead, utilization, linear vs RSS `P10`/`P90` bounds) and rerun after any scope, rate, or discount edit before exporting:

   ```bash
   python3 -I ~/.agents/skills/proposal/scripts/check_estimate.py estimate.json --json
   ```

1. **Review adversarially**: run `vale` per [humanize](../humanize/SKILL.md#pre-send-gate) and fan out `1`–`2` targeted reviewers (`fmind-review-human` + `fmind-review-proposal`; add `fmind-review-factcheck`, `fmind-review-finops`, or `fmind-review-compliance` only when external claims, cloud/AI TCO, or legal/GDPR clauses are in scope) via [subagent](../subagent/SKILL.md).

## Gotchas & Boundaries

- **Commercial approval & customer isolation**: never send, publish, or commit pricing, SOW terms, or timelines externally without explicit user approval. Keep client names, rates, and figures strictly inside the customer's repo or approved workspace (synthetic fixtures only in reusable templates).
- **Fixed-price R&D trap**: never commit fixed-price on unverified data, legacy schema archaeology, or uncurated AI evals; gate delivery with a time-boxed discovery/pilot phase.
- **Headcount division fallacy**: dividing person-days by headcount ignores review slack, serialization, PTO, and client approvals; derive calendar weeks from the critical path.

## Documentation

- [NASA Systems Engineering Handbook](https://www.nasa.gov/reference/systems-engineering-handbook/)
- Companion skills: [humanize](../humanize/SKILL.md), [draft](../draft/SKILL.md), [finops](../finops/SKILL.md), [extract](../extract/SKILL.md), [adr-rfc](../docs/references/adr-rfc.md), [subagent](../subagent/SKILL.md).
