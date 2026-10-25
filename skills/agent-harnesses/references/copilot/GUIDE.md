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

## Top Links

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [CLI releases and changelog](https://github.com/github/copilot-cli/releases)
- [CLI repository](https://github.com/github/copilot-cli): upstream entrypoint for support and newly documented features.
- [CLI customization](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot): custom agents, instructions, hooks, skills, and integrations.

## Operation Links

| Need                           | What to resolve                                                       | Official sources                                                                                                                                                                                                                                                  |
| ------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Session lifecycle and recovery | Manage concurrent work, steering, context, and rollback.              | [Multiple sessions](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/work-with-multiple-sessions) · [Steering](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-agents)                                         |
| Planning and parallel work     | Choose autonomy, parallel dispatch, or a second opinion.              | [Autopilot](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/use-autopilot-mode) · [Fleet](https://docs.github.com/en/copilot/concepts/agent-capabilities/choosing-and-delegating-agent-work/delegating-and-parallelizing-work-with-agents) |
| Remote and scheduled work      | Distinguish remote steering, cloud delegation, and schedules.         | [Remote Control](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/about-remote-control) · [Remote steering](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-remotely)           |
| Programmatic use and CI        | Read non-interactive, ACP, SDK, and automation contracts.             | [Programmatic CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically) · [Programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference)                |
| Instructions, hooks, and tools | Resolve instructions and connect code intelligence or external tools. | [Custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) · [Hooks](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks)                                             |
| Permissions and limits         | Check tool access, isolation, and session budgets.                    | [Allowing tools](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools) · [Local sandboxing](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/understanding-local-sandboxing)                 |

Cloud-agent delegation and local CLI execution have different environments; the SDK and ACP links above cover embedding the harness.
