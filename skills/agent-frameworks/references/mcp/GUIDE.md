---
name: mcp
description: "MCP tool and context clients/servers, transports, schemas, and protocol tests."
---

# MCP

Build typed MCP tools, resources, prompts, and clients with the official `mcp` Python SDK. [python/foundation](../../../python/references/foundation/GUIDE.md) owns project setup, [mcp-setup](../../../agent-harnesses/references/mcp-setup.md) owns host registration, and [A2A](../a2a.md) owns agent-to-agent tasks.

## Workflow

1. **Initialize and lock**: start from [Python foundation](../../../python/references/foundation/references/bootstrap.md), install the lean SDK (includes `uvicorn`, `starlette`, `httpx2`, `pyjwt[crypto]`), and inspect installed APIs beyond quickstart:
   ```bash
   UV_MALWARE_CHECK=1 uv add --preview-features malware-check "mcp>=2.3.0"
   ```
   Copy [server.py](templates/server.py) to `src/<package>/server.py` (re-export `main` in `__init__.py`, add `patch = ["subprocess"]` under `[tool.coverage.run]`, and declare `[project.scripts]` `<slug> = "<package>:main"`).
1. **Define `MCPServer`** (`mcp.server`): type-hint and document every handler to generate accurate JSON Schemas. Prefix tool names by service (`<package>_<tool>`), set `ToolAnnotations` (`read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint`—hints never replace authz), paginate lists with cursor + total, and return actionable errors.
1. **Select transport**: stdio for local child processes (stdout protocol-only, logs to stderr) or stateless Streamable HTTP at `/mcp` for hosted services (`HOST`/`PORT` or `--host`/`--port`):
   ```bash
   uv run --locked python -m <package>
   uv run --locked <slug> --transport streamable-http --host 127.0.0.1 --port 8000
   ```
1. **Test in-process and over stdio**: adapt [test_protocol.py](templates/test_protocol.py) using `Client(server)` plus one unmocked `Client(StdioServerParameters(command=sys.executable, args=["-m", "<package>"]))` subprocess test covering schemas, valid outputs, and bad inputs; before release, evaluate ~10 multi-tool read-only questions per [evaluation](../evaluation/GUIDE.md).
   ```bash
   uv run --locked pytest -q
   ```
1. **Harden HTTP**: check `Origin`, bind dev servers to `127.0.0.1`, enforce OAuth or workload identity remotely, and authorize each call against caller and resource.
1. **Build clients**: `async with Client(<approved-url-or-stdio-params>) as client`; bound timeouts and output size, and test unknown tools, bad args, cancellation, and transport errors.
1. **Ship**: package with [containerize](../../../containers/references/containerize/GUIDE.md), deploy via [cloud-run](../../../gcloud/references/cloud-run/GUIDE.md), register via [mcp-setup](../../../agent-harnesses/references/mcp-setup.md), and verify a live call.

## Gotchas

- **Target SDK v2**: use `MCPServer` and `Client`; migrate v1 `mcp.server.fastmcp.FastMCP` via the [v2 migration guide](https://py.sdk.modelcontextprotocol.io/v2/migration/) (pin `<2` only for legacy maintenance; third-party `fastmcp` is separate).
- **Stateless Streamable HTTP**: never build new HTTP+SSE servers or rely on in-memory sessions across restarts/replicas. Spec 2026-07-28 (SDK 2.3.0) drops sessions/`initialize` (`Client` falls back on legacy peers) and deprecates Roots, Sampling, Logging, and DCR—use server-minted state args, stderr/OTel logs, and Client ID Metadata Documents for OAuth.
- **Propagate cancellation and bound outputs**: cancel downstream I/O on client disconnect/cancel, strip secrets from errors, cap payload size, and attach provenance to factual results.

## Official Skills

Vet `anthropics/skills` (`mcp-builder`) or `anthropics/claude-plugins-official` `mcp-server-dev` per [vendor-skill policy](../../../agent-harnesses/references/vendor-skills.md) (`python-sdk` has contributor docs only); verify samples against SDK v2.

## Documentation

- [MCP specification](https://modelcontextprotocol.io/specification/latest) · [Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [Python SDK docs](https://py.sdk.modelcontextprotocol.io/)
- Releases: [Python SDK](https://github.com/modelcontextprotocol/python-sdk/releases) · [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog)
- Adapted from [mcp-builder](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/mcp-builder/SKILL.md) (Apache-2.0; sample uses v1 `FastMCP`).
- Companion skills: [mcp-setup](../../../agent-harnesses/references/mcp-setup.md), [python/foundation](../../../python/references/foundation/GUIDE.md), [containerize](../../../containers/references/containerize/GUIDE.md), [cloud-run](../../../gcloud/references/cloud-run/GUIDE.md).
