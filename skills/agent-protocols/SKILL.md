---
name: agent-protocols
description: "Implement A2A agents, MCP servers, and ACP editor integrations in Python."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-protocols
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Agent Protocols

Implement the protocol required by the peers: A2A exchanges agent tasks, MCP exposes tools and context, and ACP connects editor/client frontends to agents.

## Workflow

1. **Read only the matching guide** below; [mcp-setup](../agent-harnesses/references/mcp-setup.md) owns registering existing MCP servers in coding hosts.
1. **Vet vendor skills**: install only project-scoped selections from each guide's official-skill section per [vendor policy](../agent-project/references/vendor-skills.md) (protocol capability descriptors named `skill` are not Agent Skills).

## Task guides

<!-- guides:start -->

- [a2a](references/a2a.md): A2A clients, servers, Agent Cards, task lifecycle, and official guidance.
- [acp](references/acp.md): ACP editor-agent sessions, capability negotiation, streaming, and permission handling.
- [mcp](references/mcp/GUIDE.md): MCP tool and context clients/servers, transports, schemas, and protocol tests.

<!-- guides:end -->
