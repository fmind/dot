---
name: cli
description: "Drive DevTools from the shell with the chrome-devtools CLI daemon instead of an MCP connection."
---

# Chrome DevTools CLI

The `chrome-devtools-mcp` package also exposes the experimental `chrome-devtools` shell command. Use the same reviewed pin as the MCP launch command, and follow the parent workflow for diagnosis.

1. **Resolve the command**: run `npm exec --yes --package=chrome-devtools-mcp@1.10.1 -- chrome-devtools <command>`; read `chrome-devtools --help` and `start --help` for the installed commands and flags.
1. **Check before starting**: inspect `status` first; do not stop or repurpose another task's daemon.
1. **Start the task's session explicitly**: `start --workspace="$PWD" --no-usage-statistics --no-performance-crux`. Otherwise the CLI starts a persistent daemon automatically and enables unrestricted file access by default.
1. **Clean up**: close task-owned pages and `stop` only a daemon created for this task.

## Gotchas

- **CLI defaults differ from MCP**: the CLI starts headless and enables `--memoryDebugging`, unlike a default MCP connection; set the browser mode explicitly when comparing runs.

## Documentation

- [CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md) · upstream `chrome-devtools-cli` skill under the parent's vendor-skill policy.
