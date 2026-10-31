# Trusted Scanners

Run secret and license scanners against a candidate snapshot without executing it; the parent [guide](../GUIDE.md) owns the review workflow, the pattern searches, and the decision.

## Workflow

1. **Stay outside the candidate**: run from a trusted audit directory, not the snapshot root, so the candidate cannot supply configuration through ambient discovery.
1. **Pass trusted configuration explicitly**: reviewed configuration and ignore files for both tools. Trivy scans licenses only; Betterleaks owns secrets. Do not let candidate config, ignore files, or `betterleaks:allow` / `gitleaks:allow` comments suppress findings. Betterleaks reads inside bundled archives only with `--max-archive-depth`. For Trivy, `--config` overrides ambient `TRIVY_CONFIG`, `--ignorefile ''` loads no ignore file, `--license-full` scans source license text, and all severities retain permissive and unknown license detections:

   ```bash
   betterleaks dir <root> --config <trusted-betterleaks.toml> --gitleaks-ignore-path <trusted-ignorefile> --ignore-gitleaks-allow --max-archive-depth 2 --redact=100
   trivy --config <trusted-audit-policy.yaml> fs --ignorefile <trusted-ignorefile> --scanners license --license-full --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL <root>
   ```

1. **Record coverage**: each tool's version, the configuration used, skipped paths, and what the scanners cannot see (instruction authority, Unicode payloads, executable behavior); report those as the parent's manual-review evidence, not as scanner passes.

## Documentation

- [betterleaks](../../betterleaks.md) · [trivy](../../trivy/GUIDE.md)
