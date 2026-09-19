---
name: copilot
description: "Copilot sessions and extensions."
---

# GitHub Copilot CLI

Operate the Copilot CLI harness. Use [github-agentic-workflow](../../../github-actions/references/github-agentic-workflow/GUIDE.md) for GitHub Agentic Workflows rather than treating them as local CLI sessions.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- Inspect `copilot --version` and `copilot --help`; identify whether the request concerns CLI, IDE, or cloud agent behavior.
- Read the CLI release notes before using new flags, settings, or account-dependent features; avoid embedding version tables or model lists here.
- Check tool permission scope before enabling autonomous execution; extensions can add executable integrations.
- Verify discovery through the installed CLI's skill or plugin listing.

## Official Skills

- [CLI skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills): supported layout and discovery.
- [Awesome Copilot](https://github.com/github/awesome-copilot): GitHub-hosted, community-contributed skills, agents, and plugins; hosting does not make every contribution first-party.
- Select only a relevant package through the [vendor-skill policy](../../../agent-project/references/vendor-skills.md) when installation is requested.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [CLI releases and changelog](https://github.com/github/copilot-cli/releases)
- [CLI repository](https://github.com/github/copilot-cli): upstream entrypoint for support and newly documented features.
- [CLI customization](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot): custom agents, instructions, hooks, skills, and integrations.
