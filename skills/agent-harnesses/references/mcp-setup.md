---
name: mcp-setup
description: "Add, vet, or fix MCP servers across coding hosts and verify live access."
---

# MCP Setup

Register only the MCP capability a task needs using the host's native CLI. [MCP](../../agent-protocols/references/mcp/GUIDE.md) owns server code; [agent-project](../../agent-project/SKILL.md) owns shared repo layout.

## Workflow

1. **Prefer CLIs and skills**: add an MCP server only when no CLI/skill covers the capability or the host requires MCP.
1. **Vet before registering**: audit source, transport, tools, auth flow, and permissions, then register via the host CLI below.
1. **Verify live**: list the server, inspect exposed tools, and run one bounded read-only call.

## Native host commands

Python stdio examples (for HTTP, substitute `--transport http <url>` in Claude/Copilot, `--url <url>` in OpenCode/Pi, or a bare URL in Antigravity; Pi HTTP bearer tokens use `--bearer-token-env-var NAME`):

```bash
agy mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>                 # Antigravity: user scope only
claude mcp add --scope project <name> -e KEY=value -- uvx --from '<package>==<version>' <command> # -e is variadic: name first
copilot mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>             # user configuration
opencode mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>            # project config unless --global
pi mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>                  # user config unless -l
```

- **Pin executables & local projects**: use `uvx --from '<package>==<version>'`, never bare `uvx <package>`. For local Python checkouts, point directly at the locked `.venv` binary (e.g., `agy mcp add brain -- <brain-checkout>/.venv/bin/bf mcp --brain <brain>`) because `uvx --from` pins only the top-level package and agy spawns `bash -c` without shell init files.
- **Keep secrets out of args and tracked files**: `KEY=value` is non-sensitive only; supply credentials via host env refs (`{env:NAME}`, `${NAME}`, `--bearer-token-env-var`), OAuth, or `dot secret run`. Keep Claude's default `--scope local` (`~/.claude.json`) unless the user approves shared `.mcp.json` (`--scope project`; `claude mcp reset-project-choices` resets).
- **OpenCode 2.x schema** ([docs](https://opencode.ai/v2/docs/mcp-servers/)): nest under `mcp.servers.<name>` (`type: "local"` with command array + `environment`, or `type: "remote"` with `url`); use `disabled` (not `enabled`) and `{env:NAME}` for secrets. Project entries replace same-name global entries wholesale.

## Configuration files

| Host        | User scope                                           | Project scope                                   |
| ----------- | ---------------------------------------------------- | ----------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (`agy mcp add`)   | Unsupported by `agy mcp add` (user-only)        |
| Claude Code | `~/.claude.json` (`--scope user` or default `local`) | `.mcp.json` (`--scope project`)                 |
| Copilot     | `~/.copilot/mcp-config.json`                         | `.mcp.json` or `.github/mcp.json` (hand-edited) |
| OpenCode    | `~/.config/opencode/opencode.json` or `.jsonc`       | `opencode.json` or `.jsonc`                     |
| Pi          | `~/.pi/agent/mcp.json`                               | `.pi/mcp.json` (`-l`), after project trust      |

## Gotchas

- **Hold the trust boundary**: vet repo MCP configs before launching, restrict exposed tools (`copilot mcp add --tools`), and gate out-of-scope remote writes.

## Documentation

- [Model Context Protocol](https://modelcontextprotocol.io) · [MCP registry](https://registry.modelcontextprotocol.io) · [specification changelog](https://modelcontextprotocol.io/specification/latest/changelog) · [protocol releases](https://github.com/modelcontextprotocol/modelcontextprotocol/releases)
- Google Cloud managed MCP: [supported products](https://docs.cloud.google.com/mcp/supported-products) · [authentication](https://docs.cloud.google.com/mcp/authenticate-mcp), scoping IAM via [gcloud](../../gcloud/SKILL.md) (enabling the product API suffices; no separate MCP enablement, and local ADC support varies by host).
