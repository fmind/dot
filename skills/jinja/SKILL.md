---
name: jinja
description: Author and render Jinja templates. Use for HTML, email, or text templates, inheritance, macros, loaders, escaping, and undefined values.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/jinja
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Jinja

Own template authoring and rendering with Jinja; web framework skills own request integration, and [cookiecutter](../cookiecutter/SKILL.md) owns project generation. Chezmoi uses Go templates; route its dotfile templates to `chezmoi`.

## Workflow

1. Inspect the locked Jinja version, existing environment or framework adapter, template directories, output format, and source trust. Add `jinja2` with `uv add jinja2` only when missing; preserve the application's integration.
1. Configure an environment once before loading templates. Choose a package or filesystem loader with deliberate search roots; use [rendering and tests](references/rendering.md) for a small standalone setup and installed-package checks.
1. Set autoescaping explicitly for HTML/XML outputs, including custom extensions and string templates. For new templates, prefer `StrictUndefined` when missing data is an error; represent optional values explicitly and review compatibility before changing existing undefined behavior.
1. Prepare the presentation data in Python. Use inheritance for page structure, macros for repeated markup, and includes for fragments; keep database access, network calls, and business decisions outside rendering.
1. Pass untrusted values as context data, never interpolate them into template source. Review every `safe` filter, `Markup` value, custom filter, and exposed callable; escaping and sandboxing address different boundaries.
1. Render representative success, missing-value, special-character, empty-collection, and inheritance cases with pytest. Verify templates are included in the wheel and render from a fresh installed environment outside the checkout.
1. Use async rendering only when the adapter or callbacks require it: enable it on the environment and await `render_async`. Route cancellation and task lifetime to [python-async](../python-async/SKILL.md); run the project's native gate.

## Gotchas

- HTML escaping does not validate URL schemes or make arbitrary JavaScript/CSS interpolation safe. Use context-appropriate serialization such as `tojson` and keep attribute quoting deliberate.
- A sandbox does not bound CPU, memory, or output size. If user-authored templates are required, minimize exposed data and callables, use an appropriate sandbox, and enforce external resource limits.
- Do not mutate shared globals with request-specific data or change filters after templates are loaded. Pass per-render context instead.
- Autoescape selection follows template names; a suffix such as `.html.jinja` needs an explicit policy. HTML escaping is inappropriate for plain-text configuration generation.

## Documentation

- [API and loaders](https://jinja.palletsprojects.com/en/stable/api/) · [Template language](https://jinja.palletsprojects.com/en/stable/templates/) · [Sandbox](https://jinja.palletsprojects.com/en/stable/sandbox/)
