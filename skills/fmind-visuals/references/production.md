# Fmind Deck and Diagram Production

## Decks

1. **Start from the local template**: copy [deck.typ](../templates/deck.typ) into the deliverable. It uses native Typst only and compiles without downloading a package.
1. **Apply the release fonts**: copy Google Sans and Google Sans Code TTF files into `fonts/` and pass `--font-path fonts`. Confirm both families load before exporting; do not silently ship fallback fonts.
1. **Keep one idea per slide**: use one claim, mechanism, decision, or artifact; split dense content instead of shrinking type.
1. **Embed diagrams as exports**: render Mermaid or D2 to SVG, keep the source beside it, and use `#image("diagram.svg", alt: "...")` in the deck.
1. **Format, compile, and watch**:

   ```bash
   typstyle -i deck.typ
   typst compile --font-path fonts deck.typ deck.pdf
   typst watch --font-path fonts deck.typ deck.pdf
   ```

1. **Export review images**: use `typst compile --font-path fonts deck.typ 'slide-{p}.png'` when a page-by-page review or social preview is useful.
1. **Inspect every page**: review the PDF at projector and mobile-preview sizes, because fixed bounds can clip dense content; confirm font loading, contrast, clipping, and alt text before distribution.

## Diagrams

[Diagrams as code](../../diagrams-as-code/SKILL.md) owns the format choice and each format's procedure; Fmind work adds only the brand.

1. **Set every font slot**: use the eight static-face mappings in [fmind-theme.md](fmind-theme.md). Within Pub, `pub render diagram` supplies them from `assets/fonts/`; new article diagrams import `assets/fmind/diagram-v2.d2`. Keep previous imports and rendered assets intact.
1. **Start Fmind article diagrams** from [diagram.d2](../templates/diagram.d2) on a light surface, and apply the portable Fmind frontmatter from [fmind-theme.md](fmind-theme.md) to Mermaid.
