---
name: terms-review
description: Review product or service terms, licenses, and conditions for a specific use context. Use when assessing permitted use, contractual obligations, or compliance gaps before adoption.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/terms-review
  created: "2026-09-15"
  updated: "2026-09-15"
---

# Terms Review

Assess whether a defined use of a product or service fits its applicable terms and the user's requirements. Produce a dated, clause-backed decision with conditions and gaps; never turn missing evidence into permission or present a terms review as legal certification. Choosing a license for the user's own repository belongs to [project-license](../project-license/SKILL.md).

## Workflow

1. **Define the context**: identify the product, provider, version, plan, contracting entity, relevant jurisdictions, and intended activities. Establish personal, educational, research, or commercial use; internal use versus customer access, redistribution, resale, or embedding; users and scale; data categories, ownership, and destinations. Ask only for missing facts that could change the decision; continue source gathering independently. Record assumptions explicitly.
1. **Set acceptance criteria**: turn the user's constraints into checkable requirements, including internal policy and applicable regulatory obligations when requested. Separate contractual permission, legal requirements, and operational evidence. Do not infer compliance from a certification badge or a vendor's marketing claim.
1. **Collect authoritative evidence**: browse current official sources and inspect the applicable signed agreement when available. Follow incorporated documents: terms of service, license/EULA, order form, service-specific terms, acceptable-use policy, privacy notice, data processing agreement (DPA), subprocessors, and relevant model, dataset, or dependency licenses. Record each document's title, URL or private reference, version/effective date, retrieval date, scope, and clause identifiers. Verify the license of the exact release or artifact being used.
1. **Resolve applicability**: distinguish consumer, business, API, free, paid, trial, and preview terms. Check incorporation, stated precedence, amendments, renewal, and change-notice provisions; establish which version governs the planned use instead of assuming the latest public page controls an existing contract. If an agreement is unavailable or documents conflict without clear precedence, mark the affected conclusions unresolved.
1. **Map requirements to clauses**: use the checklist below only where relevant. For each requirement, record the applicable clause, a short quotation or faithful paraphrase, its practical effect, evidence of fulfillment, and any remaining action. Clearly label direct text, interpretation, and unverified claims. Silence is not a grant; a proposed setting or process is not proof that an obligation is met.
1. **Decide and report**: lead with the scoped verdict using the output contract below. Rank blockers before lesser risks. Make conditional use concrete with an owner, action, and verification criterion for each unmet obligation; identify changes of plan, configuration, or use that could resolve a conflict. For consequential legal ambiguity, prepare the precise question and clauses for qualified counsel or the authorized contract owner.
1. **Verify the conclusion**: confirm that every material requirement has evidence or an explicit gap, links support the claims, and dates and product scope match. A blocker or material unknown prevents a supported verdict. State when to re-review: changed terms, plan, version, data, jurisdiction, distribution, or intended use.

## Review checklist

- **Rights and restrictions**: commercial use, seats and affiliates, automation/API access, scraping, benchmarking and publication, security testing, reverse engineering, prohibited sectors or activities, geography, and export restrictions.
- **Software, models, and content**: copying, modification, redistribution, network use, attribution/notices, source disclosure, copyleft compatibility, patents, trademarks, and separate rights for code, weights, datasets, inputs, and outputs. Read the actual license; a repository label or scanner result is only a discovery aid.
- **Data and AI use**: confidentiality, provider access, training and improvement rights, opt-outs and their scope, retention/deletion including logs and backups, residency/transfers, subprocessors, personal or regulated data restrictions, and required agreements. Verify operational controls separately from contractual promises.
- **Commercial and exit conditions**: metering, overages, quotas, renewals/cancellation, price changes, suspension/termination, data export/deletion, survival clauses, warranties, liability limits, indemnities, audit rights, governing law, and dispute terms against the user's acceptance criteria.

## Output contract

Keep a simple review short; expand the evidence matrix when several documents or obligations interact.

- **Verdict and scope**: `Supported`, `Conditional`, `Not supported`, or `Unresolved`, as of a stated date, for the exact product/plan/version and intended use. `Supported` means the reviewed evidence supports the stated requirements; it is not blanket legal approval. `Conditional` requires known, achievable obligations; missing material evidence is `Unresolved`. Explicit conflicts are `Not supported`; list unknowns separately when both exist.
- **Context and assumptions**: relevant entities, jurisdictions, data, activities, requirements, exclusions, and missing facts.
- **Evidence matrix**: requirement | document and clause | finding and interpretation | status | action and verification. Link public sources at the claim; use non-sensitive labels for private contracts in shared reports.
- **Next steps**: prioritized blockers, conditions, responsible owners, precise open questions, and re-review triggers. Include a compact source register with document dates and access dates.

## Boundaries

- Review authority permits reading and analysis. Accepting terms, purchasing, changing account settings, uploading data, and contacting providers require separate authorization; draft questions locally first.
- Use current official legislation or regulator guidance for jurisdiction-specific legal claims; if unavailable, state the gap. A terms review alone cannot establish regulatory compliance, enforceability, or the user's actual operational compliance.
- Inaccessible, undated, archived, or supplied excerpts support only a bounded assessment. Identify missing incorporated documents and do not reconstruct their content from search snippets or memory.
- Keep private agreement text and business context out of public searches, reports, and repository fixtures; retrieve public documents using product names and public identifiers only.

## Companion skills

- [project-license](../project-license/SKILL.md): select and write the user's repository license.
- [secure](../secure/SKILL.md): verify technical security controls and dependency findings.
- [production-readiness](../production-readiness/SKILL.md): assess operational launch evidence beyond contractual permission.
