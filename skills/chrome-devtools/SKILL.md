---
name: chrome-devtools
description: "Debug Chrome with DevTools MCP or its CLI: console, network, performance, accessibility."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/chrome-devtools
  created: "2026-09-03"
  updated: "2026-11-14"
---

# Chrome DevTools

Live Chrome diagnostics via DevTools MCP or its CLI ([playwright](../playwright/SKILL.md) owns repeatable E2E journeys; [web-frontend](../web-frontend/SKILL.md) owns UI implementation).

## Setup

Requires Node.js LTS, `npm`/`npx`, and Chrome. Reuse an active MCP server if connected, default to the CLI below when none is configured (`dot` deploys none), or register MCP via [mcp-setup](../agent-harnesses/references/mcp-setup.md):

```bash
npx --yes chrome-devtools-mcp@1.13.0 --isolated --headless --no-usage-statistics --no-performance-crux --redact-network-headers
```

Keep debugging on loopback in a dedicated profile (pages, bodies, cookies, screenshots, and traces may hold sensitive data). Workstation sets `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1`; keep `--no-usage-statistics`, `--no-performance-crux`, and `--redact-network-headers` (`Cookie`, `Set-Cookie`, `Authorization`, `ETag`, `Content-Length` masked) on external hosts.

## CLI without MCP

1. **Run via pinned package**: `npm exec --yes --package=chrome-devtools-mcp@1.13.0 -- chrome-devtools <command>` (check `--help` and `start --help`).
1. **Respect running daemons**: check `status` first; never stop or hijack another task's daemon.
1. **Start scoped**: `start --workspace="$PWD" --no-usage-statistics --no-performance-crux` (auto-start on first tool call grants unrestricted file access).
1. **Tear down**: close task-owned pages and `stop` only daemons started by this task.

## Workflow

1. **Select target and snapshot**: pick the page ID and take a fresh snapshot before using element UIDs (navigation/rerenders invalidate them).
1. **Console and network**: list bounded console logs and failed requests first, fetching only needed request IDs/bodies.
1. **Performance and Lighthouse**: pass `filePath` to `performance_start_trace` / `performance_stop_trace` instead of dumping raw traces; `lighthouse_audit` checks a11y, SEO, and best practices (reloads unless `mode="snapshot"`; excludes performance).
1. **Memory**: `take_heapsnapshot` is enabled by default; `compare_heapsnapshots` and deeper analysis require `--memoryDebugging` on MCP.
1. **Clean up**: close task-owned pages after verification.

## Gotchas

- **Explicit browser mode**: pass headed/headless explicitly (the CLI defaults to headless + `--memoryDebugging`, which may differ from an MCP config).
- **Workspace write roots**: MCP file tools write only inside temp dirs, client MCP roots, or `--workspace=<dir>` (`is not within any of the configured workspace roots` otherwise).

## Official Skills

Upstream: `ChromeDevTools/chrome-devtools-mcp` (`chrome-devtools-cli`, `a11y-debugging`, `memory-leak-debugging` — preview only and never install colliding `chrome-devtools` per [vendor-skill policy](../agent-project/references/vendor-skills.md#name-collisions)).

## Documentation

- [Chrome DevTools for agents](https://github.com/ChromeDevTools/chrome-devtools-mcp) · [Tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md) · [CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md)
- Releases: [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp/releases)
- Companion skills: [mcp-setup](../agent-harnesses/references/mcp-setup.md), [playwright](../playwright/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [performance](../python-stack/references/performance.md).
