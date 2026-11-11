---
name: code-security
description: "Review code security, threat-model designs, vet skills, red-team AI with PyRIT, and scan with Betterleaks, Trivy, and SonarQube."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/code-security
  created: "2026-07-04"
  updated: "2026-11-11"
---

# Code Security

Investigate and fix security defects with verified evidence—scanners inform reasoning, never replace it. Named `code-security` to avoid colliding with Claude Code and Copilot CLI's built-in `security-review` command.

## Workflow

Read only the matching guide and its required resources.

## Task guides

<!-- guides:start -->

- [ai-red-team](references/ai-red-team/GUIDE.md): Red-team AI apps and agents with PyRIT: prompt injection, tool misuse, and agent authority.
- [betterleaks](references/betterleaks.md): Scan the working tree and history for secrets; handle confirmed exposure.
- [code-review](references/code-review/GUIDE.md): Assess code and repository security; verify findings and repairs.
- [skill-security-review](references/skill-security-review/GUIDE.md): Review third-party skills and agent extensions for supply-chain risk.
- [sonarqube](references/sonarqube.md): Inspect SonarQube quality gates and issues, run local scans, and gate server-side AI actions with sonar.
- [threat-model](references/threat-model.md): Model attack paths, trust boundaries, abuse cases, and controls.
- [trivy](references/trivy/GUIDE.md): Scan dependencies, IaC, images, and licenses; generate SBOMs.

<!-- guides:end -->
