---
name: terms-review
description: "Review ToS, licenses, and DPAs against an intended use."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/terms-review
  created: "2026-09-15"
  updated: "2026-11-10"
---

# Terms Review

Assess whether an intended use of a product, service, or artifact fits its governing terms and user constraints. Deliver a dated, clause-backed decision—never treat silence as permission or present the review as legal advice. [project-license](../project-scaffolding/references/project-license/GUIDE.md) owns choosing a repository license.

## Workflow

1. **Define context**: product, provider, exact version/artifact, plan, contracting entity, jurisdictions, activities, audience, scale, and data flows; ask only decision-changing unknowns while gathering sources, and record assumptions.
1. **Set criteria**: turn user, policy, and requested regulatory constraints into checkable requirements, keeping contractual grants, legal duties, and operational proof distinct (ignore badges and marketing claims).
1. **Collect primary texts**: inspect the signed agreement if any and all incorporated documents—ToS, EULA/license, order form, service terms, AUP, privacy notice, DPA, subprocessors, and exact-release model/dataset/dependency licenses—recording title, URL or private ID, effective date, retrieval date, scope, and clause IDs.
1. **Resolve precedence**: separate consumer, business, API, free, paid, trial, and preview terms; check incorporation, precedence, amendments, renewal, and notice rules rather than assuming the latest public page governs an existing contract. Mark unavailable or irreconcilable texts unresolved; never reconstruct clauses from snippets or memory.
1. **Map clauses**: walk relevant [assessment](references/assessment.md) items, recording clause, brief quote or paraphrase, effect, operational proof, and remaining actions while distinguishing literal text, interpretation, and unverified claims.
1. **Decide and report**: follow the [assessment](references/assessment.md) output contract, ranking blockers first, assigning owner/action/verification to each condition, noting plan or config changes that resolve conflicts, and drafting exact counsel/vendor questions for consequential ambiguity.
1. **Audit the verdict**: confirm every material requirement has clause evidence or an explicit gap (blockers or missing facts forbid `Supported`), ground jurisdiction claims in official statutes/regulator guidance, and list re-review triggers (changed terms, plan, version, data, jurisdiction, distribution, or use).

## Boundaries

- **Analysis only**: accepting terms, buying, changing settings, uploading data, or contacting vendors requires separate approval; draft outreach locally.
- **Protect private context**: keep contract text and business details out of public searches, shared reports, and repo fixtures; search using public product names only.

## Companion skills

- [code-security](../code-security/references/code-review/GUIDE.md): technical controls and dependency licenses/vulns.
- [full-review](../full-review/SKILL.md#proof-ladder): operational launch proof beyond contractual permission.
