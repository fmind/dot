---
name: adr-rfc
description: "Write lightweight ADRs and architecture RFCs with scale bounds, alternatives, failure modes, and rollback."
---

# Architecture Decision Records & RFCs

Write concise ADRs (`docs/decisions/NNNN-<slug>.md`, MADR style) for single irreversible or cross-cutting choices, and short RFCs for multi-component designs. Match ceremony to scale (local CLI vs single-node service vs distributed multi-tenant platform) and pair prose with [humanize](../../humanize/SKILL.md) and diagrams with [diagrams-as-code](../../diagrams-as-code/SKILL.md).

## Required Sections

1. **Context, Goals & Non-Goals**: state the concrete trigger, explicit non-goals, tenancy/data-residency bounds, trust boundaries, and quantitative scale envelope (users, QPS, payload/dataset size, latency SLO, RPO/RTO).
1. **Decision & Bounded Contexts**: name the chosen architecture and component seams (acyclic module/service boundaries, narrow contracts, zero shared mutable databases across independent services). Prefer boring, proven primitives and modular monoliths unless the scale envelope proves distributed splits pay off.
1. **Alternatives Considered (`>= 2`)**: compare the chosen option against **Do nothing** (or a simpler single-process/relational baseline) and at least one serious peer across complexity, latency, TCO, Day-2 operations, and exit/reversal cost. State the exact constraint each rejected option fails.
1. **Failure Modes & Graceful Degradation**: trace partial dependency failures, hangs, rate limits, blast-radius bulkheads, and dual-write consistency (outbox or idempotent sagas). State what degrades cleanly vs fails closed.
1. **Migration & Minute-Scale Rollback**: specify expand-contract steps for schema/wire changes, N-1 compatibility, pre-migration snapshots, verification gates, and an exact rollback procedure before mutating state.
1. **Sources & Review**: cite primary benchmarks, docs, and constraints with dates/versions; audit substantive ADRs/RFCs via `fmind-review-architecture`, `fmind-review-security`, and `fmind-review-finops` ([subagent](../../subagent/SKILL.md)).

## Gotchas

- **Avoid premature microservices or custom queues**: justify every new runtime component against its Day-2 operational tax.
- **Never skip flip conditions**: state the exact threshold (load, cost, compliance, or vendor change) that would reverse the decision.
- **Model-check distributed designs before coding**: for multi-step sagas, consensus, or concurrency/locking protocols, specify and check invariants in **Quint** (TLA+) during the RFC phase; keep implementation-level checks on Python's [4-tier verification ladder](../../python/references/testing/references/property-tests.md#verification-ladder) and skip Lean 4 unless building crypto primitives or prover-compiled policy kernels.

## Documentation

- [MADR (Markdown Architectural Decision Records)](https://adr.github.io/madr/) · [C4 Model](https://c4model.com/) · [Quint](https://quint.sh/)
- Companions: [repository](repository/GUIDE.md), [humanize](../../humanize/SKILL.md), [diagrams-as-code](../../diagrams-as-code/SKILL.md), [finops](../../finops/SKILL.md), [proposal](../../proposal/SKILL.md).
