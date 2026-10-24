---
name: codex
description: "Codex sessions and customization."
---

# Codex

Operate Codex's harness, sessions, and customization. Use a host-provided OpenAI documentation skill when available for deeper product questions; API application development is a separate workflow.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- **Identify CLI, app, or cloud context**: app features are not automatically CLI commands.
- **Do not freeze model lists or release details in this skill.**

## Official Skills

- [OpenAI skills catalog](https://github.com/openai/skills) · [OpenAI plugins catalog](https://github.com/openai/plugins): choose a package that matches the task and check already installed native skills first.
- [Skills and plugins documentation](https://learn.chatgpt.com/docs/skills-and-plugins): current discovery and customization entrypoint.
- **Follow the vendor-skill policy**: for requested installations, follow the [vendor-skill policy](../../../agent-project/references/vendor-skills.md) and retain the existing package manager's ownership.

## Top Links

- [Documentation](https://learn.chatgpt.com/docs) · [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [Changelog](https://learn.chatgpt.com/docs/changelog) · [CLI releases](https://github.com/openai/codex/releases): select Codex entries and the surface in use.
- [Configuration](https://learn.chatgpt.com/docs/configuration) · [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Permissions](https://learn.chatgpt.com/docs/permissions) · [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Remote connections](https://learn.chatgpt.com/docs/remote-connections) · [Hooks](https://learn.chatgpt.com/docs/hooks)

## Operation Links

Use these for session recovery, automation, and integration decisions; discover other capabilities from the official documentation index.

| Need                                  | What to resolve                                                    | Official sources                                                                                                                                    |
| ------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Session and task operation            | Find commands, steering, persistent work, and review controls.     | [CLI commands](https://learn.chatgpt.com/docs/reference/commands) · [CLI customization](https://learn.chatgpt.com/docs/cli-customization)           |
| Workspaces and execution environments | Check worktree isolation, setup scripts, and network access.       | [Environment modes](https://learn.chatgpt.com/docs/environments/modes) · [Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees) |
| Remote and scheduled work             | Check remote connectivity, automation triggers, and notifications. | [Mobile](https://learn.chatgpt.com/docs/mobile) · [Remote connections](https://learn.chatgpt.com/docs/remote-connections)                           |
| Headless and programmatic use         | Read machine-output and integration contracts.                     | [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) · [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)                 |
| Skills, plugins, and hooks            | Discover and build task-specific extensions.                       | [Skills and plugins](https://learn.chatgpt.com/docs/skills-and-plugins) · [Build skills](https://learn.chatgpt.com/docs/build-skills)               |
| Approvals and isolation               | Check permission modes, sandbox boundaries, and automatic review.  | [Permissions](https://learn.chatgpt.com/docs/permissions) · [Permission modes](https://learn.chatgpt.com/docs/permission-modes)                     |

Match the installed version, product surface, account, and platform before applying a recipe. The documentation shares navigation with other OpenAI products: keep the Codex surface explicit when following redirected pages; the [CLI source and releases](https://github.com/openai/codex) are a second reference for local behavior.
