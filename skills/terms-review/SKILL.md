---
name: terms-review
description: "Review ToS, licenses, and DPAs against an intended use."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/terms-review
  created: "2026-09-15"
  updated: "2026-11-14"
---

# Terms Review

Assess whether an intended use of a product, service, or artifact fits its governing terms and user constraints. Deliver a dated, clause-backed decision—never treat silence as permission or present the review as legal advice. [project-license](../project-scaffolding/references/project-license/GUIDE.md) owns choosing a repository license.

## Workflow

1. **Define context & criteria**: record product, exact version/artifact, plan, entities, jurisdictions, scale, data flows, and checkable policy/regulatory requirements (ignore badges and marketing).
1. **Collect & order primary texts**: inspect signed agreements and incorporated docs (ToS, EULA/license, DPA, subprocessors, release model/dataset licenses) with URL/ID and effective date; resolve consumer/API/enterprise precedence and mark unavailable texts `Unresolved` instead of reconstructing from memory.
1. **Audit clauses**: cover commercial/API/scraping/benchmark/export rights; code/weights/dataset/output licenses and copyleft compatibility (read raw license text); and confidentiality, AI training/opt-out, retention, residency, and DPA/BAA obligations alongside technical verification.
1. **Deliver the report**: state dated verdict (`Supported`, `Conditional`, `Not supported`, or `Unresolved`), context/assumptions, evidence matrix (requirement | document & clause | finding | status | action), ranked blockers, counsel/vendor questions, re-review triggers, and dated sources.

## Boundaries

- **Analysis only**: accepting terms, buying, changing settings, uploading data, or contacting vendors requires separate approval; draft outreach locally.
- **Protect private context**: keep contract text and business details out of public searches, shared reports, and repo fixtures; search using public product names only.

## Companion skills

- [code-security](../code-security/references/code-review/GUIDE.md): technical controls and dependency licenses/vulns.
- [full-review](../full-review/SKILL.md#proof-ladder): operational launch proof beyond contractual permission.
