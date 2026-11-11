---
name: sonarqube
description: "Inspect SonarQube quality gates and issues, run local scans, and gate server-side AI actions with sonar."
---

# SonarQube CLI (`sonar`)

Inspect quality gates, triage code and dependency findings, and run local diff scans with `sonar` (`sonarqube-cli`); [code-review](code-review/GUIDE.md) orders the full repository security review.

## Workstation Auth & Privacy

`fmind/dot` sets `SONARQUBE_CLI_KEYCHAIN_FILE=~/.sonar/sonarqube-cli/tokens.json` (`0600`) so `sonar` never triggers macOS Keychain modal prompts, and seeds `telemetry.enabled=false` in `~/.sonar/sonarqube-cli/cli-config.properties`.

1. **Verify session read-only**: run `sonar auth status` (checks active server, organization, and token validity; for CI/headless runs use `SONAR_TOKEN` from a secret store, never CLI arguments).
1. **Never print or copy token files**: never inspect `~/.sonar/sonarqube-cli/tokens.json`, pass tokens on argv, or commit `.sonar-config.json` with private server hostnames into public repos.

## Workflow

1. **Check quality gate and server issues (bounded JSON)**:

   ```bash
   sonar quality-gate status --project <project-key> --format json
   sonar list issues --project <project-key> --new-code --page-size 100 --format json
   ```

   Add `--pull-request <id>` or `--branch <name>` (mutually exclusive) and `--file <path>` to narrow scope; filter `--severities HIGH,BLOCKER` (Multi-Quality Rule mode) or `CRITICAL,BLOCKER` (Standard mode).

1. **Scan local diffs before pushing**:

   ```bash
   sonar analyze --staged --format json
   sonar analyze --base main --depth DEEP --format json
   ```

   Single `--file <path>` defaults to fast `STANDARD` depth; `--depth DEEP` enables cross-file taint and dataflow analysis. `sonar analyze secrets <paths>` and `sonar analyze dependency-risks` complement—never replace—[betterleaks](betterleaks.md), `uv audit`, and [trivy](trivy/GUIDE.md).

1. **Verify fixes**: re-run `sonar analyze --file <path> --format json` locally and confirm server quality-gate status after CI analysis completes.

## Hard Boundaries

- **Gate server-side AI commands**: `sonar analyze agentic` uploads source to server-side Vortex analysis, and `sonar remediate` triggers SonarQube Cloud AI code edits—both require explicit user approval and customer data-residency clearance.
- **Never run `sonar integrate`**: `fmind/dot` manages Claude, Antigravity, Copilot, OpenCode, Pi, and Git hooks centrally; `sonar integrate` rewrites host settings and hooks.
- **Treat secret findings as incidents**: never silence a real credential with `sonar allowlist secrets`; contain and rotate per [betterleaks](betterleaks.md).

## Documentation

- [SonarQube CLI docs](https://docs.sonarsource.com/sonarqube-cli/) · [Environment variables](https://docs.sonarsource.com/sonarqube-cli/using-sonarqube-cli/environment-variables)
- Companion guides: [code-review](code-review/GUIDE.md), [betterleaks](betterleaks.md), [trivy](trivy/GUIDE.md).
