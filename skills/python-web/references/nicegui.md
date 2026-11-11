---
name: nicegui
description: "NiceGUI dashboards and general browser interfaces."
---

# NiceGUI

Build browser utilities with Python components and event handlers; use [gradio](gradio.md) for model demos and [marimo](../../python-mlops/references/marimo.md) for reactive notebooks, preserving existing project choices.

## Workflow

1. **Read the installed reference (`3.12.0+`)**: preserve packaged or PEP 723 setup and inspect the version-matched `llms.md` before consulting online examples (which track `main`):
   ```bash
   uv run python -c 'from importlib.metadata import version; from importlib.util import find_spec; from pathlib import Path; print(version("nicegui")); print(Path(find_spec("nicegui").origin).with_name("llms.md"))'
   ```
   (On `<3.12.0`, read installed package source + docs.)
1. **Isolate logic and bind locally**: keep business logic testable outside UI callbacks and bind dev servers to `127.0.0.1`.
1. **Keep layout Google-simple**: one focused workspace (`max-w-3xl` tools, `max-w-6xl` data) on `~/.agents/DESIGN.md` light palette ([web-frontend](../../web-frontend/SKILL.md)), essential inputs + one primary action upfront, advanced options in `ui.expansion`, and no unrequested drawers, headers, tabs, or KPI cards.

## Gotchas & Upstream Reference

- **Module-level state is shared across all users**: scope state per page or storage, and never treat storage IDs as authentication.
- Upstream [zauberzeug/nicegui](https://github.com/zauberzeug/nicegui) ships [llms.md](https://github.com/zauberzeug/nicegui/blob/main/nicegui/llms.md) ([llms.txt](https://nicegui.io/llms.txt)); skip its `.claude/skills` (repo maintenance only).
- Docs: [NiceGUI](https://nicegui.io/documentation) · [Styling](https://nicegui.io/documentation/section_styling_appearance) · [Testing](https://nicegui.io/documentation/section_testing) · [Releases](https://github.com/zauberzeug/nicegui/releases).
