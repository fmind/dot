---
name: typst
description: "Compose branded illustrations, concept diagrams, and cards in Typst stdlib with 2x PNG/SVG exports."
---

# Typst Composed Illustrations

Build calm concept illustrations, architecture diagrams, and step flows with the Typst stdlib (`fmind-diagram` in `fmind.typ`): zero `@preview/...` packages, ~5x fewer tokens than raw `<svg>`, and crisp 2x PNG or SVG exports. [Diagrams as code](../SKILL.md) owns format selection; use `fmind-diagram` here for auto-sized technical/architecture visuals, and [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md) (`brand-card` / `fmind-slides.typ`) for fixed-width executive KPI/bar cards and 16:9 decks (`typst` is global in `fmind/dot`; pin via `mise use --pin typst && mise lock`).

## Workflow

1. **Pick one concept**: loop, before/after, mapping, boundary, or pipeline (`3–7` items/group; split dense views instead of shrinking type).
1. **Stage theme**: for Fmind work, copy `~/.agents/themes/typst/fmind.typ` beside `.typ` sources (`docs/assets/fmind.typ`) so `#import "fmind.typ": *` resolves inside `--root`. For customer work, define their brand tokens instead (never mix brands).
1. **Compose with `fmind-diagram`**: use `grid`, `stack`, `frame`, `section-label`, `chip`, `tile`, `flow-arrow`, `loop-back`, `status-badge`, and `diagram-{group,container,component,actor,external,step,terminal}`. Target `~680–720pt` for READMEs/docs, or `<=440pt` for Google Docs ([draft/doc](../../draft/references/doc/GUIDE.md)):

   ```typst
   #import "fmind.typ": *
   #show: fmind-diagram

   #frame[#grid(
     columns: (170pt, 54pt, 220pt, 54pt, 170pt),
     align: (top, horizon, top, horizon, top),
     stack(spacing: 6pt, section-label[Inputs], ..("Events", "Schemas").map(chip)),
     flow-arrow(step: 1, caption: "validate"),
     diagram-container(width: 100%, fill: colors.canvas, tile("worker", "transform · verify")),
     flow-arrow(step: 2, caption: "publish"),
     stack(spacing: 6pt, section-label[Outputs], ..("Tables", "Metrics").map(chip)),
   )]
   ```

1. **Compile 2x PNG (primary) and keep `.typ` beside exports** (add `--format svg` only when vector zoom is needed):

   ```bash
   cp ~/.agents/themes/typst/fmind.typ docs/assets/fmind.typ
   typst compile --format png --ppi 192 docs/assets/concept.typ docs/assets/concept.png
   ```

1. **Embed & inspect**: wrap `<img src="docs/assets/concept.png" alt="Takeaway conclusion" width="960">` in `<a href="docs/assets/concept.png">` with a nearby prose/table summary; inspect the PNG for zero stderr warnings, crisp connectors, unclipped labels, and `>= 4.5:1` contrast.

## Gotchas

- **No `@preview/...` packages**: Universe packages (`fletcher`, `cetz`) trigger cold-cache fetches; stdlib layout stays offline and compact.
- **Avoid root `width: 100%` on `width: auto` pages**: `100%` of `auto` collapses to `0pt`. Use explicit `grid(columns: (...))` widths or `brand-card` ([draft/typst-deck](../../draft/references/typst-deck/GUIDE.md)) for fixed-width cards.
- **Fonts & warnings**: pass `--font-path` to `Google Sans` / `Google Sans Code` under `--ignore-system-fonts` or overridden `HOME`. Treat any Typst stderr warning (`unknown font family`, unescaped `*`) as failure; `tile()` uses `Google Sans Code`.

## Documentation

- [Typst styling](https://typst.app/docs/reference/styling/) · [Layout](https://typst.app/docs/reference/layout/) · [Visualize](https://typst.app/docs/reference/visualize/)
- Companions: [d2](d2.md), [svg](svg/GUIDE.md), [draft/doc](../../draft/references/doc/GUIDE.md), [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md).
