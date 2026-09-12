---
name: codex
description: Operate OpenAI Codex CLI and app sessions with current official guidance. Use when configuring codex, permissions, skills, plugins, or remote connections.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/codex
  created: "2026-09-09"
  updated: "2026-09-11"
---

# Codex

Operate Codex's harness, sessions, and customization. Use a host-provided OpenAI documentation skill when available for deeper product questions; API application development is a separate workflow.

## Workflow

1. Inspect `codex --version` and `codex --help`; identify CLI, app, or cloud context and the workspace or session involved.
1. Open the relevant official page and changelog before relying on flags, configuration keys, models, or feature availability. Compare with installed help and report any version gap; do not freeze model lists or release details in this skill.
1. Use the documented session or configuration interface. Resolve configuration precedence and permission mode before changing execution behavior; app features are not automatically CLI commands.
1. Verify the requested behavior and resulting artifacts. Use [agent-project](../agent-project/SKILL.md) for shared instruction and skill discovery, and [agent-mcp](../agent-mcp/SKILL.md) for MCP registration.

## Official Skills

- [OpenAI skills catalog](https://github.com/openai/skills) · [OpenAI plugins catalog](https://github.com/openai/plugins): choose a package that matches the task and check already installed native skills first.
- [Skills and plugins documentation](https://learn.chatgpt.com/docs/skills-and-plugins): current discovery and customization entrypoint.
- For requested installations, follow the [vendor-skill policy](../agent-project/references/vendor-skills.md) and retain the existing package manager's ownership.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Documentation](https://learn.chatgpt.com/docs) · [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [Changelog](https://learn.chatgpt.com/docs/changelog) · [CLI releases](https://github.com/openai/codex/releases): select Codex entries and the surface in use.
- [Configuration](https://learn.chatgpt.com/docs/configuration) · [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Permissions](https://learn.chatgpt.com/docs/permissions) · [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Remote connections](https://learn.chatgpt.com/docs/remote-connections) · [Hooks](https://learn.chatgpt.com/docs/hooks)
