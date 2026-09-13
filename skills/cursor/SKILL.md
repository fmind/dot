---
name: cursor
description: Operate Cursor CLI sessions and customization. Use when configuring cursor-agent, resuming work, running headless tasks, or managing Cursor skills, plugins, and MCP.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cursor
  created: "2026-09-13"
  updated: "2026-09-13"
---

# Cursor

Operate Cursor's CLI and distinguish local sessions from editor and remote-worker features. This workstation exposes the upstream `agent` executable as `cursor-agent`; preserve that name instead of assuming a bare `agent` belongs to Cursor.

## Workflow

1. Inspect `cursor-agent --version` and `cursor-agent --help`; resolve the workspace, existing session, and requested execution mode before starting another task.
1. Read the relevant [operation links](references/features.md) and CLI changelog, comparing flags and configuration with the installed release. Keep model lists and evolving feature details upstream.
1. Reuse `--resume <chat-id>` or `resume` when continuing work. For automation, select `--print` and its output format deliberately; `--mode plan` and `--mode ask` are read-only modes, while `--print` alone retains write and shell tools.
1. Preserve the managed global configuration, explicit denials, Vim mode, and disabled attribution. Read the documented configuration scope before editing: global settings use `~/.cursor/cli-config.json`, while `.cursor/cli.json` holds project permissions. Resolve environment overrides before diagnosing the wrong file.
1. Inspect skills through Cursor's Skills interface and MCP through the installed `cursor-agent mcp --help`, `list`, and `list-tools` commands. [agent-project](../agent-project/SKILL.md) owns shared discovery; [agent-mcp](../agent-mcp/SKILL.md) owns registration.
1. Verify resulting files, tests, and session state. A chat ID, streamed text, or a remote task's completion message does not prove the requested artifact or local gate.

## Gotchas

- **Local versus remote**: user-level skills are not automatically copied to Cloud Agents, remote SSH sessions, or self-hosted workers. Use reviewed project skills or worker packaging for those environments.
- **MCP inspection can connect**: listing server status or tools may start configured processes or contact services; inspect the configuration and server source first.
- **Persistent work**: `persist`, `worker`, worktree setup scripts, and trust/approval flags have distinct effects. Resolve their installed contract and reuse only the authority granted for the task.
- **Secrets**: supply authentication through the supported environment or login flow; keep API keys and custom authorization headers out of arguments and shared output.

## Official Skills

Cursor provides built-in authoring and configuration skills alongside user packages. Inspect the installed interface before adding duplicates; [skills](https://cursor.com/docs/skills) and [plugins](https://cursor.com/docs/plugins) document the supported surfaces. Apply the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) to requested third-party packages.

## Top Links

- [CLI documentation](https://cursor.com/docs/cli/overview) · [CLI changelog](https://cursor.com/docs/cli/changelog)
- [Parameters](https://cursor.com/docs/cli/reference/parameters) · [Configuration](https://cursor.com/docs/cli/reference/configuration) · [Permissions](https://cursor.com/docs/cli/reference/permissions)
- [Using the CLI](https://cursor.com/docs/cli/using) · [MCP](https://cursor.com/docs/cli/mcp)
