---
name: python-ui
description: "Build Gradio model demos and NiceGUI dashboards or browser utilities."
---

# Python UIs (Gradio & NiceGUI)

Use Gradio for ML/LLM model demos, NiceGUI for multi-screen dashboards or general browser utilities, [marimo](../../python-mlops/references/marimo.md) for reactive notebooks, and Litestar + HTMX + [tailwind](../../web-frontend/references/tailwind.md) for custom public web apps.

## Gradio (`6.32.0+`)

1. **Check the locked release**: add `'gradio>=6.32.0'` for packages or preserve PEP 723 metadata in scripts; verify via `uv run python -c 'from importlib.metadata import version; print(version("gradio"))'`.
1. **Start simple**: prefer single-screen `Interface` / `ChatInterface` over multi-tab `Blocks`, tucking advanced parameters into a closed `gr.Accordion`.
1. **Style via supported APIs**: apply a calm light theme from `~/.agents/DESIGN.md` ([web-frontend](../../web-frontend/SKILL.md)) unless branded otherwise. Use `gr.HTML` (`html_template`, `css_template`, `js_on_load`, plus `head` for external scripts since inline `<script>` never runs) instead of brittle internal DOM selectors.
1. **Bind locally**: run `demo.launch(server_name="127.0.0.1", share=False)`. Public `share` tunnels, Spaces uploads, and remote endpoints require explicit authorization.
1. **Guard boundaries**: escape untrusted values in templates/JS, restrict served/downloadable paths to intended artifacts, and enforce server-side auth/validation (Gradio exposes callable HTTP endpoints and `gr.HTML(server_functions=...)` exposes functions to browser JS).

## NiceGUI (`4.0.0+`)

1. **Read the installed reference**: add `'nicegui>=4.0.0'` (`httpx2` client included for `nicegui.testing` `User` fixture) or preserve PEP 723 setup, and inspect the version-matched `llms.md` before consulting online examples:
   ```bash
   uv run python -c 'from importlib.metadata import version; from importlib.util import find_spec; from pathlib import Path; print(version("nicegui")); print(Path(find_spec("nicegui").origin).with_name("llms.md"))'
   ```
   (On `<3.12.0`, read installed package source + docs.)
1. **Isolate logic and bind locally**: keep business logic testable outside UI callbacks and bind dev servers to `127.0.0.1`.
1. **Keep layout Google-simple**: one focused workspace (`max-w-3xl` tools, `max-w-6xl` data) on `~/.agents/DESIGN.md` light palette ([web-frontend](../../web-frontend/SKILL.md)), essential inputs + one primary action upfront, advanced options in `ui.expansion`, and no unrequested drawers, headers, tabs, or KPI cards.
1. **Scope state per user**: module-level state is shared across all users; keep state per page or `app.storage.user` and never treat browser storage IDs as authentication.

## Official Skills & Docs

- **Gradio**: [gradio skill](https://github.com/gradio-app/gradio/tree/main/.agents/skills/gradio) (`huggingface/skills` lags it; install snapshots per [vendor-skills](../../agent-project/references/vendor-skills.md) — never run `gradio skills add`) · [Gradio quickstart](https://www.gradio.app/guides/quickstart) · [Releases](https://github.com/gradio-app/gradio/releases).
- **NiceGUI**: [llms.md](https://github.com/zauberzeug/nicegui/blob/main/nicegui/llms.md) ([llms.txt](https://nicegui.io/llms.txt); skip its `.claude/skills` repo-maintenance files) · [NiceGUI docs](https://nicegui.io/documentation) · [Styling](https://nicegui.io/documentation/section_styling_appearance) · [Testing](https://nicegui.io/documentation/section_testing) · [Releases](https://github.com/zauberzeug/nicegui/releases).
