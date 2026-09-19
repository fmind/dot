---
name: codex
description: "Codex sessions and customization."
---

# Codex

Operate Codex's harness, sessions, and customization. Use a host-provided OpenAI documentation skill when available for deeper product questions; API application development is a separate workflow.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- Inspect `codex --version` and `codex --help`; identify CLI, app, or cloud context. App features are not automatically CLI commands.
- Resolve configuration precedence and permission mode before changing execution behavior.
- Do not freeze model lists or release details in this skill.

## Official Skills

- [OpenAI skills catalog](https://github.com/openai/skills) · [OpenAI plugins catalog](https://github.com/openai/plugins): choose a package that matches the task and check already installed native skills first.
- [Skills and plugins documentation](https://learn.chatgpt.com/docs/skills-and-plugins): current discovery and customization entrypoint.
- For requested installations, follow the [vendor-skill policy](../../../agent-project/references/vendor-skills.md) and retain the existing package manager's ownership.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Documentation](https://learn.chatgpt.com/docs) · [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [Changelog](https://learn.chatgpt.com/docs/changelog) · [CLI releases](https://github.com/openai/codex/releases): select Codex entries and the surface in use.
- [Configuration](https://learn.chatgpt.com/docs/configuration) · [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Permissions](https://learn.chatgpt.com/docs/permissions) · [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Remote connections](https://learn.chatgpt.com/docs/remote-connections) · [Hooks](https://learn.chatgpt.com/docs/hooks)
