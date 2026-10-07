---
name: copilot
description: "Copilot sessions and extensions."
---

# GitHub Copilot CLI

Operate the Copilot CLI harness. Use [github-agentic-workflow](../../../github-actions/references/github-agentic-workflow/GUIDE.md) for GitHub Agentic Workflows rather than treating them as local CLI sessions.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- **Identify CLI, IDE, or cloud agent scope**: their behavior and settings differ.

## Official Skills

- [CLI skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills): supported layout and discovery.
- [Awesome Copilot](https://github.com/github/awesome-copilot): GitHub-hosted, community-contributed skills, agents, and plugins; hosting does not make every contribution first-party.
- **Select only relevant packages**: through the [vendor-skill policy](../../../agent-project/references/vendor-skills.md) when installation is requested.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [CLI releases and changelog](https://github.com/github/copilot-cli/releases)
- [CLI repository](https://github.com/github/copilot-cli): upstream entrypoint for support and newly documented features.
- [CLI customization](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot): custom agents, instructions, hooks, skills, and integrations.
