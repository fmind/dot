---
name: chrome-devtools
description: "Inspect, debug, and automate Chrome via the Chrome DevTools MCP server and CLI: performance, accessibility, cookies, and memory. Use for live browser debugging and audits."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/chrome-devtools
  created: "2026-09-03"
  updated: "2026-09-11"
---

# Chrome DevTools

Use Chrome DevTools MCP or its experimental CLI for live browser diagnostics. [playwright](../playwright/SKILL.md) owns repeatable end-to-end journeys; [modern-web](../modern-web/SKILL.md) owns platform implementation guidance.

## Setup

Require Node.js LTS, `npm`/`npx`, and supported Chrome. Reuse an available DevTools connection; otherwise follow [agent-mcp](../agent-mcp/SKILL.md) for the active harness. The launch command below uses a reviewed package pin; recheck installed help before updating it.

```bash
npx --yes chrome-devtools-mcp@1.9.0 --isolated --headless --no-usage-statistics --no-performance-crux
```

The MCP client starts that process over stdio. Use a dedicated browser profile. Keep remote debugging on loopback; browser content, network bodies, cookies, screenshots, and traces may expose private data. The two opt-out flags disable MCP usage statistics and CrUX URL lookups respectively.

For shell workflows, the same package exposes `chrome-devtools`; resolve it with `npm exec --yes --package=chrome-devtools-mcp@1.9.0 -- chrome-devtools <command>`. Inspect `status` before starting a daemon, then explicitly start the task's session with `start --workspace="$PWD" --no-usage-statistics --no-performance-crux`. The CLI otherwise starts a persistent daemon automatically and enables unrestricted file access by default. Read `start --help` for the installed flags; do not stop or repurpose another task's daemon.

## Workflow

1. **Identify the target**: list pages and select the intended page ID, URL, viewport, and browser mode. Take a fresh accessibility snapshot before using element UIDs; navigation and rerenders can invalidate them.
1. **Reproduce the symptom**: capture console errors and relevant failed requests, then reduce to the smallest repeatable action. Redact credentials and private request data from artifacts.
1. **Measure performance**: record a bounded trace of the same action before and after a change; preserve CPU/network throttling, cache conditions, viewport, and tool versions. Stop traces you started and save artifacts in the authorized workspace.
1. **Check accessibility**: inspect roles, names, focus order, keyboard operation, and visible contrast. Combine automated checks with manual interaction; an accessibility tree or Lighthouse score alone does not establish WCAG conformance.
1. **Investigate memory and cookies**: compare repeated lifecycle actions and heap snapshots when those tools are available; inspect `HttpOnly`, `Secure`, `SameSite`, and partitioning in the request's actual context. A single heap size or cookie attribute is not a diagnosis.
1. **Verify the fix**: repeat the reproduction and relevant measurements, then add a regression test through the owning project workflow. Close task-owned pages and stop only a daemon created for this task.

## Gotchas

- **Tool availability**: inspect the live tool schema or CLI help before calling a capability; optional categories, page routing, and CLI arguments vary by version.
- **Browser mode**: set headed or headless explicitly for reproducibility; the CLI defaults to headless, which need not match a separately configured MCP connection.
- **Lab versus field**: a local trace measures this run. CrUX field data and lab measurements describe different populations and time windows.

## Official Skills

Upstream: [ChromeDevTools/chrome-devtools-mcp skills](https://github.com/ChromeDevTools/chrome-devtools-mcp/tree/main/skills). Use `skills add ChromeDevTools/chrome-devtools-mcp --list`, then follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) for the required guidance.

## Documentation

- [Chrome DevTools for agents](https://github.com/ChromeDevTools/chrome-devtools-mcp) · [CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md) · [Tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md)
- Releases: [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp/releases)
- Companion skills: [agent-mcp](../agent-mcp/SKILL.md), [playwright](../playwright/SKILL.md), [modern-web](../modern-web/SKILL.md), [benchmark](../benchmark/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md).
