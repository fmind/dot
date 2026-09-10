---
name: mcp-server
description: Build Python MCP servers and clients with the official SDK. Use for tools, resources, prompts, stdio or Streamable HTTP transport, and protocol tests.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mcp-server
  created: "2026-09-03"
  updated: "2026-09-10"
---

# MCP Server

Use the official `mcp` Python SDK for typed tools, resources, prompts, and consuming clients. [python-stack](../python-stack/SKILL.md) owns shared setup; [agent-mcp](../agent-mcp/SKILL.md) owns host registration and [a2a-python-sdk](../a2a-python-sdk/SKILL.md) owns agent interoperability.

## Workflow

1. **Create the project** and lock the current stable SDK. Read the installed package before using APIs beyond the official quickstart.
   ```bash
   uv init --package <slug>
   cd <slug>
   uv add "mcp[cli]"
   uv add --dev pytest
   ```
1. **Define the surface** with `MCPServer` from `mcp.server`. Give each decorated function complete type hints and a useful docstring so its JSON Schema and purpose come from the implementation.
1. **Keep tools narrow**: parse external input at the function boundary, return structured values, apply time and size limits, and expose only the files, hosts, and operations named by the tool.
1. **Choose the transport**: stdio for a local host-launched process; Streamable HTTP at `/mcp` for a service. Keep stdout protocol-only under stdio and send logs to stderr.
   ```bash
   uv run mcp run server.py
   uv run mcp run server.py --transport streamable-http
   ```
1. **Test both boundaries**: use `Client(server)` for deterministic handler tests, then `Client(StdioServerParameters(...))` for one real subprocess protocol smoke. Adapt the [protocol test](references/test_protocol.py) to assert every tool schema, representative outputs, and invalid input.
   ```bash
   uv run pytest -q
   ```
1. **Secure HTTP before exposure**: validate `Origin`, bind local development to `127.0.0.1`, require OAuth or workload identity remotely, and authorize each tool against the caller and requested resource.
1. **Consume an existing server**: use `async with Client(<approved-url-or-stdio-parameters>) as client`, inspect advertised schemas, and call only requested tools/resources. Bound call duration and output; test an unknown tool, invalid arguments, cancellation, and transport failure. A client-only project can install plain `mcp` without the CLI extra.
1. **Ship and verify**: containerize a hosted server with [containerize](../containerize/SKILL.md), deploy with [cloud-run](../cloud-run/SKILL.md), register it through [agent-mcp](../agent-mcp/SKILL.md), then make one real tool call end to end.

## Gotchas

- **Use SDK v2 APIs**: `MCPServer` and `Client` are the current stable surface; pin `<2` only while maintaining an intentional v1 application.
- **Streamable HTTP replaced HTTP+SSE**: do not build a new SSE server, and do not depend on in-memory protocol sessions when instances can scale or restart.
- **Cancellation is work cancellation**: stop downstream I/O when the client disconnects or cancels rather than letting detached work continue.
- **Tool output is untrusted too**: bound it, avoid secret-bearing errors, and return citations or provenance when a tool supplies facts to a model.

## Official Skills

Upstream: `anthropics/skills`, an official Anthropic bundle with MCP builder guidance, not a skill release from the Python SDK maintainers. The inspected `modelcontextprotocol/python-sdk` tree has contributor test guidance rather than a consumer SDK skill. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md), then verify the selected Python guidance against the project's locked SDK API.

## Documentation

- [MCP specification](https://modelcontextprotocol.io/specification/latest) · [Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [Python SDK docs](https://py.sdk.modelcontextprotocol.io/)
- Companion skills: [agent-mcp](../agent-mcp/SKILL.md) (host registration), [python-stack](../python-stack/SKILL.md), [containerize](../containerize/SKILL.md), [cloud-run](../cloud-run/SKILL.md).
