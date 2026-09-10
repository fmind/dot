---
name: nicegui
description: Build Python mini apps with NiceGUI. Use for browser utilities, dashboards, forms, tables, pages, and event-driven interfaces in an existing or chosen NiceGUI app.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/nicegui
  created: "2026-09-10"
  updated: "2026-09-10"
---

# NiceGUI

Build browser utilities with Python components and event handlers. Use [gradio](../gradio/SKILL.md) for an explicitly chosen model demo and [marimo](../marimo/SKILL.md) for reactive notebooks; preserve the existing project's framework.

## Workflow

1. Inspect the project dependency model; for a new packaged app, use `uv add nicegui`. Preserve PEP 723 metadata for an existing standalone script. Locate the installed version and its official agent reference with the command below, then read the reference when present.
1. Build pages with `@ui.page`, keeping visitor-specific state inside the page or the appropriate `app.storage` scope. Prefer ordinary Python callbacks, bindings, and in-place element updates; reserve `@ui.refreshable` for subtrees that need rebuilding.
1. Use rows, columns, cards, dialogs, and native components before custom HTML or JavaScript. Style with supported component properties, Tailwind classes, and scoped CSS; verify responsive behavior and keyboard interaction in the browser.
1. Keep the shared event loop responsive. Await asynchronous I/O; use `await run.io_bound(...)` for blocking I/O and `await run.cpu_bound(...)` for CPU work, with picklable arguments and results. Return UI changes to the page context and surface task failures.
1. Run locally with `uv run python app.py`, using `ui.run(host="127.0.0.1")` for local development. Inspect the deployment model before changing binding, proxy, or worker settings.
1. Test callbacks and invalid inputs with the project's test harness. Use NiceGUI's `user` fixture for simulated interactions and browser tests for layout or JavaScript behavior; check state isolation with separate clients when state is involved. Run the project's normal gate.

## Installed reference

```bash
uv run python -c 'from importlib.metadata import version; from importlib.util import find_spec; from pathlib import Path; print(version("nicegui")); print(Path(find_spec("nicegui").origin).with_name("llms.md"))'
```

If that release lacks `llms.md`, use the official documentation and installed source. The online reference follows upstream development and may describe newer APIs.

## Gotchas

- Module-level mutable state is shared by all users. Choose page, client, tab, user, or general storage deliberately; cookie-based storage identity does not replace application authentication.
- Blocking a callback stalls the shared event loop. Do not call blocking model inference directly from an async UI handler.
- NiceGUI uses a persistent Socket.IO connection and a single server worker. A static HTML export cannot preserve Python callbacks, and adding generic ASGI workers does not automatically preserve UI state.
- Rebuilding elements can lose focus and browser state; update existing values where possible. Direct DOM mutation can diverge from NiceGUI's Python-side element model.

## Official Skills

As checked on 2026-09-10, [zauberzeug/nicegui](https://github.com/zauberzeug/nicegui) provides an official [LLM reference](https://github.com/zauberzeug/nicegui/blob/main/nicegui/llms.md), also served at [llms.txt](https://nicegui.io/llms.txt). No reusable application-authoring `SKILL.md` was found in that repository; its `.claude/skills` entries cover upstream maintenance. Use the installed reference above rather than installing those maintenance skills into an application.

## Documentation

- [NiceGUI documentation](https://nicegui.io/documentation) · [Styling](https://nicegui.io/documentation/section_styling_appearance) · [Testing](https://nicegui.io/documentation/section_testing)
