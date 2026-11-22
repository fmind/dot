---
name: terms-review
description: Review ToS, licenses, DPAs for intended use.
---

# Terms Review

Assess whether an intended use of a product, service, or artifact fits its governing terms and user constraints. Deliver a dated, clause-backed decision—never treat silence as permission or present the review as legal advice. [project-license](../../github/references/project-license/GUIDE.md) owns choosing a repository license.

## Workflow

1. **Define context & criteria**: record product, exact version/artifact, plan, entities, jurisdictions, scale, data flows, and checkable policy/regulatory requirements (ignore badges and marketing).
1. **Collect & order primary texts**: inspect signed agreements and incorporated docs (ToS, EULA/license, DPA, subprocessors, release model/dataset licenses) with URL/ID and effective date; resolve consumer/API/enterprise precedence and mark unavailable texts `Unresolved` instead of reconstructing from memory.
1. **Audit clauses**: cover commercial/API/scraping/benchmark/export rights; code/weights/dataset/output licenses and copyleft compatibility (read raw license text); and confidentiality, AI training/opt-out, retention, residency, and DPA/BAA obligations alongside technical verification.
1. **Audit adversarially & deliver the report**: run `fmind-review-compliance` and `fmind-review-factcheck` ([subagent](../../subagent/SKILL.md)) on non-trivial reviews. State dated verdict (`Supported`, `Conditional`, `Not supported`, or `Unresolved`), context/assumptions, clause evidence (compact table or scannable bullets: requirement, document & clause, finding, status, action), ranked blockers, counsel/vendor questions, re-review triggers, and a closing `Sources` section naming each primary text, what it grounds, and its effective date.

## Boundaries

- **Analysis only**: accepting terms, buying, changing settings, uploading data, or contacting vendors requires separate approval; draft outreach locally.
- **Protect private context**: keep contract text and business details out of public searches, shared reports, and repo fixtures; search using public product names only.

## Documentation

- [SPDX License List](https://spdx.org/licenses/) · [OSI Licenses](https://opensource.org/licenses) · [GDPR (2016/679)](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) · [EU AI Act (2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)
- Companions: [project-license](../../github/references/project-license/GUIDE.md), [code-security](code-review/GUIDE.md), [full-review](../../full-review/SKILL.md#proof-ladder).
