---
name: gradio
description: "Gradio model demos and interactive interfaces."
---

# Gradio

Build Gradio apps around Python functions and explicit component events. Use [nicegui](nicegui.md) for an explicitly chosen general GUI and [marimo](../../python-mlops/references/marimo.md) for reactive notebooks; preserve the framework already selected by the project.

## Workflow

1. **Start from the installed release**: inspect the project dependency model and installed version with `uv run python -c 'from importlib.metadata import version; print(version("gradio"))'`, without importing the framework. For a new packaged app, use `uv add gradio`; preserve PEP 723 metadata for an existing standalone script.
1. **Choose the API from current docs**: consult the official skill below and documentation matching the installed release. Choose `Interface` for a function demo, `ChatInterface` for conversational interaction, or `Blocks` for custom layouts and multiple event flows. Prefer a single-screen `Interface` or `ChatInterface` over multi-tab `Blocks` unless distinct workflows require it; keep only essential inputs visible and place advanced parameters in a closed `gr.Accordion`.
1. **Separate logic, state, and wiring**: keep computation independently testable; wire component inputs and outputs explicitly. Use `gr.State` for session state and keep shared model resources separate from user data. Configure queue concurrency around the actual resource, and use generator outputs for streaming work.
1. **Style through supported APIs**: start with themes and layout components, applying a calm light theme aligned with `~/.agents/DESIGN.md` (white canvas, gray panels, its primary accent, Google Sans and Google Sans Code; take values from the DESIGN.md export, never copies) unless the project has its own brand. Use `gr.HTML` for bespoke HTML/CSS/JavaScript through `html_template`, `css_template`, and `js_on_load` when the installed version supports them, loading third-party scripts through `head`; `<script>` tags in content never run. Avoid styling through undocumented internal DOM selectors.
1. **Bind development to loopback**: run locally with `uv run python app.py`, using `demo.launch(server_name="127.0.0.1", share=False)` for local development. Public tunnels, Spaces uploads, and remote predictions have their own exposure, data-transfer, and cost scope.
1. **Prove the browser workflow**: exercise the main browser interaction and any streaming or cancellation behavior; an import or HTTP 200 alone does not prove the workflow.

## Gotchas

- **Sanitize executable web content**: HTML templates and JavaScript are executable web content. Keep untrusted input escaped or sanitized, and restrict served/downloadable file paths to the intended artifacts.
- **Hiding endpoints is not authorization**: a Gradio interface can expose callable API endpoints. Hiding a component or API listing does not establish authorization, and `gr.HTML(server_functions=...)` makes each listed function callable from browser JavaScript; validate and authorize inside it.

## Official Skills

Gradio maintains its [gradio skill](https://github.com/gradio-app/gradio/tree/main/.agents/skills/gradio) (core API, component signatures, events, and examples) in the framework repository; as checked on 2026-10-31, the `huggingface-gradio` copy in huggingface/skills lags it. Discover it with `DISABLE_TELEMETRY=1 skills add gradio-app/gradio --list`; follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) to review an immutable snapshot and install only `gradio` at project scope. Do not run `gradio skills add`: it downloads from the `main` branch without snapshot review.

## Documentation

- [Quickstart](https://www.gradio.app/guides/quickstart) · [Blocks and events](https://www.gradio.app/guides/blocks-and-event-listeners) · [State](https://www.gradio.app/guides/state-in-blocks)
- [Custom HTML](https://www.gradio.app/guides/custom-HTML-components) · [Queuing](https://www.gradio.app/guides/queuing) · [File access](https://www.gradio.app/guides/file-access)
- Releases: [Gradio](https://github.com/gradio-app/gradio/releases) · [changelog](https://www.gradio.app/changelog)
