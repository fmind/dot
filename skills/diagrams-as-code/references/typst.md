---
name: typst
description: "Composed illustrations and cards in pure Typst stdlib: branding, layout, 2x PNG/SVG export, and checks."
---

# Typst Composed Illustrations

Build calm, branded concept illustrations, cards, and step flows with the Typst standard library—zero `@preview/...` packages, ~5× fewer tokens than hand-authored `<svg>`, and crisp Retina PNG or SVG exports. [Diagrams as code](../SKILL.md) owns format selection (`typst` is installed globally in `fmind/dot`; pin in projects with `mise use --pin typst && mise lock`).

## Workflow

1. **Pick one concept**: loop, before/after, mapping, boundary, or pipeline (`3–7` items per group; split dense views instead of shrinking type).
1. **Stage the theme module**: for Fmind work, copy `~/.agents/themes/typst/fmind.typ` next to your `.typ` sources (`docs/assets/fmind.typ` or `.github/assets/fmind.typ`) so `typst compile` resolves `#import "fmind.typ": *` inside `--root`. For customer work, define their brand colors and fonts instead (ask if missing; never mix brands).
1. **Compose with stdlib + `fmind.typ` helpers**: apply `#show: fmind-diagram` (auto-sized `#FFFFFF` canvas, `Google Sans` + `Google Sans Code`) and combine `grid`, `stack`, `frame`, `section-label`, `chip`, `tile`, `flow-arrow`, `loop-back`, `status-badge`, and the seven `DESIGN.md` `diagram-*` shapes (`diagram-group`, `diagram-container`, `diagram-component`, `diagram-actor`, `diagram-external`, `diagram-step`, `diagram-terminal`). Target `~680–720pt` total width (`~900–960px` at 1×) for READMEs/docs, or ≤`440pt` for Google Docs ([draft-doc](../../draft-doc/SKILL.md)):

   ```typst
   #import "fmind.typ": *
   #show: fmind-diagram

   #frame[
     #loop-back(step: 3)[change the source, never the deployed copy: diff, then apply][
       #grid(
         columns: (176pt, 54pt, 246pt, 54pt, 176pt),
         align: (top, horizon, top, horizon, top),
         stack(spacing: 6.5pt, section-label[Source], ..("Templates", "Skills", "Lockfiles").map(chip)),
         flow-arrow(step: 1, caption: "clone"),
         stack(spacing: 6.5pt,
           section-label[chezmoi · mise · dot],
           diagram-container(width: 100%, fill: colors.canvas, inset: 13pt, stack(spacing: 8pt,
             tile("install.sh", "mise · chezmoi init · mise run install",
                  fill: colors.warning-surface, stroke: 1pt + colors.warning-accent, title-fill: colors.foreground),
             tile("chezmoi", "files · hooks · encrypted seeds"),
             align(center, muted[re-sync anytime: `mise run full`]),
           )),
         ),
         flow-arrow(step: 2, caption: "apply"),
         stack(spacing: 6.5pt, section-label[Workstation], ..("Shell · Editor", "Python · CLIs", "Five harnesses").map(chip)),
       )
     ]
   ]
   ```

1. **Compile 2× PNG (primary) and keep `.typ` beside exports** (add `--format svg` only when vector zoom is explicitly needed; Typst outlines SVG text to `<path>` curves so fonts never drift, making 2× PNG smaller and equally sharp):

   ```bash
   cp ~/.agents/themes/typst/fmind.typ docs/assets/fmind.typ
   typst compile --format png --ppi 192 docs/assets/concept.typ docs/assets/concept.png
   # Optional vector export:
   typst compile --format svg docs/assets/concept.typ docs/assets/concept.svg
   ```

1. **Embed with conclusion `alt` text and a full-size link** (plus a prose/table summary nearby):

   ```html
   <a href="docs/assets/concept.png">
     <img src="docs/assets/concept.png" alt="Conclusion the reader should take away" width="960">
   </a>
   ```

1. **Inspect visually**: open/read the rendered `.png` to verify zero stderr font warnings, crisp connectors, unclipped labels, and ≥4.5:1 text contrast.

## Gotchas

- **No `@preview/...` packages in illustrations**: external Universe packages (`fletcher`, `cetz`) trigger network fetches on cold caches and add coordinate boilerplate; stdlib `grid` + `stack` + `line` + `polygon` + `context`/`measure` stays offline and compact.
- **Avoid `width: 100%` at the root of `width: auto` pages**: `100%` of `auto` resolves to `0pt`. Use explicit column widths in `grid(columns: (...))` (`100%` works _inside_ fixed-width columns) or `context { measure(body).width }`.
- **Isolated / CI font & escaping checks**: if running with `--ignore-system-fonts` or an overridden `HOME`, pass `--font-path` pointing to static/variable `Google Sans` and `Google Sans Code` (`~/.local/share/fonts` on Linux, `~/Library/Fonts` on macOS). Treat any Typst stderr warning (`unknown font family`, unescaped `*` math/emphasis) as a hard failure; remember `tile()` renders titles in `Google Sans Code`.

## Documentation

- [Typst styling](https://typst.app/docs/reference/styling/) · [Layout](https://typst.app/docs/reference/layout/) · [Visualize](https://typst.app/docs/reference/visualize/)
- Companions: [d2](d2.md) (routed technical graphs), [svg](svg/GUIDE.md) (logos and raw `<svg>` marks), [draft-doc](../../draft-doc/SKILL.md) (Google Docs `.typ` figures), [draft-typst-deck](../../draft-typst-deck/SKILL.md) (16:9 slide decks & branded PNG/SVG cards).
