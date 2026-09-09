# Grok Build Feature Map

Use this map when choosing or configuring a capability beyond the quick links in [the skill](../SKILL.md). Read only the pages relevant to the task; the links own commands, schemas, availability, and limitations.

## Discover and Refresh

The [official documentation index](https://docs.x.ai/build/overview) was audited on 2026-09-09. Start there and check the changelog linked from the skill when a feature is missing or has changed; follow current upstream navigation if a page moves. Match the installed version, product surface, account, and platform before applying a recipe. This map covers capability families, not every setting or a promise that every feature is enabled locally.

## Capabilities

| Need | What to resolve | Official sources |
| --- | --- | --- |
| Install and operate | Find authentication, model selection, and command behavior. | [Overview](https://docs.x.ai/build/overview) · [Modes and commands](https://docs.x.ai/build/modes-and-commands) · [CLI reference](https://docs.x.ai/build/cli/reference) |
| Plan and recover sessions | Choose planning mode and manage conversation state. | [Plan mode](https://docs.x.ai/build/features/plan-mode) · [Sessions](https://docs.x.ai/build/features/sessions) |
| Parallel work and isolation | Check subagent, worktree, and background-task lifecycle. | [Subagents](https://docs.x.ai/build/features/subagents) · [Worktrees](https://docs.x.ai/build/features/worktrees) · [Background tasks](https://docs.x.ai/build/features/background-tasks) |
| Headless and remote interfaces | Find scripting and ACP contracts; inspect dashboard capabilities separately. | [Headless scripting](https://docs.x.ai/build/cli/headless-scripting) · [CLI reference](https://docs.x.ai/build/cli/reference) · [Agent dashboard](https://docs.x.ai/build/features/dashboard) |
| Instructions and extensions | Find discovery, compatibility, and package configuration. | [Project rules / AGENTS.md](https://docs.x.ai/build/features/project-rules) · [Skills, plugins, marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces) · [MCP](https://docs.x.ai/build/features/mcp-servers) · [Hooks](https://docs.x.ai/build/features/hooks) |
| Configuration and models | Resolve settings and custom model/provider configuration. | [Settings overview](https://docs.x.ai/build/settings) · [Settings reference](https://docs.x.ai/build/settings/reference) · [Custom models](https://docs.x.ai/build/overview#custom-models) |
| Permissions and sandboxing | Check approvals and execution isolation separately. | [Permissions](https://docs.x.ai/build/features/permissions) · [Sandbox](https://docs.x.ai/build/features/sandbox) |
| Terminal customization | Find keyboard, theme, status, and terminal compatibility settings. | [Keyboard shortcuts](https://docs.x.ai/build/keyboard-shortcuts) · [Theming](https://docs.x.ai/build/features/theming) · [Status line](https://docs.x.ai/build/features/status-line) · [Terminal support](https://docs.x.ai/build/cli/terminal-support) |
| Deployment and privacy | Check enterprise deployment and retention controls for the chosen feature. | [Enterprise](https://docs.x.ai/build/enterprise) · [Video storage and ZDR](https://docs.x.ai/build/settings/zdr-video-storage) |

## Boundaries

For new capabilities or fixes, use the [Build changelog](https://x.ai/build/changelog), [official source repository](https://github.com/xai-org/grok-build), and [service status](https://status.x.ai). The Build navigation does not establish a dedicated scheduling interface or a general-purpose consumer skill bundle; verify current docs before proposing either.
