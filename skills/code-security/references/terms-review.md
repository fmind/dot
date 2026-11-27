---
name: terms-review
description: "Review ToS, GDPR/EU AI Act, SPDX licenses, and DPAs for intended use."
---

# Terms, Privacy & License Review

Assess whether an intended use of a product, model, dataset, or library fits its governing terms and regulatory constraints. Deliver a dated, clause-backed decision—never treat silence as permission or present the review as legal advice. [project-license](../../github/references/project-license/GUIDE.md) owns choosing a repository license.

## Workflow

1. **Define context**: record product, exact version/artifact, plan/tier, entities, jurisdictions, scale, data flows, and policy/regulatory requirements (ignore badges/marketing).
1. **Collect primary texts**: inspect signed agreements and incorporated docs (ToS, SPDX license, DPA, subprocessors, model/dataset cards) with URL/ID and effective date; resolve consumer/API/enterprise precedence and mark missing texts `Unresolved`.
1. **Audit clauses**: evaluate commercial/API/scraping/export rights plus the GDPR, EU AI Act, and SPDX checklists below alongside technical verification.
1. **Review adversarially & deliver**: run `fmind-review-compliance` and `fmind-review-factcheck` ([subagent](../../subagent/SKILL.md)). Report dated verdict (`Supported`, `Conditional`, `Not supported`, `Unresolved`), clause evidence table (`Requirement | Document & Clause | Finding | Status | Action`), ranked blockers, counsel/vendor questions, re-review triggers, and closing `Sources` with effective dates.

## GDPR, DPIA & Data Residency Checklist

- **Role & basis**: identify Controller vs Processor (Art. 28), Art. 6 lawful basis, and Art. 9 special-category restrictions.
- **DPA & subprocessors**: verify signed DPA for the exact tier, current subprocessor list, change-notice window, and objection right.
- **Residency & transfers**: verify EU/EEA storage _and_ inference/logging residency, or valid transfer tool (adequacy or EU SCCs + TIA).
- **ZDR & training opt-out**: confirm contractual Zero Data Retention (ZDR) and no-training on prompts and abuse logs, plus matching runtime endpoint/flags.
- **DPIA, breach & deletion**: screen Art. 35 DPIA triggers (profiling, Art. 9, monitoring), `≤72h` breach SLA (Art. 33), and deletion timeline.

## EU AI Act (2024/1689) Risk Tiering

| Tier                      | Trigger examples                                                                  | Obligations & verdict                                                        |
| ------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Prohibited (Art. 5)**   | Social scoring, manipulation, facial scraping, workplace/school emotion inference | `Not supported` — block                                                      |
| **High-Risk (Annex III)** | Biometrics, critical infra, HR, credit/scoring, public services                   | Conformity, QMS, data governance, logs, human oversight, FRIA (Art. 27)      |
| **Limited (Art. 50)**     | Chatbots, synthetic media, biometric/emotion categorization                       | User disclosure + machine-readable AI marking                                |
| **Minimal**               | Spam filters, autocomplete, internal search                                       | Voluntary codes; GDPR/IP still apply                                         |
| **GPAI (Art. 53/55)**     | Foundation models (systemic risk >$10^{25}$ FLOPs)                                | Docs, copyright policy, training summary; check fine-tuning provider trigger |

## SPDX Code, Weight & Dataset Matrix

| Class                       | Examples                                                   | Key obligations & risks                                                               |
| --------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Permissive**              | `MIT`, `Apache-2.0`, `BSD-2/3-Clause`                      | Keep notices (`Apache-2.0`: patent grant + `NOTICE`)                                  |
| **Weak copyleft**           | `MPL-2.0`, `LGPL-2.1/3.0`                                  | Disclose file (`MPL`) or library (`LGPL`) edits; relinking rules                      |
| **Strong/network copyleft** | `GPL-2.0/3.0`, `AGPL-3.0`                                  | Derivative / SaaS (`AGPL`) source release; flag in proprietary code                   |
| **Source-available**        | `BSL-1.1`, `SSPL-1.0`, `Elastic-2.0`                       | Not OSI; check hosted-service bans and change dates                                   |
| **Weights & datasets**      | Llama/Gemma/Rail; `CC-BY/SA/NC-4.0`, `CDLA-Permissive-2.0` | Check MAU caps, AUP, synthetic-output training bans, `SA` taint, `NC` commercial bans |

## Boundaries & Documentation

- **Analysis only & privacy**: accepting terms, buying, or contacting vendors needs separate approval; keep contract/client details out of public searches and shared fixtures.
- [SPDX](https://spdx.org/licenses/) · [OSI](https://opensource.org/licenses) · [GDPR (2016/679)](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) · [EU AI Act (2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) · Companions: [project-license](../../github/references/project-license/GUIDE.md), [code-security](code-review/GUIDE.md), [full-review](../../full-review/SKILL.md#proof-ladder).
