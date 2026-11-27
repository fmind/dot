---
name: web-frontend
description: "Build browser UIs with HTML, CSS, JS, Tailwind; test and debug via Playwright and Chrome DevTools."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-11-25"
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

## Surface, A11y & Security Floors

- **Browser security**: block DOM XSS sinks (`innerHTML`, `dangerouslySetInnerHTML`, `document.write`, `javascript:` URLs); ship nonce/hash `CSP`, `nosniff`, `frame-ancestors`, `Referrer-Policy`, `HttpOnly`/`Secure`/`SameSite` cookies, and `SRI` on external scripts.
- **SEO & HTTP honesty**: public pages declare `<title>`, `description`, `canonical`, `robots.txt`, `sitemap.xml`; private/admin/preview routes enforce `noindex` (`X-Robots-Tag`/meta) + `Cache-Control: private, no-store`; zero soft-`200` error pages.
- **A11y & forms**: declare `<meta name="color-scheme">`, honor `prefers-reduced-motion`, enforce `>= 24x24px` targets + `:focus-visible`, and preserve form input on error without leaking raw stacks.

## Task guides

<!-- guides:start -->

- [chrome-devtools](references/chrome-devtools.md): Debug Chrome via DevTools MCP/CLI: screenshots, console, network, CWV/Lighthouse, accessibility.
- [playwright](references/playwright.md): Automate browsers/E2E tests via Playwright: screenshots, traces.
- [tailwind](references/tailwind.md): Compile standalone Tailwind CSS in Python web apps via mise without Node.

<!-- guides:end -->

## Gotchas

- **Microcopy & figures**: action verbs on buttons ("Save changes", not "Submit"), consistent labels, right-aligned `tabular-nums`, semantic delta colors, and dashes for missing values vs `0`.
- **Browser baseline**: verify APIs on MDN against the project matrix (else Baseline Widely available + `@supports`); Tailwind v4 requires Chrome ≥111, Safari ≥16.4, Firefox ≥128.
- **Pin `modern-web-guidance`**: replace `@latest` in retrieved references with the pinned version and upgrade both commands together.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow [vendor-skill policy](../agent-harnesses/references/vendor-skills.md).

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [repo](https://github.com/GoogleChrome/modern-web-guidance) · [npm](https://registry.npmjs.org/modern-web-guidance) · [Tailwind releases](https://github.com/tailwindlabs/tailwindcss/releases)
- Copy/number rules adapted from [anthropics/skills frontend-design](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/frontend-design/SKILL.md) (Apache-2.0) and [taste-skill app-screens](https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/references/app-screens.md) (MIT).
- Companion: [python/foundation](../python/references/foundation/GUIDE.md).
