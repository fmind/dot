---
name: mcp-setup
description: "Add or fix MCP servers in coding agents and verify access."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mcp-setup
  created: "2026-06-23"
  updated: "2026-11-07"
---

# MCP Setup

Connect only the MCP capability the task needs, using the installed host's native interface. [MCP implementation](../agent-protocols/references/mcp/GUIDE.md) owns server implementation and [agent-project](../agent-project/SKILL.md) owns shared project layout.

## Workflow

1. **Prefer an existing CLI or skill**: the owner prefers CLIs over MCP servers. Add a server only when no installed CLI or skill covers the capability, or the host can reach it only through MCP.
1. **Review the server**: verify its source, transport, tools, credential flow, and requested permissions before launching it, then register it with the matching [host commands](references/host-commands.md).
1. **Verify**: list the configured server, check its tool surface, and exercise a small read-only call; registration alone does not prove authentication or safe writes.

## Gotchas

- **Claude default scope is `local`**: the server lands in `~/.claude.json` for this path only; pass `--scope project` to share it through `.mcp.json`.
- **Resolve runners in the agent environment**: agy runs commands with `bash -c` and no shell startup files, so a bare `uvx` or project command may not resolve. Register a pinned `uvx --from` command or a locked virtual environment's absolute executable instead.
- **Keep the trust boundary**: review repository-provided MCP files before starting their servers, enable only the tools a workflow needs (`copilot mcp add --tools`), and keep credentials out of arguments and committed files. Preserve authorized autonomous writes; require confirmation only for effects outside existing authority.

## Documentation

- [Model Context Protocol](https://modelcontextprotocol.io) · [MCP registry](https://registry.modelcontextprotocol.io)
- Releases: [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog) · [protocol releases](https://github.com/modelcontextprotocol/modelcontextprotocol/releases)
- Google Cloud managed MCP: follow the [supported products](https://docs.cloud.google.com/mcp/supported-products) and [authentication](https://docs.cloud.google.com/mcp/authenticate-mcp) pages, select the identity and project with [gcloud](../gcloud/SKILL.md), and grant only the needed roles. Enabling the product API is enough (there is no separate MCP enable step), and not every host can use local ADC.
