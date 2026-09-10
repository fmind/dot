---
name: gradio
description: Build Python model demos and mini apps with Gradio. Use for Gradio interfaces, chatbots, Blocks event flows, custom HTML components, or official skill setup.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gradio
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Gradio

Build Gradio apps around Python functions and explicit component events. Use [nicegui](../nicegui/SKILL.md) for an explicitly chosen general GUI and [marimo](../marimo/SKILL.md) for reactive notebooks; preserve the framework already selected by the project.

## Workflow

1. Inspect the project dependency model and installed version with `uv run python -c 'import gradio; print(gradio.__version__)'`. For a new packaged app, use `uv add gradio`; preserve PEP 723 metadata for an existing standalone script.
1. Consult the official skill below and documentation matching the installed release. Choose `Interface` for a function demo, `ChatInterface` for conversational interaction, or `Blocks` for custom layouts and multiple event flows.
1. Keep computation independently testable; wire component inputs and outputs explicitly. Use `gr.State` for session state and keep shared model resources separate from user data. Configure queue concurrency around the actual resource, and use generator outputs for streaming work.
1. Start with themes and layout components. Use `gr.HTML` for bespoke HTML/CSS/JavaScript when the installed version supports the needed template and event APIs; avoid styling through undocumented internal DOM selectors.
1. Run locally with `uv run python app.py`, using `demo.launch(server_name="127.0.0.1", share=False)` for local development. Public tunnels, Spaces uploads, and remote predictions have their own exposure, data-transfer, and cost scope.
1. Test successful and invalid inputs, callback failures, and independent sessions where state is used. Exercise the main browser interaction and any streaming or cancellation behavior; an import or HTTP 200 alone does not prove the workflow. Run the project's normal gate.

## Gotchas

- Upstream skill signatures can track a different release; verify constructor and `launch()` parameters against installed source before copying examples.
- HTML templates and JavaScript are executable web content. Keep untrusted input escaped or sanitized, and restrict served/downloadable file paths to the intended artifacts.
- A Gradio interface can expose callable API endpoints. Hiding a component or API listing does not establish authorization.

## Official Skills

Hugging Face publishes [huggingface-gradio](https://github.com/huggingface/skills/tree/main/skills/huggingface-gradio), including app patterns, components, events, custom HTML, and examples. Discover it with `skills add huggingface/skills --list`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) to review an immutable snapshot and install only `huggingface-gradio` at project scope. This catalog entry does not vendor or automatically install that package.

## Documentation

- [Quickstart](https://www.gradio.app/guides/quickstart) · [Blocks and events](https://www.gradio.app/guides/blocks-and-event-listeners) · [State](https://www.gradio.app/guides/state-in-blocks)
- [Custom HTML](https://www.gradio.app/guides/custom-HTML-components) · [Queuing](https://www.gradio.app/guides/queuing) · [File access](https://www.gradio.app/guides/file-access)
