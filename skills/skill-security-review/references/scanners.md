---
name: scanners
description: "Run gitleaks and Trivy on a candidate with trusted configuration it cannot suppress."
---

# Trusted Scanners

Run secret and license scanners against a candidate snapshot without executing it; the parent [skill](../SKILL.md) owns the review workflow, the pattern searches, and the decision.

## Workflow

1. **Stay outside the candidate**: run from a trusted audit directory, not the snapshot root, so the candidate cannot supply configuration through ambient discovery.
1. **Pass trusted configuration explicitly**: reviewed configuration and ignore files for both tools. Trivy scans licenses only; Gitleaks owns secrets. Do not let candidate config, ignore files, or `gitleaks:allow` comments suppress findings. For Trivy, `--config` overrides ambient `TRIVY_CONFIG`; `--license-full` scans source license text, and all severities retain permissive and unknown license detections:

   ```bash
   gitleaks dir <root> --config <trusted-gitleaks.toml> --gitleaks-ignore-path <trusted-ignorefile> --ignore-gitleaks-allow --redact=100
   trivy --config <trusted-audit-policy.yaml> fs --ignorefile <trusted-ignorefile> --scanners license --license-full --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL <root>
   ```

1. **Record coverage**: each tool's version, the configuration used, skipped paths, and what the scanners cannot see (instruction authority, Unicode payloads, executable behavior); report those as the parent's manual-review evidence, not as scanner passes.

## Documentation

- [gitleaks](../../code-security/references/gitleaks.md) · [trivy](../../code-security/references/trivy/GUIDE.md)
