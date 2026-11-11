---
name: acp
description: "ACP editor-agent sessions, capability negotiation, streaming, and permission handling."
---

# Agent Client Protocol

Connect an editor or client frontend to an agent process via Agent Client Protocol (confirm the spec when another product reuses the `ACP` acronym).

## Python implementation

1. **Pin the SDK**: inspect peer protocol versions and add `uv add agent-client-protocol` (`agentclientprotocol/python-sdk`) when needed.
1. **Use SDK bases and schemas**: adapt official client/echo-agent examples using async base classes and generated `acp.schema` models rather than raw JSON-RPC dicts.
1. **Negotiate capabilities first**: open a session before prompting; handle streamed updates, tool calls, cancellations, and permission prompts bounded strictly by the user's granted authority.
1. **Isolate stdio and subprocesses**: reserve stdout for protocol frames (logs to stderr); spawn only approved executables with explicit argv, cwd, and env, tearing them down on completion, cancel, or error.
1. **Test deterministically**: cover normal turns, denied permissions, cancellation, unexpected child exit, and only advertised optional capabilities.

## Boundaries

- **Default to stdio**: adopt remote transport extras only when both peers require them and the locked SDK's security posture is verified.
- **Keep protocols distinct**: ACP neither replaces A2A tasks nor wraps MCP tool servers into editor agents without a real interop need.
- **Skip contributor files**: `agentclientprotocol` contributor `AGENTS.md` is not a consumer skill—use SDK docs and examples unless an official consumer skill ships.

## Documentation

- [Protocol architecture](https://agentclientprotocol.com/get-started/architecture) · [Official Python library](https://agentclientprotocol.com/libraries/python)
- [Python SDK and examples](https://github.com/agentclientprotocol/python-sdk) · [SDK documentation](https://agentclientprotocol.github.io/python-sdk/)
- Releases: [Python SDK](https://github.com/agentclientprotocol/python-sdk/releases)
