---
name: mcp-setup
description: "Add, vet, or fix MCP servers across coding hosts and verify live access."
---

# MCP Setup

Register only the MCP capability a task needs using the host's native CLI. [MCP](../../agent-frameworks/references/mcp/GUIDE.md) owns server code; [project-setup](project-setup.md) owns shared repo layout.

## Workflow

1. **Prefer CLIs and skills**: add an MCP server only when no CLI/skill covers the capability or the host requires MCP.
1. **Vet before registering**: audit source, transport, tools, auth flow, and permissions, then register via the host CLI below.
1. **Verify live**: list the server, inspect exposed tools, and run one bounded read-only call.

## Native host commands

Python stdio examples (for HTTP, pass a bare URL in Antigravity or `--transport http <url>` in Copilot):

```bash
agy mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>      # Antigravity: user scope only; flags must precede <name>
copilot mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>  # Copilot: user configuration
```

- **Pin executables & local projects**: use `uvx --from '<package>==<version>'`, never bare `uvx <package>`. For local Python checkouts, point directly at the locked `.venv` binary (e.g., `agy mcp add brain -- <brain-checkout>/.venv/bin/bf mcp --brain <brain>`) because `uvx --from` pins only the top-level package and agy spawns `bash -c` without shell init files.
- **Keep secrets out of args and tracked files**: `KEY=value` is non-sensitive only; supply credentials via host env refs (`${NAME}`), OAuth, or `with-secret` ([scoped credentials](../../dot-cli/references/authentication.md#scoped-credentials)).
- **Antigravity transport & auth**: remote servers require Streamable HTTP (`serverUrl` or `url`; no legacy SSE/`httpUrl`), with OAuth 2.0 PKCE supporting CIMD (`https://antigravity.google/oauth/client-metadata.json`), DCR, or manual `oauth` (`https://antigravity.google/oauth-callback`), `authProviderType: "google_credentials"` for GCP ADC, and `1.5.9+` stripping custom `headers` on cross-origin redirects. Avoid duplicate server names across global/workspace files (the running server wins).
- **Antigravity tool loading & timeouts**: tools lazy-load by default (schemas cached in `~/.gemini/antigravity-cli/mcp/<server>/`); set `tools.<name>.eager: true` for hot tools (`1.5.8+` enforces `mcp(...)` deny/ask rules on eager tools too), `background: "always"|"off"`, `enabledTools`/`disabledTools`, or `timeoutSeconds` (default 180s call / 300s connect; `-1` disables both).

## Configuration files

| Host        | User scope                                         | Project scope                                              |
| ----------- | -------------------------------------------------- | ---------------------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (`agy mcp add`) | `.agents/mcp_config.json` (hand-edited; CLI add user-only) |
| Copilot     | `~/.copilot/mcp-config.json`                       | `.mcp.json` or `.github/mcp.json` (hand-edited)            |

## Gotchas

- **Hold the trust boundary**: vet repo MCP configs before launching, restrict exposed tools (`copilot mcp add --tools`), and gate out-of-scope remote writes.

## Documentation

- [Model Context Protocol](https://modelcontextprotocol.io) · [MCP registry](https://registry.modelcontextprotocol.io) · [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog) · [protocol releases](https://github.com/modelcontextprotocol/modelcontextprotocol/releases)
- Google Cloud managed MCP: [supported products](https://docs.cloud.google.com/mcp/supported-products) · [authentication](https://docs.cloud.google.com/mcp/authenticate-mcp), scoping IAM via [gcloud](../../gcloud/SKILL.md) (enabling the product API suffices; no separate MCP enablement, and local ADC support varies by host).
