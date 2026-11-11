# Trusted Scanners

Scan a candidate snapshot for secrets and licenses without executing it; the [parent guide](../GUIDE.md) owns manual pattern checks and the verdict.

## Workflow

1. **Run outside `<root>`** with explicit trusted configs/ignorefiles so candidate files or `betterleaks:allow` / `gitleaks:allow` comments cannot suppress hits (keep Betterleaks `--max-archive-depth` >= default 8; Trivy `--config` overrides `TRIVY_CONFIG`, `--ignorefile ''` disables ignorefiles, and `--license-full` + all severities catch permissive/unknown licenses):

   ```bash
   betterleaks dir <root> --config <trusted-betterleaks.toml> --gitleaks-ignore-path <trusted-ignorefile> --ignore-gitleaks-allow --redact=100
   trivy --config <trusted-audit-policy.yaml> fs --ignorefile <trusted-ignorefile> --scanners license --license-full --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL <root>
   ```

1. **Record versions, configs, and skipped paths**; instruction authority, Unicode smuggling, and code behavior remain manual-review items.

## Documentation

- [betterleaks](../../betterleaks.md) · [trivy](../../trivy/GUIDE.md)
