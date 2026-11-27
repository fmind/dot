---
name: spec-prd
description: "Write evidence-backed PRDs and feature specs with falsifiable metrics, non-goals, edge states, and acceptance criteria."
---

# Product Specs & PRDs

Author concise feature briefs and PRDs that prove user pain, lock scope boundaries, and define testable acceptance criteria before writing code. Pair prose with [humanize](../../humanize/SKILL.md) (select the 2–3 points that drive alignment in plain language; park extra detail in an optional `Annex`) and technical design with [adr-rfc](adr-rfc.md).

## Default Feature Brief (`~1` Page)

Use by default for features and multi-PR changes (skip formal specs entirely on 1–2 day bug fixes):

1. **Problem & Evidence**: target user, concrete workflow pain, current workaround, and observed frequency/severity in plain language (for AI/LLM features, state why simpler code or UX fixes fall short).
1. **First Slice & Out of Scope**: one testable v1 slice, explicit `Out of Scope` items, and any upstream prerequisites by name.
1. **How We'll Measure It & Pass/Fail Checks**: one baseline-anchored outcome metric plus concrete pass/fail checks (replace vague terms like _"fast"_ or _"intuitive"_).

## Full PRD (Opt-In)

Add these sections only for new products, cross-team initiatives, or when formal depth is requested:

1. **Guardrails & Kill Criteria**: pair target gains with counter-metrics (error rate, latency, support load, user trust, unit cost) and an explicit stop or pivot threshold.
1. **Edge-State Matrix & Adoption Friction**: first-run onboarding, empty/zero-data, permission/role boundaries, partial failure/recovery, and migration impact on existing workflows.
1. **Open Questions & Decision Ownership**: risky assumptions (data, legal/privacy consent, vendor quotas) with a single named owner and deadline per unresolved `TBD`.

## Handoff & Review

- **Handoff**: route architecture boundaries, scale envelopes, and rollback plans to [adr-rfc](adr-rfc.md); track scoped slices and prerequisites in [github/issues](../../github/references/issues/GUIDE.md); route commercial pricing/WBS to [proposal](../../proposal/SKILL.md).
- **Review adversarially**: run `1`–`2` targeted reviewers (`fmind-review-spec` + `fmind-review-human`; add `fmind-review-completeness` on multi-surface PRDs; [subagent](../../subagent/SKILL.md)).

## Documentation

- Companions: [adr-rfc](adr-rfc.md), [github/issues](../../github/references/issues/GUIDE.md), [humanize](../../humanize/SKILL.md), [proposal](../../proposal/SKILL.md), [subagent](../../subagent/SKILL.md).
