---
name: web-frontend
description: "Design and build simple browser UIs with HTML, CSS, JavaScript, and Tailwind."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-10-31"
---

# Web Frontend

Build calm, spacious, Google-simple browser interfaces with native HTML, CSS, and JavaScript. Apply `~/.agents/DESIGN.md` by default unless the project or customer defines its own identity; preserve an existing frontend stack and use Tailwind when the project selects it. [python-web](../python-web/SKILL.md) owns server applications, including server rendering, APIs, and application tests through [litestar](../python-web/references/litestar/GUIDE.md) or [django](../python-web/references/django/GUIDE.md); [playwright](../playwright/SKILL.md) owns browser automation.

## Workflow

1. **Scope to one primary job per view**: center the main input and result in a single clean flow (`768px` reading/tool width, `1152px` page max) with one primary action pill in the theme's primary color and sensible defaults that work on first click or `Enter`. Put advanced or secondary controls behind progressive disclosure (`<details>` or a menu), and omit unrequested chrome (navbars, sidebars, tabs, KPI ribbons, filter bars, settings drawers, fake auth).
1. **Apply the design tokens**: for Fmind work, read `~/.agents/DESIGN.md` and export CSS variables or Tailwind `@theme` tokens via [fmind-visuals renderers](../fmind-visuals/references/renderers.md#exports) (`npx @google/design.md@0.4.0 export`). Use a flat light hierarchy from those tokens (white canvas, gray panels, 1px borders, charcoal text, muted labels, Google Sans and Google Sans Code, 4px/8px spacing with 24–32px margins) without drop shadows, gradients, or nested bordered cards.
1. **Prefer web platform primitives**: prioritize native elements (`<details>`, `<dialog>`, popover API, subgrid, container queries, CSS nesting) over third-party component libraries or custom script wrappers, and render loading, empty, error, and result states inline rather than in modals or toast spam.
1. **Retrieve platform guidance**: search curated web platform recipes, then fetch a guide's implementation details and browser baselines by identifier:
   ```bash
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@0.0.196 search "<topic or platform feature>"
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@0.0.196 retrieve "<guide-id>[,<guide-id>]"
   ```
1. **Compile Tailwind**: use the [standalone Tailwind workflow](references/tailwind.md) when the project selects Tailwind; preserve an existing asset pipeline. `tailwindcss` owns CSS compilation, while `npx` runs only the guidance and token export CLIs above.
1. **Audit with DevTools**: validate rendering, visual restraint, keyboard flow, performance, and accessibility against live browser sessions using [chrome-devtools](../chrome-devtools/SKILL.md) and [quality-assurance](../quality-assurance/SKILL.md).

## Gotchas

- **Verify preview guidance against MDN**: Modern Web Guidance is an evolving catalog; always verify API signatures and baseline status against authoritative MDN documentation.
- **Set the browser target first**: use the project's browserslist or support matrix, else Baseline Widely available; guard newer features from the guidance with `@supports` or progressive enhancement. Tailwind v4 needs Chrome 111, Safari 16.4, and Firefox 128; confirm the target allows them before adopting it.
- **Keep the pin for cross-references**: retrieved guides cite `npx -y modern-web-guidance@latest retrieve ...`; run those with the pinned version instead. Bump both commands together to the latest stable release after qualifying it.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Releases: [guidance package metadata](https://registry.npmjs.org/modern-web-guidance) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md), [research-brief](../implementation-plan/references/research-brief.md).
