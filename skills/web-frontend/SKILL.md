---
name: web-frontend
description: "Build browser UIs with HTML, CSS, JS, Tailwind; test and debug via Playwright and Chrome DevTools."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-11-22"
---

# Web Frontend

Build calm, detail-perfect browser UIs with native HTML, CSS, and JavaScript. Default to `~/.agents/DESIGN.md` and [humanize](../humanize/SKILL.md) visual clarity unless the project or customer defines its own brand; preserve existing stacks and use Tailwind when selected. [python](../python/SKILL.md) ([litestar](../python/references/litestar/GUIDE.md), [django](../python/references/django/GUIDE.md)) owns backend apps and tests; [playwright](references/playwright.md) owns E2E automation.

## Workflow

1. **Apply the design system**: follow `~/.agents/DESIGN.md` (single primary action, flat hierarchy, inline states, minimal chrome) and copy `~/.agents/themes/{css,tailwind,daisyui}/fmind.css` from [fmind/theme](https://github.com/fmind/theme/tree/main/themes) without editing local copies (export W3C Design Tokens via `npx --yes @google/design.md@0.4.0 export --format dtcg ~/.agents/DESIGN.md`).
1. **Use native web primitives**: prefer `<details>`, `<dialog>`, Popover API, subgrid, container queries, and CSS nesting over JS wrappers or component libraries.
1. **Lookup curated platform guidance**:
   ```bash
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@1.0.0 search "<topic or platform feature>"
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@1.0.0 retrieve "<guide-id>[,<guide-id>]"
   ```
1. **Compile Tailwind**: follow [standalone Tailwind](references/tailwind.md) when Tailwind is used (`tailwindcss` compiles CSS; reserve `npx` for guidance/token CLIs).
1. **Verify live in Chrome & audit a11y/CWV**: capture and inspect **empty, loading, error, and populated states** at `1440x900` and `390x844` via [chrome-devtools](references/chrome-devtools.md); run `lighthouse_audit` and a performance trace (CWV/CLS); confirm zero console/network errors, `>= 4.5:1` contrast, and keyboard/focus flow; run `fmind-review-frontend` ([subagent](../subagent/SKILL.md)) and fix verified defects before delivery.

## Task guides

<!-- guides:start -->

- [chrome-devtools](references/chrome-devtools.md): Debug Chrome via DevTools MCP/CLI: screenshots, console, network, CWV/Lighthouse, accessibility.
- [playwright](references/playwright.md): Automate browsers/E2E tests via Playwright: screenshots, traces.

<!-- guides:end -->

## Gotchas

- **UI microcopy & tabular figures**: action-named buttons ("Save changes", not "Submit"), consistent verbs (Publish → "Published"), right-aligned `tabular-nums`, semantic delta colors (rising latency red, zero gray), and dashes for missing values vs `0`.
- **Cross-check against MDN**: confirm API signatures and baseline support on MDN; enforce the project's browser matrix (else Baseline Widely available, guarding newer features with `@supports`). Tailwind v4 requires Chrome ≥111, Safari ≥16.4, and Firefox ≥128.
- **Pin `modern-web-guidance`**: replace `@latest` in retrieved cross-references with the pinned version, and upgrade both commands together after qualification.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-harnesses/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Releases: [guidance package metadata](https://registry.npmjs.org/modern-web-guidance) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
- Copy and number rules adapted from [anthropics/skills frontend-design](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/frontend-design/SKILL.md) (Apache-2.0) and [taste-skill app-screens](https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/references/app-screens.md) (MIT).
- Companion skills: [python/foundation](../python/references/foundation/GUIDE.md).
