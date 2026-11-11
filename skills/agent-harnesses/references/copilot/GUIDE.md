---
name: copilot
description: "Copilot sessions and extensions."
---

# GitHub Copilot CLI

Operate Copilot CLI; [github-actions](../../../github-actions/SKILL.md) owns GitHub Agentic Workflows.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- **Separate CLI, IDE, and cloud agent scopes**: settings and behavior differ across them.
- **Separate tool approval from folder trust**: `--allow-all-tools` (without it, `-p` denies unapproved tools) and managed `COPILOT_ALLOW_ALL=1` only auto-approve tools; setting `COPILOT_ALLOW_ALL=true` also trusts cwd and loads its skills, plugins, MCP servers, and shell hooks. Use `--trust-folder` per reviewed run; `--share-gist` publishes content.

## Official Skills

- [CLI skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills): layout and discovery.
- [Awesome Copilot](https://github.com/github/awesome-copilot): community-contributed skills, agents, and plugins (not first-party).

## Documentation

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- Releases: [Copilot CLI](https://github.com/github/copilot-cli/releases)
