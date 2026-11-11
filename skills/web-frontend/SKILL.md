---
name: web-frontend
description: "Design and build simple browser UIs with HTML, CSS, JavaScript, and Tailwind."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/web-frontend
  created: "2026-09-03"
  updated: "2026-11-11"
---

# Web Frontend

Build calm, Google-simple browser UIs with native HTML, CSS, and JavaScript. Default to `~/.agents/DESIGN.md` unless the project or customer defines its own brand; preserve existing stacks and use Tailwind when selected. [python-web](../python-web/SKILL.md) ([litestar](../python-web/references/litestar/GUIDE.md), [django](../python-web/references/django/GUIDE.md)) owns backend apps and tests; [playwright](../playwright/SKILL.md) owns E2E automation.

## Workflow

1. **Apply the design system**: follow `~/.agents/DESIGN.md` (single primary action, flat hierarchy, inline states, minimal chrome) and copy `~/.agents/themes/` CSS, Tailwind `@theme`, or daisyUI files ([renderers](../fmind-visuals/references/renderers.md#pinned-files)).
1. **Use native web primitives**: prefer `<details>`, `<dialog>`, Popover API, subgrid, container queries, and CSS nesting over JS wrappers or component libraries.
1. **Lookup curated platform guidance**:
   ```bash
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@1.0.0 search "<topic or platform feature>"
   DISABLE_TELEMETRY=1 npx --yes modern-web-guidance@1.0.0 retrieve "<guide-id>[,<guide-id>]"
   ```
1. **Compile Tailwind**: follow [standalone Tailwind](references/tailwind.md) when Tailwind is used (`tailwindcss` compiles CSS; reserve `npx` for guidance/token CLIs).
1. **Verify live in Chrome**: exercise the primary flow with [chrome-devtools](../chrome-devtools/SKILL.md), confirming zero console/network errors, clean responsive viewports, keyboard flow, and accessibility; fix defects, recheck, and stop without open-ended polish loops.

## Gotchas

- **User-centered copy**: action-named buttons ("Save changes", not "Submit"), consistent verbs (Publish → "Published"), user terms over internal names, and actionable non-apologetic errors.
- **Comparable numbers**: right-aligned tabular numerals, fixed decimals per metric, semantic delta colors (rising latency is red, zero is gray), dashes for missing values vs `0`, and row-consistent sample totals.
- **Cross-check against MDN**: confirm API signatures and baseline support on MDN; enforce the project's browser matrix (else Baseline Widely available, guarding newer features with `@supports`). Tailwind v4 requires Chrome ≥111, Safari ≥16.4, and Firefox ≥128.
- **Pin `modern-web-guidance`**: replace `@latest` in retrieved cross-references with the pinned version, and upgrade both commands together after qualification.

## Official Skills

Upstream: `GoogleChrome/modern-web-guidance`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant platform guidance.

## Documentation

- [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) · [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance)
- Releases: [guidance package metadata](https://registry.npmjs.org/modern-web-guidance) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/releases)
- Copy and number rules adapted from [anthropics/skills frontend-design](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/frontend-design/SKILL.md) (Apache-2.0) and [taste-skill app-screens](https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/references/app-screens.md) (MIT).
- Companion skills: [python-stack](../python-stack/references/foundation/GUIDE.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md).
