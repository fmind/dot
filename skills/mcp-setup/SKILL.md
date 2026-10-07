---
name: mcp-setup
description: "Add or fix MCP servers in coding agents and verify access."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mcp-setup
  created: "2026-06-23"
  updated: "2026-10-07"
---

# MCP Setup

Connect only the MCP capability the task needs, using the installed host's native interface. [MCP implementation](../agent-protocols/references/mcp/GUIDE.md) owns server implementation and [agent-project](../agent-project/SKILL.md) owns shared project layout.

## Workflow

1. **Review the server**: verify its source, transport, tools, credential flow, and requested permissions before launching it; use [host commands](references/host-commands.md) for the matching setup.
1. **Verify**: list the configured server, check its tool surface, and exercise a small read-only call; registration alone does not prove authentication or safe writes.
1. **Use the Google Cloud guide for its products**: read [google-cloud-mcp.md](references/google-cloud-mcp.md) only for those product-specific registrations.

## Gotchas

- **Claude default scope is `local`**: the server lands in `~/.claude.json` for this path only; pass `--scope project` to share it through `.mcp.json`.
- **Vet repository-provided servers first**: review project MCP files before starting their servers; do not auto-approve every repository-provided server.
- **Resolve runners in the agent environment**: `uvx` and `docker` must resolve from the agent's environment, not only from your shell.
- **Scope tools to the workflow**: enable only the tools a workflow needs (`copilot mcp add --tools`) and enforce the user's granted scope at the tool boundary. Preserve authorized autonomous writes; require confirmation only for effects outside existing authority.
- **Diagnose auth before broadening permissions**: confirm OAuth, Application Default Credentials, scopes, and IAM before broadening permissions.

## Documentation

- [Model Context Protocol](https://modelcontextprotocol.io) · [MCP registry](https://registry.modelcontextprotocol.io)
- Releases: [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog) · [protocol releases](https://github.com/modelcontextprotocol/modelcontextprotocol/releases)
- Companion skill: [gcloud](../gcloud/SKILL.md) (project and IAM context for managed servers).
