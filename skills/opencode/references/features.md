# OpenCode Feature Map

Use this map when choosing or configuring a capability beyond the quick links in [the skill](../SKILL.md). Read only the pages relevant to the task; the links own commands, schemas, availability, and limitations.

## Discover and Refresh

The [official documentation index](https://opencode.ai/docs/) was audited on 2026-09-09. Start there and check the changelog linked from the skill when a feature is missing or has changed; follow current upstream navigation if a page moves. Match the installed version, product surface, account, and platform before applying a recipe. This map covers capability families, not every setting or a promise that every feature is enabled locally.

## Capabilities

| Need | What to resolve | Official sources |
| --- | --- | --- |
| Choose a surface | Match terminal, web, and IDE behavior. | [Overview](https://opencode.ai/docs/) · [TUI](https://opencode.ai/docs/tui/) · [CLI](https://opencode.ai/docs/cli/) · [Web](https://opencode.ai/docs/web/) · [IDE](https://opencode.ai/docs/ide/) |
| Sessions and recovery | Find resume, fork, undo/redo, export/import, and session commands. | [TUI session commands](https://opencode.ai/docs/tui/) · [CLI session interfaces](https://opencode.ai/docs/cli/) · [Sharing](https://opencode.ai/docs/share/) |
| Agent roles and automation | Choose agent roles, custom commands, and headless execution. | [Agents](https://opencode.ai/docs/agents/) · [Commands](https://opencode.ai/docs/commands/) · [CLI run interface](https://opencode.ai/docs/cli/) |
| Server and editor protocols | Read server, client attachment, SDK, and ACP contracts. | [Server](https://opencode.ai/docs/server/) · [SDK](https://opencode.ai/docs/sdk/) · [ACP](https://opencode.ai/docs/acp/) · [Web interface](https://opencode.ai/docs/web/) |
| Instructions and skills | Check instruction precedence and skill discovery. | [Rules](https://opencode.ai/docs/rules/) · [Skills](https://opencode.ai/docs/skills/) · [References](https://opencode.ai/docs/references/) |
| Plugins and external tools | Find plugin events, MCP connections, and tool authoring. | [Plugins](https://opencode.ai/docs/plugins/) · [MCP](https://opencode.ai/docs/mcp-servers/) · [Custom tools](https://opencode.ai/docs/custom-tools/) · [Built-in tools](https://opencode.ai/docs/tools/) |
| Configuration and providers | Check merge precedence, authentication, and model variants. | [Configuration](https://opencode.ai/docs/config/) · [Providers](https://opencode.ai/docs/providers/) · [Models](https://opencode.ai/docs/models/) · [Zen](https://opencode.ai/docs/zen/) · [Go](https://opencode.ai/docs/go/) |
| Permissions and policy | Check tool approvals and policy enforcement. | [Permissions](https://opencode.ai/docs/permissions/) · [Policies](https://opencode.ai/docs/policies/) |
| Code intelligence and formatting | Resolve LSP, formatter, and tool integration. | [LSP](https://opencode.ai/docs/lsp/) · [Formatters](https://opencode.ai/docs/formatters/) · [Tools](https://opencode.ai/docs/tools/) |
| Repository automation | Find the supported GitHub and GitLab workflows. | [GitHub](https://opencode.ai/docs/github/) · [GitLab](https://opencode.ai/docs/gitlab/) |
| Terminal customization | Find theme and keyboard configuration. | [Themes](https://opencode.ai/docs/themes/) · [Keybindings](https://opencode.ai/docs/keybinds/) · [TUI](https://opencode.ai/docs/tui/) |
| Operations and deployment | Diagnose provider, network, platform, and enterprise issues. | [Troubleshooting](https://opencode.ai/docs/troubleshooting/) · [Network](https://opencode.ai/docs/network/) · [Enterprise](https://opencode.ai/docs/enterprise/) · [Ecosystem](https://opencode.ai/docs/ecosystem/) |

## Boundaries

Use the [CLI reference](https://opencode.ai/docs/cli/) for session, export/import, stats, debug, and server-attachment commands. The [plugin guide](https://opencode.ai/docs/plugins/) owns event-hook integrations; do not translate another harness's hook schema into OpenCode settings.
