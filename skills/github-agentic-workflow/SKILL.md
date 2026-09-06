---
name: github-agentic-workflow
description: Design, secure, compile, run, and audit GitHub Agentic Workflows with GitHub Copilot. Use when repository automation needs AI reasoning in GitHub Actions.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/github-agentic-workflow
  created: "2026-09-03"
  updated: "2026-09-05"
---

# GitHub Agentic Workflow

Run Copilot in GitHub Actions for bounded investigation, triage, review, and documentation. Keep deterministic builds/tests/deployment in [github-actions](../github-actions/SKILL.md).

## Workflow

1. **Choose the job**: use reasoning only where context changes the work; resolve repository, candidate git revision, expected output, and existing authority.
1. **Inspect native support**: read `gh aw version` and the repository's generated dispatcher. Use [authoring.md](references/authoring.md) for setup, runtime identity, and lifecycle commands.
1. **Constrain the candidate**: begin with read permissions, narrow tools/network, explicit budgets, staged safe outputs, and the [Copilot starter](references/copilot-starter.md).
1. **Validate locally**: run `gh aw validate --strict` and `gh aw compile`; inspect source and lock output together before publication.
1. **Pilot when authorized**: preview dispatch, then run within Actions/Copilot spend authority; inspect output, audit traces and credits, and remove staging only after evidence supports it.

## Gotchas

- **Two Copilot roles**: `gh aw init --engine copilot` configures Copilot as the authoring assistant; `engine: copilot` plus runtime authentication selects it inside the Actions workflow.
- **Generated lock file**: Markdown body edits load at runtime, but frontmatter edits require recompilation; repository policy may still require compiling every change.
- **Web search**: Copilot supports `web-fetch`, but native `web-search` is unavailable; add a trusted, narrowly configured MCP search server only when needed.
- **Writes and spend**: `gh aw run`, safe outputs without staged mode, `--push`, and `--auto-merge-prs` can mutate GitHub or consume paid resources; require explicit authority for the exact repository and action.
- **Imported workflows**: Treat their triggers, permissions, tools, network, instructions, safe outputs, and lock files as executable supply-chain input; prefer pinned trusted releases.
- **Guardrails are boundaries, not proof**: Sandboxing, integrity filtering, threat detection, and safe outputs reduce blast radius; they do not make broad permissions or unreviewed output safe.

## Official Skills

- `gh aw init --engine copilot` installs GitHub's repository-scoped `agentic-workflows` dispatcher skill, Copilot custom agent, and MCP wiring. Use those generated, upgradeable assets for detailed authoring instead of copying the evolving upstream schema into this global skill.

## Documentation

- [Overview](https://github.github.com/gh-aw/introduction/overview/) · [Copilot engine](https://github.github.com/gh-aw/engines/copilot/) · [CLI](https://github.github.com/gh-aw/setup/cli/) · [Security architecture](https://github.github.com/gh-aw/introduction/architecture/) · [Safe outputs](https://github.github.com/gh-aw/reference/safe-outputs/) · [Cost management](https://github.github.com/gh-aw/reference/cost-management/)
- Companion skills: [github-actions](../github-actions/SKILL.md) (deterministic CI/CD and workflow linting), [github-issues](../github-issues/SKILL.md) and [github-pull-request](../github-pull-request/SKILL.md) (human-controlled GitHub writes), [agent-mcp](../agent-mcp/SKILL.md) (host MCP configuration).
