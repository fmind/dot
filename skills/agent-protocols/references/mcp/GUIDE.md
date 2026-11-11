---
name: mcp
description: "MCP tool and context clients/servers, transports, schemas, and protocol tests."
---

# MCP

Build typed MCP tools, resources, prompts, and clients with the official `mcp` Python SDK. [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns project setup, [mcp-setup](../../../agent-harnesses/references/mcp-setup.md) owns host registration, and [A2A](../a2a.md) owns agent-to-agent tasks.

## Workflow

1. **Initialize and lock**: inspect the installed SDK before using APIs beyond quickstart.
   ```bash
   uv init --package <slug> && cd <slug>
   uv add "mcp[cli]" && uv add --dev pytest
   ```
1. **Define `MCPServer`** (`mcp.server`): type-hint and document every handler to generate accurate JSON Schemas. Prefix tool names by service, set `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`—hints never replace authz), paginate lists with cursor + total, and return actionable errors.
1. **Select transport**: stdio for local child processes (stdout protocol-only, logs to stderr) or Streamable HTTP at `/mcp` for hosted services:
   ```bash
   uv run mcp run src/<package>/server.py:server
   uv run mcp run src/<package>/server.py:server --transport streamable-http
   ```
1. **Test in-process and over stdio**: adapt [test_protocol.py](templates/test_protocol.py) using `Client(server)` plus one `Client(StdioServerParameters(...))` subprocess test covering schemas, valid outputs, and bad inputs; before release, evaluate ~10 multi-tool read-only questions per [agent-evaluation](../../../agent-evaluation/SKILL.md).
   ```bash
   uv run pytest -q
   ```
1. **Harden HTTP**: check `Origin`, bind dev servers to `127.0.0.1`, enforce OAuth or workload identity remotely, and authorize each call against caller and resource.
1. **Build clients**: `async with Client(<approved-url-or-stdio-params>) as client` (plain `mcp` suffices without `[cli]`); bound timeouts and output size, and test unknown tools, bad args, cancellation, and transport errors.
1. **Ship**: package with [containerize](../../../docker/references/containerize/GUIDE.md), deploy via [cloud-run](../../../cloud-run/SKILL.md), register via [mcp-setup](../../../agent-harnesses/references/mcp-setup.md), and verify a live call.

## Gotchas

- **Target SDK v2**: use `MCPServer` and `Client`; migrate v1 `mcp.server.fastmcp.FastMCP` via the [v2 migration guide](https://py.sdk.modelcontextprotocol.io/v2/migration/) (pin `<2` only for legacy maintenance; third-party `fastmcp` is separate).
- **Stateless Streamable HTTP**: never build new HTTP+SSE servers or rely on in-memory sessions across restarts/replicas. Spec 2026-07-28 (SDK 2.3.0) drops sessions and `initialize` (`Client` falls back for older peers) and deprecates Roots, Sampling, Logging, and DCR—pass server-minted state handles in tool args, log via stderr/OTel, and use Client ID Metadata Documents for OAuth.
- **Propagate cancellation and bound outputs**: cancel downstream I/O on client disconnect/cancel, strip secrets from errors, cap payload size, and attach provenance to factual results.

## Official Skills

Vet `anthropics/skills` (`mcp-builder`) or Claude Code's `mcp-server-dev` plugin in `anthropics/claude-plugins-official` (`build-mcp-server`, `build-mcp-app`, `build-mcpb`) per [vendor-skill policy](../../../agent-project/references/vendor-skills.md) (`modelcontextprotocol/python-sdk` has contributor docs only), verifying samples against SDK v2.

## Documentation

- [MCP specification](https://modelcontextprotocol.io/specification/latest) · [Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [Python SDK docs](https://py.sdk.modelcontextprotocol.io/)
- Releases: [Python SDK](https://github.com/modelcontextprotocol/python-sdk/releases) · [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog)
- Adapted from [anthropics/skills mcp-builder](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/mcp-builder/SKILL.md) (Apache-2.0; Python sample still uses v1 `FastMCP`).
- Companion skills: [mcp-setup](../../../agent-harnesses/references/mcp-setup.md), [python-stack](../../../python-stack/references/foundation/GUIDE.md), [containerize](../../../docker/references/containerize/GUIDE.md), [cloud-run](../../../cloud-run/SKILL.md).
