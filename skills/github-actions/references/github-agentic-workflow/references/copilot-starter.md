# Bounded Copilot Starter

Use this first as a manual, preview-only repository report. The deliberately small budgets are starting guardrails, not performance recommendations; adjust them only from `gh aw logs` and `gh aw audit` evidence.

## Authentication

Choose exactly one path:

| Path                        | Workflow configuration               | Credential boundary                                                                                               |
| --------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Organization-billed Copilot | Keep `copilot-requests: write` below | Requires an organization Copilot subscription with centralized billing; inference uses the per-run Actions token. |
| Copilot subscription        | Remove `copilot-requests: write`     | Store a fine-grained PAT with Copilot Requests access in the `COPILOT_GITHUB_TOKEN` repository secret.            |

## Workflow Source

Save as `.github/workflows/repository-report.md`:

```markdown
---
on:
  workflow_dispatch:

permissions:
  contents: read
  actions: read
  issues: read
  pull-requests: read
  copilot-requests: write

engine: copilot
network: defaults
max-turns: 10
max-ai-credits: 100

tools:
  github:
    toolsets: [repos, issues, pull_requests, actions]
    allowed-repos: "${{ github.repository }}"
    min-integrity: approved

safe-outputs:
  staged: true
  create-issue:
    max: 1
    title-prefix: "[agentic-report] "
  threat-detection:
    max-ai-credits: 50
---

# Repository Health Report

Inspect only this repository. Produce one concise maintainer report with evidence links covering recent pull requests, important open issues, failing Actions runs, and at most three prioritized next actions.

Do not speculate, modify files, or request any output other than the configured report issue. If evidence is missing, state the gap.
```

Then follow the [guide's validate, compile, and pilot steps](../GUIDE.md#workflow) with `repository-report` as the workflow name. A live run consumes GitHub Actions and Copilot capacity, while `safe-outputs.staged: true` prevents the proposed issue from being created.
