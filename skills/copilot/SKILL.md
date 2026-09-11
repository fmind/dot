---
name: copilot
description: Operate GitHub Copilot CLI sessions and extensions using current GitHub guidance. Use when configuring copilot, custom agents, skills, or plugins.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/copilot
  created: "2026-09-09"
  updated: "2026-09-11"
---

# GitHub Copilot CLI

Operate the Copilot CLI harness. Use [github-agentic-workflow](../github-agentic-workflow/SKILL.md) for GitHub Agentic Workflows rather than treating them as local CLI sessions.

## Workflow

1. Inspect `copilot --version` and `copilot --help`; identify the workspace and whether the request concerns CLI, IDE, or cloud agent behavior.
1. Open the applicable official page and CLI release notes before using new flags, settings, or account-dependent features. Compare with the installed CLI; avoid embedding version tables or model lists here.
1. Use the documented session or extension interface. Check tool permission scope before enabling autonomous execution; extensions can add executable integrations.
1. Verify the session result and discovery through the installed CLI's skill or plugin listing. Use [agent-project](../agent-project/SKILL.md) for instruction layout and [agent-mcp](../agent-mcp/SKILL.md) for MCP registration.

## Official Skills

- [CLI skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills): supported layout and discovery.
- [Awesome Copilot](https://github.com/github/awesome-copilot): GitHub-hosted, community-contributed skills, agents, and plugins; hosting does not make every contribution first-party.
- Select only a relevant package through the [vendor-skill policy](../agent-project/references/vendor-skills.md) when installation is requested.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [CLI releases and changelog](https://github.com/github/copilot-cli/releases)
- [CLI repository](https://github.com/github/copilot-cli): upstream entrypoint for support and newly documented features.
- [CLI customization](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot): custom agents, instructions, hooks, skills, and integrations.
