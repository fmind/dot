---
name: diagrams-as-code
description: "Create Typst, D2, LikeC4, Mermaid, SVG diagrams, Altair/Matplotlib charts, VHS demos, visual variants."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diagrams-as-code
  created: "2026-09-16"
  updated: "2026-11-27"
---

# Diagrams as Code

Use diagrams for boundaries, flows, lifecycles, and comparisons (tables/lists when non-spatial). Apply client brand/palette (ask if missing; never mix), keep existing identities, or use `~/.agents/DESIGN.md` ([fmind/theme](https://github.com/fmind/theme/blob/main/DESIGN.md)) and `~/.agents/themes/` (edit upstream only). Cut chrome, gradients, AI imagery.

## Workflow

1. **Pick a guide below**: `typst` (composed cards), `d2` (routed graphs & single-service C4 `layers:`), `likec4` (opt-in multi-container C4 models & interactive explorer), `mermaid` (GitHub/PR/Zensical fenced blocks), `charts` (Altair/Matplotlib quantitative plots), `svg` (logos/marks), `recording` (VHS demos), `variants` (open look or rejected draft).
1. **Render & inspect**: keep editable sources, inspect PNG/SVG (`>= 12px` text, `>= 8pt` dense chart ticks, fonts, `>= 4.5:1` contrast, light/dark), and audit via `fmind-review-visuals` / `fmind-review-frontend` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [charts](references/charts.md): Plot quantitative data charts with Altair/vl-convert and Matplotlib: honest scales, CVD palettes, PNG/SVG.
- [d2](references/d2.md): Author D2 diagram sources, standalone layouts, theming, and vector/raster exports.
- [likec4](references/likec4.md): Author opt-in LikeC4 C4 architecture models, validate in CI, and build interactive static explorers.
- [mermaid](references/mermaid.md): Author portable Mermaid diagrams in Markdown and GitHub: frontmatter config, validation, and rendering.
- [recording](references/recording/GUIDE.md): Record reproducible, isolated terminal demos with VHS, ttyd, and FFmpeg.
- [svg](references/svg/GUIDE.md): Author self-contained SVG logos, geometric marks, and live-text visual checks.
- [typst](references/typst.md): Compose branded illustrations, concept diagrams, and cards in Typst stdlib with 2x PNG/SVG exports.
- [variants](references/variants/GUIDE.md): Generate numbered logo, cover, or illustration variants with light/dark contact sheets.

<!-- guides:end -->

## Documentation

- [fmind/theme](https://github.com/fmind/theme) (each guide links its upstream tool docs/releases).
- Companions: [draft/typst-deck](../draft/references/typst-deck/GUIDE.md), [draft/doc](../draft/references/doc/GUIDE.md), [docs/site](../docs/references/site/GUIDE.md), [docs/repository](../docs/references/repository/GUIDE.md), [web-frontend](../web-frontend/SKILL.md).
