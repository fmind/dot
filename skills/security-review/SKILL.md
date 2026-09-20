---
name: security-review
description: "Review and fix code security; scan secrets and vulnerabilities with Gitleaks and Trivy."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/security-review
  created: "2026-07-04"
  updated: "2026-09-20"
---

# Security Review

Investigate and fix security defects with evidence. Choose code review, secret scanning, or vulnerability scanning from the task; findings need verification and scanners do not replace reasoning.

## Workflow

Read only the matching guide and its required resources. Use a known guide directly when shared prerequisites are not needed.

## Task guides

<!-- guides:start -->

- [code-review](references/code-review/GUIDE.md): Assess code and repository security; verify findings and repairs.
- [gitleaks](references/gitleaks.md): Secret scanning and verified exposure handling.
- [trivy](references/trivy/GUIDE.md): Dependency, configuration, image, license, and SBOM scanning.

<!-- guides:end -->
