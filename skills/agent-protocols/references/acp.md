---
name: acp
description: "ACP editor-agent sessions, capability negotiation, streamed updates, and permission handling."
---

# Agent Client Protocol

Use ACP for integration between an editor or other client and an agent process. Here ACP means Agent Client Protocol; confirm the intended specification when another product uses the same acronym.

## Python implementation

1. Inspect the peers' protocol versions and the installed SDK. Use the official `agentclientprotocol/python-sdk` distribution `agent-client-protocol`; add it with `uv add agent-client-protocol` only when the project needs it.
1. Start from the SDK's matching client and echo-agent examples. Implement the required role through its async bases and generated `acp.schema` models rather than hand-writing JSON-RPC envelopes.
1. Negotiate capabilities and establish a session before prompting. Handle streamed session updates, tool calls, permission requests, and cancellation according to the negotiated schema. A client permission response must reflect the user's existing authority; never automatically approve a broader operation.
1. Keep stdout protocol-only for stdio and diagnostics on stderr. Launch only an approved executable with explicit arguments, working directory, and environment; tear down the process on completion, cancellation, and failure.
1. Test a local deterministic client/agent exchange: initialization, session creation, prompt completion, streamed updates, denied permissions, cancellation, malformed input, and unexpected subprocess exit. Test only advertised optional capabilities.

## Boundaries

- Start with stdio unless both peers require a documented remote transport. The Python SDK's remote transport extras have their own maturity and security requirements; verify the locked release before exposing a service.
- ACP sessions are not A2A tasks and do not turn an MCP tool server into an editor agent. Choose an adapter only for a demonstrated interoperability requirement.
- For official skills, inspect the maintainer's current repository and distribution before installing anything. Contributor `AGENTS.md` is not a consumer skill package; fall back to the official SDK examples and docs when no applicable package is established.

## Documentation

- [Protocol architecture](https://agentclientprotocol.com/get-started/architecture) · [Official Python library](https://agentclientprotocol.com/libraries/python)
- [Python SDK and examples](https://github.com/agentclientprotocol/python-sdk) · [SDK documentation](https://agentclientprotocol.github.io/python-sdk/)
- Releases: [Python SDK](https://github.com/agentclientprotocol/python-sdk/releases)
