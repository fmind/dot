---
name: docs
description: "Sync README, AGENTS.md, repo docs; write ADRs/RFCs, runbooks, postmortems; build Zensical sites, migrate MkDocs/Hugo."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/docs
  created: "2026-11-21"
  updated: "2026-11-22"
---

# Documentation

Keep human and agent repository docs aligned with live code, and build Zensical documentation, course, and API sites. Apply [humanize](../humanize/SKILL.md) for prose and visuals, and audit substantive rewrites with `fmind-review-docs`, `fmind-review-factcheck`, or `fmind-review-frontend` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [adr-rfc](references/adr-rfc.md): Write lightweight ADRs and architecture RFCs with scale bounds, alternatives, failure modes, and rollback.
- [repository](references/repository/GUIDE.md): Sync README, AGENTS.md, repo docs with verified behavior.
- [runbook-postmortem](references/runbook-postmortem.md): Write Day-2 operational runbooks, safe cutover plans, SLO alerts, and blameless incident postmortems.
- [site](references/site/GUIDE.md): Build Zensical docs, courses, and API sites; deploy Pages or migrate MkDocs/Hugo.

<!-- guides:end -->

## Documentation

- Companions: [humanize](../humanize/SKILL.md), [project-setup](../agent-harnesses/references/project-setup.md), [diagrams-as-code](../diagrams-as-code/SKILL.md), [mise](../mise/SKILL.md).
