# Fmind Deck and Diagram Production

## Decks

1. **Start from the local template**: copy [deck.typ](../templates/deck.typ) into the deliverable. It uses native Typst only and compiles without downloading a package.
1. **Apply the release fonts**: copy Google Sans and Google Sans Code TTF files into `fonts/` and compile with `--ignore-system-fonts --font-path fonts`, so a missing family prints `warning: unknown font family` instead of resolving to an installed copy; Typst still exits 0, so treat that warning as a failure.
1. **Embed diagrams as exports**: render Mermaid or D2 to SVG, keep the source beside it, and use `#image("diagram.svg", alt: "...")` in the deck.
1. **Format, compile, and watch** with `typst` and `typstyle` declared in the deck's project (`mise use --pin typst typstyle`; the workstation does not install them globally):

   ```bash
   typstyle -i deck.typ
   typst compile --ignore-system-fonts --font-path fonts --pdf-standard ua-1 deck.typ deck.pdf
   typst watch --ignore-system-fonts --font-path fonts deck.typ deck.pdf
   ```

1. **Export review images**: use `typst compile --ignore-system-fonts --font-path fonts deck.typ 'slide-{p}.png'` when a page-by-page review or social preview is useful.
1. **Inspect every page**: review the PDF at projector and mobile-preview sizes, because fixed bounds can clip dense content; confirm contrast and clipping before distribution. `--pdf-standard ua-1` already fails the build on a missing document title or image alt text.

## Diagrams

[Diagrams as code](../../diagrams-as-code/SKILL.md) owns the format choice and each format's procedure; Fmind work adds only the brand.

1. **Set every font slot**: use the eight static-face mappings in [renderers.md](renderers.md).
1. **Start Fmind article diagrams** from [diagram.d2](../templates/diagram.d2) on a light surface, and apply the portable Fmind frontmatter from [renderers.md](renderers.md) to Mermaid.
