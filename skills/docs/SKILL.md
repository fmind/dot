---
name: docs
description: "Sync README, AGENTS.md, repo docs; write standalone PRDs and ADRs/RFCs; build Zensical sites, migrate MkDocs/Hugo."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docs
  created: "2026-11-21"
  updated: "2026-11-27"
---

# Documentation

Keep human and agent repository docs aligned with live code, author standalone pre-build PRDs and ADRs/RFCs, and build Zensical documentation, course, and API sites (living repo `openspec/` specs and changes live in [openspec](../openspec/SKILL.md); operational runbooks and postmortems live in [sre](../sre/SKILL.md)). Apply [humanize](../humanize/SKILL.md) for prose and visuals (1-page brief default; escalate to formal depth only when asked), and audit substantive rewrites with `1`–`2` targeted reviewers (`fmind-review-docs`, `fmind-review-human`, `fmind-review-spec`, `fmind-review-architecture`, `fmind-review-factcheck`, or `fmind-review-frontend` per [subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [adr-rfc](references/adr-rfc.md): Write lightweight ADRs and architecture RFCs with scale bounds, alternatives, failure modes, and rollback.
- [repository](references/repository/GUIDE.md): Sync README, AGENTS.md, repo docs with verified behavior.
- [site](references/site/GUIDE.md): Build Zensical docs, courses, and API sites; deploy Pages or migrate MkDocs/Hugo.
- [spec-prd](references/spec-prd.md): Write evidence-backed PRDs and feature specs with falsifiable metrics, non-goals, edge states, and acceptance criteria.

<!-- guides:end -->

## Documentation

- Companions: [openspec](../openspec/SKILL.md), [sre](../sre/SKILL.md), [humanize](../humanize/SKILL.md), [project-setup](../agent-harnesses/references/project-setup.md), [diagrams-as-code](../diagrams-as-code/SKILL.md), [mise](../mise/SKILL.md).
