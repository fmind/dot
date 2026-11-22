---
name: diagrams-as-code
description: "Create Typst, D2, Mermaid, SVG diagrams, Altair/Matplotlib charts, VHS demos, visual variants."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diagrams-as-code
  created: "2026-09-16"
  updated: "2026-11-22"
---

# Diagrams as Code

Use diagrams for boundaries, flows, lifecycles, and comparisons (tables/lists when non-spatial). Apply client brand/palette (ask if missing; never mix), keep existing identities, or use `~/.agents/DESIGN.md` ([fmind/theme](https://github.com/fmind/theme/blob/main/DESIGN.md)) and `~/.agents/themes/` (edit upstream only). Cut chrome, gradients, AI imagery.

## Workflow

1. **Pick a guide below**: `typst` (composed cards), `d2` (routed graphs), `mermaid` (GitHub/PR/Zensical fenced blocks), `charts` (Altair/Matplotlib quantitative plots), `svg` (logos/marks), `recording` (VHS demos), `variants` (open look or rejected draft).
1. **Render & inspect**: keep editable sources, inspect PNG/SVG (`>= 12px`, fonts, `>= 4.5:1` contrast, light/dark), and audit via `fmind-review-visuals` / `fmind-review-frontend` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [charts](references/charts.md): Quantitative data charts with Altair/vl-convert and Matplotlib: honest scales, CVD palettes, direct labels, PNG/SVG export.
- [d2](references/d2.md): D2 sources, standalone layouts, theming, and exports.
- [mermaid](references/mermaid.md): Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering.
- [recording](references/recording/GUIDE.md): Record reproducible, isolated terminal demos with VHS, ttyd, and FFmpeg.
- [svg](references/svg/GUIDE.md): Self-contained SVG logos, geometric marks, and live-text visual checks.
- [typst](references/typst.md): Composed illustrations and cards in Typst stdlib: 2x PNG/SVG exports.
- [variants](references/variants/GUIDE.md): Numbered logo, cover, or illustration variants with light/dark sheets.

<!-- guides:end -->

## Documentation

- [fmind/theme](https://github.com/fmind/theme) (each guide links its upstream tool docs/releases).
- Companions: [draft/typst-deck](../draft/references/typst-deck/GUIDE.md), [draft/doc](../draft/references/doc/GUIDE.md), [docs/site](../docs/references/site/GUIDE.md), [docs/repository](../docs/references/repository/GUIDE.md), [web-frontend](../web-frontend/SKILL.md).
