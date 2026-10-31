# Native MCP Host Commands

## Commands

One Python stdio example per host. For a remote server replace the trailing command with `--transport http <url>` (Claude Code, Copilot), `--url <url>` (OpenCode), or a plain URL argument (Antigravity):

```bash
agy mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>                 # Antigravity CLI; flags before <name>
claude mcp add --scope project <name> -e KEY=value -- uvx --from '<package>==<version>' <command> # -e is variadic: name first; default scope is local
copilot mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>             # user configuration
opencode mcp add --env KEY=value <name> -- uvx --from '<package>==<version>' <command>            # OpenCode 2.x: project configuration unless --global
```

`KEY=value` represents non-sensitive configuration. Do not place credentials in CLI arguments or committed MCP files; use the host's supported environment references, OAuth, or a scoped secret launcher.

Resolve `<version>` to a reviewed exact release and update it deliberately. This pins the top-level package only; transitive dependencies can still change when an environment is rebuilt. Use a reviewed locked environment and its executable when reproducible server startup is required.

OpenCode 2.x configuration nests servers under `mcp.servers.<name>`: `type: "local"` with a command array and an `environment` mapping, or `type: "remote"` with a `url`. Use `disabled`, not `enabled`, and `{env:NAME}` references for secrets; a project entry replaces the whole same-name global entry. See [OpenCode MCP docs](https://opencode.ai/v2/docs/mcp-servers/) before writing the matching configuration.

## Configuration files

| Host        | User scope                                           | Project scope                                   |
| ----------- | ---------------------------------------------------- | ----------------------------------------------- |
| Antigravity | `~/.gemini/config/mcp_config.json` (per its docs)    | `.agents/mcp_config.json` (per its docs)        |
| Claude Code | `~/.claude.json` (`--scope user` or default `local`) | `.mcp.json` (`--scope project`)                 |
| Copilot     | `~/.copilot/mcp-config.json`                         | `.mcp.json` or `.github/mcp.json` (hand-edited) |
| OpenCode    | `~/.config/opencode/opencode.json` or `.jsonc`       | `opencode.json` or `.jsonc`                     |
