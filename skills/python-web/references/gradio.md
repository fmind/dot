---
name: gradio
description: "Gradio model demos and interactive interfaces."
---

# Gradio

Build Gradio model demos around Python functions and explicit component events; use [nicegui](nicegui.md) for general browser utilities and [marimo](../../python-mlops/references/marimo.md) for reactive notebooks, preserving existing project choices.

## Workflow

1. **Check the locked release**: inspect `uv run python -c 'from importlib.metadata import version; print(version("gradio"))'`; use `uv add gradio` for packages or preserve PEP 723 metadata in scripts.
1. **Start simple**: prefer single-screen `Interface` / `ChatInterface` over multi-tab `Blocks`, tucking advanced parameters into a closed `gr.Accordion`.
1. **Style via supported APIs**: apply a calm light theme from `~/.agents/DESIGN.md` ([web-frontend](../../web-frontend/SKILL.md)) unless branded otherwise. Use `gr.HTML` (`html_template`, `css_template`, `js_on_load`, plus `head` for external scripts since inline `<script>` never runs) instead of brittle internal DOM selectors.
1. **Bind locally**: run `demo.launch(server_name="127.0.0.1", share=False)`. Public `share` tunnels, Spaces uploads, and remote endpoints require explicit authorization.

## Gotchas

- **Sanitize HTML/JS and file paths**: escape untrusted values in templates/JS and restrict served/downloadable paths to intended artifacts.
- **Hidden UI != auth**: Gradio exposes callable HTTP endpoints and `gr.HTML(server_functions=...)` exposes functions to browser JS — validate and authorize server-side.

## Official Skills & Docs

Upstream: [gradio skill](https://github.com/gradio-app/gradio/tree/main/.agents/skills/gradio) (`huggingface/skills` lags it); install reviewed snapshots per [vendor-skills](../../agent-project/references/vendor-skills.md) — never run `gradio skills add` (pulls unreviewed `main`). Docs: [Gradio](https://www.gradio.app/guides/quickstart) · [Releases](https://github.com/gradio-app/gradio/releases).
