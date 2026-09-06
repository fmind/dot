---
name: agent-mcp
description: Configure MCP servers for Antigravity, Claude Code, Codex, Copilot, and Grok with each host's native add command at project or user scope. Use when an agent needs an MCP server.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-mcp
  created: "2026-06-23"
  updated: "2026-09-06"
---

# Configure Agent MCP Servers

Connect only the MCP capability the task needs, using the installed host's native interface. [mcp-server](../mcp-server/SKILL.md) owns server implementation and [agent-project](../agent-project/SKILL.md) owns shared project layout.

## Workflow

1. **Identify host and scope**: inspect the installed `agy`, `claude`, `codex`, `copilot`, or `grok` interface and choose project versus user configuration.
1. **Review the server**: verify its source, transport, tools, credential flow, and requested permissions before launching it; use [host commands](references/host-commands.md) for the matching setup.
1. **Configure once**: preserve unmanaged settings, avoid duplicate registrations, and pass secrets through the supported environment or secret manager.
1. **Verify**: list the configured server, check its tool surface, and exercise a small read-only call; registration alone does not prove authentication or safe writes.
1. **Google Cloud case**: read [google-cloud-mcp.md](references/google-cloud-mcp.md) only for those product-specific registrations.

## Gotchas

- **Claude default scope is `local`**: the server lands in `~/.claude.json` for this path only; pass `--scope project` to share it through `.mcp.json`.
- **Repository trust**: review project MCP files before starting their servers; do not auto-approve every repository-provided server.
- **Runner resolution**: `uvx` and `docker` must resolve from the agent's environment, not only from your shell.
- **Tool scope**: enable only the tools a workflow needs (`copilot mcp add --tools`) and keep write-capable tools approval-gated.
- **Auth errors**: confirm OAuth, Application Default Credentials, scopes, and IAM before broadening permissions.

## Documentation

- [Model Context Protocol](https://modelcontextprotocol.io) · [MCP registry](https://registry.modelcontextprotocol.io) · [Google Cloud managed MCP](references/google-cloud-mcp.md)
- Companion skills: [agent-project](../agent-project/SKILL.md) (repository layout), [gcloud](../gcloud/SKILL.md) (project and IAM context for managed servers).
