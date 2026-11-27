---
name: adr-rfc
description: "Write lightweight ADRs and architecture RFCs with scale bounds, alternatives, failure modes, and rollback."
---

# Architecture Decision Records & RFCs

Write concise ADRs (`docs/decisions/NNNN-<slug>.md`, MADR style) for single irreversible or cross-cutting choices, and full RFCs only for multi-service, stateful, or high-risk designs. Pair prose with [humanize](../../humanize/SKILL.md) (select the 2–3 trade-offs that drive the choice in plain language; park extra detail in an optional `Annex`) and diagrams with [diagrams-as-code](../../diagrams-as-code/SKILL.md).

## Default Lightweight ADR (`~1` Page)

Use by default unless asked for a full RFC or introducing new distributed/multi-tenant boundaries:

1. **Trigger, Decision & Non-Goals**: concrete problem, chosen design, and what stays out of scope.
1. **Options (`2`–`3`) & Key Trade-Off**: compare against **Do nothing** (or a simpler single-process baseline) on the 2–3 dimensions that matter most.
1. **Top Risk, Rollback & What Would Reverse It**: main failure mode, how to undo safely, and the clear threshold that reverses the choice.

## Full Architecture RFC (Opt-In)

Add these sections only for distributed, stateful, or high-risk platform designs:

1. **Scale Envelope & Trust Boundaries**: tenancy/data-residency bounds and quantitative targets (users, QPS, dataset size, latency SLO, RPO/RTO).
1. **Bounded Contexts**: acyclic module/service seams, narrow contracts, zero shared mutable databases; prefer boring primitives and modular monoliths unless scale proves a split pays off.
1. **Failure Modes & Graceful Degradation**: partial dependency hangs/rate limits, blast-radius bulkheads, dual-write consistency (outbox/idempotency), degrade-vs-fail-closed behavior.
1. **Expand-Contract Migration & Minute-Scale Rollback**: N-1 compatibility, pre-migration snapshots, verification gates, and an exact rollback procedure before mutating state.
1. **Sources & Review**: cite primary benchmarks/docs with dates; audit substantive ADRs/RFCs with `1`–`2` targeted reviewers (`fmind-review-architecture` + `fmind-review-human`; add `fmind-review-security` or `fmind-review-finops` only when trust boundaries or infra spend are in scope; [subagent](../../subagent/SKILL.md)).

## Gotchas

- **Avoid premature microservices or custom queues**: justify every new runtime component against its Day-2 operational tax.
- **State what would reverse the decision**: name the exact threshold (load, cost, compliance, or vendor change) in plain words instead of calling it a "flip condition".
- **Model-check distributed designs before coding**: for multi-step sagas, consensus, or concurrency/locking protocols, specify and check invariants in **Quint** (TLA+) during the RFC phase; keep implementation-level checks on Python's [4-tier verification ladder](../../python/references/testing/references/property-tests.md#verification-ladder) and skip Lean 4 unless building crypto primitives or prover-compiled policy kernels.

## Documentation

- [MADR (Markdown Architectural Decision Records)](https://adr.github.io/madr/) · [C4 Model](https://c4model.com/) · [Quint](https://quint.sh/)
- Companions: [repository](repository/GUIDE.md), [humanize](../../humanize/SKILL.md), [diagrams-as-code](../../diagrams-as-code/SKILL.md), [finops](../../finops/SKILL.md), [proposal](../../proposal/SKILL.md).
