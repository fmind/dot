---
name: agent-protocols
description: "Implement A2A agents, MCP servers, and ACP editor integrations in Python."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-protocols
  created: "2026-09-16"
  updated: "2026-10-07"
---

# Agent Protocols

Connect agents and tools through the protocol required by the peers. A2A exchanges agent tasks, MCP exposes tools and context, and ACP connects agent clients such as editors to agents; these protocols are not interchangeable.

## Workflow

1. **Read only the needed guide**: read only the A2A, MCP, or ACP guide needed below. Use [mcp-setup](../mcp-setup/SKILL.md) for registering an existing MCP server in a host; registration is separate from implementing a client or server.
1. **Vet vendor skills through policy**: take vendor skills only from each guide's official-skill guidance, reviewed through the [vendor policy](../agent-project/references/vendor-skills.md) and installed project-scoped. A protocol capability named skill is not an installable Agent Skill.

## Task guides

<!-- guides:start -->

- [a2a](references/a2a.md): A2A clients, servers, Agent Cards, task lifecycle, and official guidance.
- [acp](references/acp.md): ACP editor-agent sessions, capability negotiation, streamed updates, and permission handling.
- [mcp](references/mcp/GUIDE.md): MCP tool and context clients/servers, transports, schemas, and protocol tests.

<!-- guides:end -->
