# Native MCP Host Commands

## Commands

One Python stdio example per host. For a remote server replace the trailing command with `--transport http <url>` (Claude Code, Copilot, Grok), `--url <url>` (Codex), or a plain URL argument (Antigravity):

```bash
agy mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>                 # Antigravity CLI; flags before <name>
claude mcp add --scope project -e KEY=value <name> -- uvx --from '<package>==<version>' <command> # default scope is local, not project
codex mcp add <name> --env KEY=value -- uvx --from '<package>==<version>' <command>               # no scope flag: writes ~/.codex/config.toml
copilot mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>             # user configuration
grok mcp add --scope project -e KEY=value <name> -- uvx --from '<package>==<version>' <command>   # --scope user is the default
```

Resolve `<version>` to a reviewed exact release; update it deliberately rather than letting each agent start execute newly published code.

OpenCode uses `opencode mcp add <name>` for its setup interface; inspect `--help` for non-interactive URL and environment options. For a local server, the project config uses `mcp.<name>` with `type: "local"`, a command array, and an `environment` mapping; for remote servers use `type: "remote"` and a URL. See [OpenCode MCP docs](https://opencode.ai/docs/mcp-servers/) before writing the matching configuration.

## Configuration files

Cursor's installed CLI manages existing registrations rather than offering `mcp add`. Inspect `cursor-agent mcp --help`, then merge the reviewed server into `mcpServers` in the selected JSON file below. A local entry uses `command`, `args`, and optional `env`; remote configuration follows [Cursor MCP documentation](https://cursor.com/docs/context/mcp). Preserve unrelated entries and supported secret references. `cursor-agent mcp enable <identifier>` changes approval, and `login` performs authentication; listing status or tools can start or connect to servers, so review their configuration first. Verify with `list` and `list-tools <identifier>` after configuration. [cursor](../../agent-harnesses/references/cursor/GUIDE.md) owns session operation.

| Host        | User scope                                           | Project scope                                        |
| ----------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (per its docs)    | `.agents/mcp_config.json` (per its docs)             |
| Claude Code | `~/.claude.json` (`--scope user` or default `local`) | `.mcp.json` (`--scope project`)                      |
| Codex       | `~/.codex/config.toml` under `[mcp_servers.<name>]`  | `.codex/config.toml` (trusted projects, hand-edited) |
| Copilot     | `~/.copilot/mcp-config.json`                         | `.mcp.json` or `.github/mcp.json` (hand-edited)      |
| Cursor | `~/.cursor/mcp.json` | `.cursor/mcp.json` |
| OpenCode | `~/.config/opencode/opencode.json` or `.jsonc` | `opencode.json` or `.jsonc` |
| Grok        | `~/.grok/config.toml`                                | `./.grok/config.toml`                                |
