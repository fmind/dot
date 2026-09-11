---
name: nicegui
description: Build Python mini apps with NiceGUI. Use for browser utilities, dashboards, forms, tables, pages, and event-driven interfaces in an existing or chosen NiceGUI app.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/nicegui
  created: "2026-09-10"
  updated: "2026-09-11"
---

# NiceGUI

Build browser utilities with Python components and event handlers. Use [gradio](../gradio/SKILL.md) for an explicitly chosen model demo and [marimo](../marimo/SKILL.md) for reactive notebooks; preserve the existing project's framework.

## Workflow

1. Inspect the project's locked NiceGUI version and dependency model, preserving packaged or PEP 723 setup. Locate and read its installed agent reference below before using online examples.
1. Use that reference for components, page state, callbacks, and tests. Keep computation independently testable and local development bound to `127.0.0.1`.
1. Verify the main browser interaction, independent client state, callback failures, and the project's native gate. An import or HTTP 200 alone does not prove UI behavior.

## Installed reference

```bash
uv run python -c 'from importlib.metadata import version; from importlib.util import find_spec; from pathlib import Path; print(version("nicegui")); print(Path(find_spec("nicegui").origin).with_name("llms.md"))'
```

If that release lacks `llms.md`, use the official documentation and installed source. The online reference follows upstream development and may describe newer APIs.

## Gotchas

- Module-level mutable state is shared across users; choose the page or storage scope deliberately. Storage identity does not replace authentication.
- Blocking callbacks stall the shared event loop; use the installed reference's supported I/O and CPU offloading facilities.
- Python callbacks need the running server and persistent connection. Static export or generic extra ASGI workers do not automatically preserve that model.

## Official Skills

As checked on 2026-09-10, [zauberzeug/nicegui](https://github.com/zauberzeug/nicegui) provides an official [LLM reference](https://github.com/zauberzeug/nicegui/blob/main/nicegui/llms.md), also served at [llms.txt](https://nicegui.io/llms.txt). No reusable application-authoring `SKILL.md` was found in that repository; its `.claude/skills` entries cover upstream maintenance. Use the installed reference above rather than installing those maintenance skills into an application.

## Documentation

- [NiceGUI documentation](https://nicegui.io/documentation) · [Styling](https://nicegui.io/documentation/section_styling_appearance) · [Testing](https://nicegui.io/documentation/section_testing)
