---
name: code-security
description: "Review security, terms/licenses, threat-model, vet skills, PyRIT red-team, Betterleaks, Opengrep, Trivy, SonarQube."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/code-security
  created: "2026-07-04"
  updated: "2026-11-24"
---

# Code Security

Investigate and fix security defects with verified evidence—scanners inform reasoning, never replace it. Named `code-security` to avoid colliding with Claude/Copilot `security-review`.

## Workflow

Load the matching guide(s) below for every active surface and pair non-trivial changes with clean-context `fmind-review-security` review ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [ai-red-team](references/ai-red-team/GUIDE.md): Red-team AI apps/agents via PyRIT: injection, tool misuse, authority.
- [betterleaks](references/betterleaks.md): Scan the working tree and history for secrets; handle confirmed exposure.
- [code-review](references/code-review/GUIDE.md): Assess code and repository security; verify findings and repairs.
- [opengrep](references/opengrep.md): Run local intrafile and cross-file taint SAST scans with opengrep.
- [skill-security-review](references/skill-security-review/GUIDE.md): Review third-party skills and agent extensions for supply-chain risk.
- [sonarqube](references/sonarqube.md): SonarQube quality gates, issues, local scans, and server AI gates via sonar.
- [terms-review](references/terms-review.md): Review ToS, licenses, DPAs for intended use.
- [threat-model](references/threat-model.md): Model attack paths, trust boundaries, abuse cases, and controls.
- [trivy](references/trivy/GUIDE.md): Scan dependencies, IaC, images, and licenses; generate SBOMs.

<!-- guides:end -->

## Documentation

- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) · [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [MITRE ATLAS](https://atlas.mitre.org/)
- Companions: [full-review](../full-review/SKILL.md), [github](../github/SKILL.md), [containers](../containers/SKILL.md), [cloud-run](../gcloud/references/cloud-run/GUIDE.md).
