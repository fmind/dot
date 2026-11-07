---
name: chrome-devtools
description: "Debug Chrome with DevTools MCP or its CLI: console, network, performance, accessibility."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/chrome-devtools
  created: "2026-09-03"
  updated: "2026-11-07"
---

# Chrome DevTools

Use Chrome DevTools MCP or its CLI for live browser diagnostics. [playwright](../playwright/SKILL.md) owns repeatable end-to-end journeys; [web-frontend](../web-frontend/SKILL.md) owns platform implementation guidance.

## Setup

Require Node.js LTS, `npm`/`npx`, and supported Chrome. dot deploys no DevTools MCP server: reuse a connected one, use the CLI below when none is connected, and add the server with [mcp-setup](../mcp-setup/SKILL.md) only when a harness needs it. The launch command below uses a reviewed package pin; recheck installed help before updating it.

```bash
npx --yes chrome-devtools-mcp@1.12.0 --isolated --headless --no-usage-statistics --no-performance-crux --redact-network-headers
```

The MCP client starts that process over stdio. Use a dedicated browser profile. Keep remote debugging on loopback; browser content, network bodies, cookies, screenshots, and traces may expose private data. The two opt-out flags disable MCP usage statistics and CrUX URL lookups respectively. `--redact-network-headers` replaces every header outside DevTools' allowlist with `<redacted>`, including `Cookie`, `Set-Cookie`, `Authorization`, `ETag`, and `Content-Length`; omit it only from a session that must read those headers.

## CLI without MCP

The same package exposes the `chrome-devtools` shell command, a client to a persistent background daemon. It is the default path when no DevTools MCP is connected.

1. **Resolve the command**: run `npm exec --yes --package=chrome-devtools-mcp@1.12.0 -- chrome-devtools <command>`; read `chrome-devtools --help` and `start --help` for the installed commands and flags.
1. **Check before starting**: inspect `status` first; do not stop or repurpose another task's daemon.
1. **Start the task's session explicitly**: `start --workspace="$PWD" --no-usage-statistics --no-performance-crux`. Otherwise the first tool call starts the daemon automatically with unrestricted file access.
1. **Clean up**: close task-owned pages and `stop` only a daemon created for this task.

## Workflow

1. **Identify the target**: list pages and select the intended page ID. Take a fresh snapshot before using element UIDs; navigation and rerenders invalidate them.
1. **Inspect console and network**: list bounded console messages and failed-request metadata, then fetch only the relevant request IDs and bodies.
1. **Trace performance**: `performance_start_trace` and `performance_stop_trace` take a `filePath`; save large traces as files instead of returning their raw contents.
1. **Audit accessibility**: `lighthouse_audit` covers accessibility, SEO, and best practices; it reloads the page unless `mode` is `snapshot`, and it excludes performance, which needs a trace.
1. **Analyze memory**: `take_heapsnapshot` is on by default, while `compare_heapsnapshots` and the other analysis tools need `--memoryDebugging` on the MCP server.
1. **Close task-owned pages**: after verifying the fix.

## Gotchas

- **Pin the browser mode**: set headed or headless explicitly for reproducibility; the CLI defaults to headless and enables `--memoryDebugging`, which need not match a separately configured MCP connection.
- **Save artifacts inside allowed roots**: MCP file tools write only under the OS temp directory, the client's MCP roots, and `--workspace` directories; other paths fail with `is not within any of the configured workspace roots`. Add `--workspace=<dir>` to the launch command for the authorized artifact directory, or save to the temp directory and move the file.

## Official Skills

Upstream: [ChromeDevTools/chrome-devtools-mcp skills](https://github.com/ChromeDevTools/chrome-devtools-mcp/tree/main/skills), including `chrome-devtools-cli` for the CLI. Use `DISABLE_TELEMETRY=1 skills add ChromeDevTools/chrome-devtools-mcp --list`, then follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) for the required guidance. Select task-specific entries such as `a11y-debugging` or `memory-leak-debugging`; preview the same-name `chrome-devtools` entry (also in `github/awesome-copilot`) instead of installing it ([vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)).

## Documentation

- [Chrome DevTools for agents](https://github.com/ChromeDevTools/chrome-devtools-mcp) · [Tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md) · [CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md)
- Releases: [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp/releases)
- Companion skills: [mcp-setup](../mcp-setup/SKILL.md), [playwright](../playwright/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [performance](../python-stack/references/performance.md).
