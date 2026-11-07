---
name: web-frontend
description: "Design and build simple browser UIs with HTML, CSS, JavaScript, and Tailwind."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-11-07"
---

# Web Frontend

Build calm, spacious, Google-simple browser interfaces with native HTML, CSS, and JavaScript. Apply `~/.agents/DESIGN.md` by default unless the project or customer defines its own identity; preserve an existing frontend stack and use Tailwind when the project selects it. [python-web](../python-web/SKILL.md) owns server applications, including server rendering, APIs, and application tests through [litestar](../python-web/references/litestar/GUIDE.md) or [django](../python-web/references/django/GUIDE.md); [playwright](../playwright/SKILL.md) owns browser automation.

## Workflow

1. **Apply the design system**: for Fmind work, follow `~/.agents/DESIGN.md` for layouts, the single primary action, flat hierarchy, inline states, and omitted chrome; export its CSS variables or Tailwind `@theme` tokens via [fmind-visuals renderers](../fmind-visuals/references/renderers.md#exports) (`npx @google/design.md@0.4.0 export`).
1. **Prefer web platform primitives**: use native elements (`<details>`, `<dialog>`, popover API, subgrid, container queries, CSS nesting) over third-party component libraries or custom script wrappers.
1. **Retrieve platform guidance**: search curated web platform recipes, then fetch a guide's implementation details and browser baselines by identifier:
   ```bash
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@0.0.196 search "<topic or platform feature>"
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@0.0.196 retrieve "<guide-id>[,<guide-id>]"
   ```
1. **Compile Tailwind**: use the [standalone Tailwind workflow](references/tailwind.md) when the project selects Tailwind; preserve an existing asset pipeline. `tailwindcss` owns CSS compilation, while `npx` runs only the guidance and token export CLIs above.
1. **Open and check in Chrome**: start the app, open it in Chrome with [chrome-devtools](../chrome-devtools/SKILL.md), and exercise the primary flow; verify it works without console or network errors and check layout, visual restraint, responsive viewports, keyboard flow, and accessibility before reporting done. Fix the issues found, recheck the affected flow, and stop: no open-ended visual polishing loops.

## Gotchas

- **Write copy in the user's terms**: buttons name their action ("Save changes", not "Submit"), one verb carries through the flow (Publish → "Published"), labels use the user's vocabulary, not the system's, and errors state the fix without apologizing.
- **Show numbers so they compare**: right-align figures with tabular numerals and fixed decimals per metric; color a change by good or bad, not up or down (rising latency is red), with zero change in gray; show a missing value as a dash and a real zero as `0`. Sample data is computed from its rows, and totals add up.
- **Verify preview guidance against MDN**: Modern Web Guidance is an evolving catalog; always verify API signatures and baseline status against authoritative MDN documentation.
- **Set the browser target first**: use the project's browserslist or support matrix, else Baseline Widely available; guard newer features from the guidance with `@supports` or progressive enhancement. Tailwind v4 needs Chrome 111, Safari 16.4, and Firefox 128; confirm the target allows them before adopting it.
- **Keep the pin for cross-references**: retrieved guides cite `npx -y modern-web-guidance@latest retrieve ...`; run those with the pinned version instead. Bump both commands together to the latest stable release after qualifying it.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Releases: [guidance package metadata](https://registry.npmjs.org/modern-web-guidance) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
- Copy and number rules adapted from [anthropics/skills frontend-design](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/frontend-design/SKILL.md) (Apache-2.0) and [taste-skill app-screens](https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/references/app-screens.md) (MIT).
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md).
