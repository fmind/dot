---
name: code-security
description: "Review code security, threat-model designs, vet third-party skills, and scan with Gitleaks and Trivy."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/code-security
  created: "2026-07-04"
  updated: "2026-10-29"
---

# Code Security

Investigate and fix security defects with evidence. Choose code review, threat modeling, third-party skill review, secret scanning, or vulnerability scanning from the task; findings need verification and scanners do not replace reasoning. The name deliberately avoids `security-review`, which Claude Code and Copilot CLI ship as a built-in command.

## Workflow

Read only the matching guide and its required resources.

## Task guides

<!-- guides:start -->

- [code-review](references/code-review/GUIDE.md): Assess code and repository security; verify findings and repairs.
- [gitleaks](references/gitleaks.md): Scan the working tree and history for secrets; handle confirmed exposure.
- [skill-security-review](references/skill-security-review/GUIDE.md): Review third-party skills and agent extensions for supply-chain risk.
- [scanners](references/skill-security-review/references/scanners.md): Run gitleaks and Trivy on a candidate with trusted configuration it cannot suppress.
- [threat-model](references/threat-model.md): Model attack paths, trust boundaries, abuse cases, and controls.
- [trivy](references/trivy/GUIDE.md): Scan dependencies, IaC, images, and licenses; generate SBOMs.

<!-- guides:end -->
