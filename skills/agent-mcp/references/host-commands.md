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

## Configuration files

| Host        | User scope                                           | Project scope                                        |
| ----------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (per its docs)    | `.agents/mcp_config.json` (per its docs)             |
| Claude Code | `~/.claude.json` (`--scope user` or default `local`) | `.mcp.json` (`--scope project`)                      |
| Codex       | `~/.codex/config.toml` under `[mcp_servers.<name>]`  | `.codex/config.toml` (trusted projects, hand-edited) |
| Copilot     | `~/.copilot/mcp-config.json`                         | `.mcp.json` or `.github/mcp.json` (hand-edited)      |
| Grok        | `~/.grok/config.toml`                                | `./.grok/config.toml`                                |
