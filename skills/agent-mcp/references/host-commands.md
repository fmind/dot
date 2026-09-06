# Native MCP Host Commands

## Commands

One stdio example per host. For a remote server replace the trailing command with `--transport http <url>` (Claude Code, Copilot, Grok), `--url <url>` (Codex, OpenCode), or a plain URL argument (Antigravity):

```bash
agy mcp add --env KEY=value <name> -- npx -y <package>                   # Antigravity CLI; flags before <name>
claude mcp add --scope project -e KEY=value <name> -- npx -y <package>   # default scope is local, not project
codex mcp add <name> --env KEY=value -- npx -y <package>                 # no scope flag: writes ~/.codex/config.toml
copilot mcp add --env KEY=value <name> -- npx -y <package>               # user configuration
grok mcp add --scope project -e KEY=value <name> -- npx -y <package>     # --scope user is the default
opencode mcp add <name> --env KEY=value                                  # prompts for the remaining fields
```

## Configuration files

| Host        | User scope                                           | Project scope                                        |
| ----------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (per its docs)    | `.agents/mcp_config.json` (per its docs)             |
| Claude Code | `~/.claude.json` (`--scope user` or default `local`) | `.mcp.json` (`--scope project`)                      |
| Codex       | `~/.codex/config.toml` under `[mcp_servers.<name>]`  | `.codex/config.toml` (trusted projects, hand-edited) |
| Copilot     | `~/.copilot/mcp-config.json`                         | `.mcp.json` or `.github/mcp.json` (hand-edited)      |
| Grok        | `~/.grok/config.toml`                                | `./.grok/config.toml`                                |
| OpenCode    | `~/.config/opencode/opencode.json` under `"mcp"`     | `opencode.json` under `"mcp"`                        |
