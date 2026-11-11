---
name: fmind-visuals
description: "Create VHS terminal demos and logo or cover variants in Fmind/client branding."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fmind-visuals
  created: "2026-07-16"
  updated: "2026-11-11"
---

# Fmind Visual Communication

Apply customer branding when the work belongs to one; otherwise use `~/.agents/DESIGN.md` ([source](https://github.com/fmind/theme/blob/main/DESIGN.md)): legible type, spacious layout, and evidence-backed visuals.

## Workflow

1. **Select the format**: VHS for reproducible terminal demos ([diagrams-as-code](../diagrams-as-code/SKILL.md) owns Mermaid, SVG, and D2 diagrams).
1. **Apply the brand**: use customer/employer palette, fonts, and logo (ask if missing; never mix brands), preserve existing project identities, or map `~/.agents/DESIGN.md` via [renderers.md](references/renderers.md) with OFL font notices and the reviewed Fmind logo. Keep published assets stable across theme updates.
1. **Explore variants**: when the look is open (logo, cover, hero) or a draft is rejected, run numbered rounds via [variants](references/variants.md).
1. **Create and verify**: record VHS demos via [recording.md](references/recording.md) and theme diagrams with [renderers.md](references/renderers.md). Inspect every rendered frame or image for legibility, clipping, fonts, and accessibility, and keep editable sources beside exports.

## Gotchas

- **Cut decoration**: remove decorative nodes, gradients, and generic AI imagery.
- **Edit the source, not a copy**: change the design in fmind/theme; `~/.agents/DESIGN.md` and `~/.agents/themes/` are pinned copies that `mise run upgrade` in fmind/dot advances.

## Task guides

<!-- guides:start -->

- [variants](references/variants.md): Numbered logo, cover, or illustration variant rounds with a light and dark contact sheet.

<!-- guides:end -->

## Documentation

- [Fmind website](https://www.fmind.dev/) · [Mermaid](https://mermaid.js.org/) · [D2](https://d2lang.com/)
- [VHS documentation](https://github.com/charmbracelet/vhs) · Releases: [VHS](https://github.com/charmbracelet/vhs/releases)
- Companions: [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid, SVG, and D2).
