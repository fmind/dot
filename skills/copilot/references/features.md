# GitHub Copilot CLI Operation Links

Start with the [official documentation index](https://docs.github.com/en/copilot/how-tos/copilot-cli) and the changelog in [the skill](../SKILL.md). Use these links for execution decisions; discover other capabilities upstream. Match the installed version, product surface, account, and platform before applying a recipe.

| Need | What to resolve | Official sources |
| --- | --- | --- |
| Session lifecycle and recovery | Manage concurrent work, steering, context, and rollback. | [Multiple sessions](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/work-with-multiple-sessions) · [Steering](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-agents) |
| Planning and parallel work | Choose autonomy, parallel dispatch, or a second opinion. | [Autopilot](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/autopilot) · [Fleet](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/fleet) |
| Remote and scheduled work | Distinguish remote steering, cloud delegation, and schedules. | [Remote Control](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-remote-control) · [Remote steering](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/steer-remotely) |
| Programmatic use and CI | Read non-interactive, ACP, SDK, and automation contracts. | [Programmatic CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically) · [Programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference) |
| Instructions, hooks, and tools | Resolve instructions and connect code intelligence or external tools. | [Custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) · [Hooks](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks) |
| Permissions and limits | Check tool access, isolation, and session budgets. | [Allowing tools](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools) · [Local sandboxing](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/understanding-local-sandboxing) |

## Boundaries

Cloud-agent delegation and local CLI execution have different environments. [GitHub Agentic Workflows](../../github-agentic-workflow/SKILL.md) owns repository workflow authoring; the CLI SDK and ACP links above cover embedding the harness.
