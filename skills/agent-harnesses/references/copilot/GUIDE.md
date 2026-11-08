---
name: copilot
description: "Copilot sessions and extensions."
---

# GitHub Copilot CLI

Operate the Copilot CLI harness. Use [github-actions](../../../github-actions/SKILL.md) for GitHub Agentic Workflows rather than treating them as local CLI sessions.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- **Identify CLI, IDE, or cloud agent scope**: their behavior and settings differ.
- **Keep tool approval separate from folder trust**: `--allow-all-tools` (without it, `-p` denies every tool request no allow rule approves) and the managed `COPILOT_ALLOW_ALL=1` only auto-approve tools; the exact value `true` also trusts the working directory and loads its skills, plugins, MCP servers, and shell hooks. Use `--trust-folder` for one reviewed run, and treat `--share-gist` as publication.

## Official Skills

- [CLI skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills): supported layout and discovery.
- [Awesome Copilot](https://github.com/github/awesome-copilot): GitHub-hosted, community-contributed skills, agents, and plugins; hosting does not make every contribution first-party.

## Documentation

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- Releases: [Copilot CLI](https://github.com/github/copilot-cli/releases)
