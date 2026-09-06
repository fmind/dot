---
name: modern-web
description: "Apply modern web platform standards, native HTML, CSS, and JavaScript features, and compatibility guidance. Use for modern web development, APIs, or front-end modernization."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/modern-web
  created: "2026-09-03"
  updated: "2026-09-06"
---

# Modern Web Guidance

Modern Web Guidance embeds web platform expertise, browser compatibility data, and modern baseline practices directly into coding agents. It steers code generation away from obsolete polyfills and heavy JavaScript abstractions toward native HTML, modern CSS, and standard browser APIs. Python web applications route through [python-stack](../python-stack/SKILL.md); browser automation and testing route through [playwright](../playwright/SKILL.md) and [chrome-devtools](../chrome-devtools/SKILL.md).

## 1. Retrieve Guidance

1. **Search guidelines**: Query curated web platform recipes and modern practices using the CLI:
   ```bash
   npx --yes modern-web-guidance@0.0.185 search "<topic or api>"
   ```
1. **Fetch specific pattern**: Retrieve detailed implementation guidelines and browser baselines by guide identifier:
   ```bash
   npx --yes modern-web-guidance@0.0.185 retrieve "<guide-id>"
   ```

## 2. Adoption Workflow

1. **Prefer web platform primitives**: Prioritize native elements (`<dialog>`, `<details>`, popover API, subgrid, container queries, CSS nesting) over third-party component libraries or custom script wrappers.
1. **Verify baseline compatibility**: Check baseline availability and browser support before adopting newly standardized APIs; fall back progressively without blocking core experiences.
1. **Audit with DevTools**: Validate rendering, performance, and accessibility against live browser sessions using [chrome-devtools](../chrome-devtools/SKILL.md) and [quality-assurance](../quality-assurance/SKILL.md).

## Gotchas

- **Preview status**: Modern Web Guidance is an evolving catalog; always verify API signatures and baseline status against authoritative MDN documentation.
- **Version refresh**: the CLI example is review-pinned; verify the latest stable npm release and update both commands together before adopting newer guidance.
- **Application integration**: keep browser behavior in native HTML, CSS, and JavaScript; use [python-stack](../python-stack/SKILL.md) for server rendering, APIs, and application tests.
- **Progressive enhancement**: Native dialogs, popovers, and top-layer elements require careful focus and accessibility management; verify keyboard navigation.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Companion skills: [python-stack](../python-stack/SKILL.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md), [technical-research](../technical-research/SKILL.md).
