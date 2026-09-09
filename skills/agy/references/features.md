# Antigravity Feature Map

Use this map when choosing or configuring a capability beyond the quick links in [the skill](../SKILL.md). Read only the pages relevant to the task; the links own commands, schemas, availability, and limitations.

## Discover and Refresh

The [official documentation index](https://antigravity.google/docs/cli/overview/) was audited on 2026-09-09. Start there and check the changelog linked from the skill when a feature is missing or has changed; follow current upstream navigation if a page moves. Match the installed version, product surface, account, and platform before applying a recipe. This map covers capability families, not every setting or a promise that every feature is enabled locally.

## Capabilities

| Need | What to resolve | Official sources |
| --- | --- | --- |
| Choose a surface | Match CLI, desktop, and IDE capabilities. | [CLI overview](https://antigravity.google/docs/cli/overview/) · [Desktop features](https://antigravity.google/docs/features/) · [IDE overview](https://antigravity.google/docs/ide/overview/) |
| Install, authenticate, migrate | Check platform and provider setup before changing the installation. | [Installation and auth](https://antigravity.google/docs/cli/install/) · [Gemini CLI migration](https://antigravity.google/docs/cli/gcli-migration/) · [CLI reference](https://antigravity.google/docs/cli/reference/) |
| Daily interaction | Find input, context attachment, and command behavior. | [Using agy](https://antigravity.google/docs/cli/using/) · [Prompting](https://antigravity.google/docs/cli/prompting/) · [Best practices](https://antigravity.google/docs/cli/best-practices/) |
| Projects and session recovery | Select the workspace and recover the intended conversation. | [CLI projects](https://antigravity.google/docs/cli/projects/) · [Conversations](https://antigravity.google/docs/cli/conversations/) · [Resume](https://antigravity.google/docs/cli/commands/resume/) |
| Planning and review | Choose an execution mode and inspect plans, diffs, and artifacts. | [Execution modes](https://antigravity.google/docs/cli/modes/) · [Artifacts](https://antigravity.google/docs/cli/artifacts/) · [Diff review](https://antigravity.google/docs/cli/commands/diff/) |
| Parallel and background work | Check coordination, background task lifecycle, and preview availability. | [Subagents and background tasks](https://antigravity.google/docs/cli/subagents/) · [Agent management](https://antigravity.google/docs/cli/commands/agents/) · [Teamwork](https://antigravity.google/docs/teamwork/) |
| Reasoning and code discovery | Find deeper reasoning and code-search features. | [Boost](https://antigravity.google/docs/boost/) · [Code search](https://antigravity.google/docs/cli/commands/codesearch/) · [Models](https://antigravity.google/docs/models/) |
| Remote and scripted execution | Distinguish persistent remote service setup from headless task execution. | [Remote Control](https://antigravity.google/docs/remote-control/) · [Headless mode](https://antigravity.google/docs/cli/headless/) |
| Instructions and extensions | Use the matching surface for rules, skills, plugins, hooks, and MCP. | [CLI plugins and skills](https://antigravity.google/docs/cli/plugins/) · [CLI MCP](https://antigravity.google/docs/cli/mcp/) · [Desktop rules](https://antigravity.google/docs/rules-workflows/) · [Desktop hooks](https://antigravity.google/docs/hooks/) · [Desktop sidecars](https://antigravity.google/docs/sidecars/) |
| Permissions and isolation | Check approvals separately from filesystem and network isolation. | [CLI permissions](https://antigravity.google/docs/cli/permissions/) · [CLI sandbox](https://antigravity.google/docs/cli/sandbox/) · [Desktop sandbox](https://antigravity.google/docs/sandbox/) |
| IDE and browser tools | Find editor integrations, browser controls, and visual review. | [IDE extensions](https://antigravity.google/docs/ide/extensions/) · [Browser](https://antigravity.google/docs/ide/browser/) · [Browser access controls](https://antigravity.google/docs/ide/allowlist-denylist/) · [Editor review](https://antigravity.google/docs/ide/review-changes-editor/) |
| Terminal customization | Find Vim, keybindings, status, titles, and voice controls. | [Settings](https://antigravity.google/docs/cli/settings/) · [Vim](https://antigravity.google/docs/cli/vim-editor-mode/) · [Status line](https://antigravity.google/docs/cli/statusline/) · [Window title](https://antigravity.google/docs/cli/title/) · [Voice](https://antigravity.google/docs/cli/commands/voice/) |
| SDK integration | Use the SDK contract for programmatic orchestration. | [SDK overview](https://antigravity.google/docs/sdk/overview/) · [Structured output](https://antigravity.google/docs/sdk/structured-output/) · [Lifecycle and hooks](https://antigravity.google/docs/sdk/lifecycle/) |
| Usage and operations | Check current quotas, credits, enterprise availability, and failures. | [Model quotas](https://antigravity.google/docs/cli/commands/usage/) · [AI credits](https://antigravity.google/docs/cli/credits/) · [Plans](https://antigravity.google/docs/plans/) · [Enterprise](https://antigravity.google/docs/enterprise/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/) |

## Boundaries

For SDK implementation, continue with [antigravity-sdk](../../antigravity-sdk/SKILL.md). The CLI, desktop, and IDE have separate documentation branches; check their respective customization and sandbox contracts.
