---
name: web-frontend
description: "Build browser UIs with HTML, CSS, JavaScript, and Tailwind."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-10-04"
---

# Web Frontend

Build browser interfaces with native HTML, CSS, and JavaScript. Preserve an existing frontend stack and use Tailwind when the project selects it. [python-web](../python-web/SKILL.md) owns server applications, including server rendering, APIs, and application tests through [litestar](../python-web/references/litestar/GUIDE.md) or [django](../python-web/references/django/GUIDE.md); [product-design-review](../product-design-review/SKILL.md) owns interface critique, and [playwright](../playwright/SKILL.md) owns browser automation.

## Workflow

1. **Retrieve guidance**: search curated web platform recipes, then fetch a guide's implementation details and browser baselines by identifier:
   ```bash
   npx --yes modern-web-guidance@0.0.190 search "<topic or api>"
   npx --yes modern-web-guidance@0.0.190 retrieve "<guide-id>"
   ```
1. **Prefer web platform primitives**: Prioritize native elements (`<dialog>`, `<details>`, popover API, subgrid, container queries, CSS nesting) over third-party component libraries or custom script wrappers.
1. **Verify baseline compatibility**: Check baseline availability and browser support before adopting newly standardized APIs; fall back progressively without blocking core experiences.
1. **Compile Tailwind**: use the [standalone Tailwind workflow](references/tailwind.md) when the project selects Tailwind; preserve an existing asset pipeline. `tailwindcss` owns CSS compilation, while `npx` runs only the guidance CLI above.
1. **Audit with DevTools**: Validate rendering, performance, and accessibility against live browser sessions using [chrome-devtools](../chrome-devtools/SKILL.md) and [quality-assurance](../quality-assurance/SKILL.md).

## Gotchas

- **Preview status**: Modern Web Guidance is an evolving catalog; always verify API signatures and baseline status against authoritative MDN documentation.
- **Version refresh**: both commands share one review pin; bump them together only to the latest stable release past npm's `min-release-age` cooldown, after qualifying it, and never disable that policy to pass a freshness check.
- **Progressive enhancement**: Native dialogs, popovers, and top-layer elements require careful focus and accessibility management; verify keyboard navigation.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Releases: [guidance package metadata](https://registry.npmjs.org/modern-web-guidance) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md), [research-brief](../implementation-plan/references/research-brief.md).
