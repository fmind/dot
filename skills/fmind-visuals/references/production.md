# Fmind Deck and Diagram Production

## Decks

1. **Start from the local template**: copy [deck.typ](deck.typ) into the deliverable. It uses native Typst only and compiles without downloading a package.
1. **Apply the release fonts**: copy Outfit and Inter TTF files into `fonts/`, update the two font names near the top of `deck.typ`, and pass `--font-path fonts`. The installed sans-serif default keeps drafts reproducible before those brand assets arrive.
1. **Keep one idea per slide**: use one claim, mechanism, decision, or artifact; split dense content instead of shrinking type.
1. **Embed diagrams as exports**: render Mermaid or D2 to SVG, keep the source beside it, and use `#image("diagram.svg", alt: "...")` in the deck.
1. **Format, compile, and watch**:

   ```bash
   typstyle -i deck.typ
   typst compile deck.typ deck.pdf
   typst watch deck.typ deck.pdf
   ```

1. **Export review images**: use `typst compile deck.typ 'slide-{p}.png'` when a page-by-page review or social preview is useful.
1. **Inspect every page**: review the PDF at projector and mobile-preview sizes; confirm font loading, contrast, clipping, and alt text before distribution.

## Diagrams

1. **Start with Mermaid**: apply the portable Fmind frontmatter from [fmind-theme.md](fmind-theme.md), then render with the external Mermaid renderer when the destination cannot render source directly.
1. **Use D2 for its specialist boundary**: start Fmind article diagrams from [diagram.d2](diagram.d2), or retain an existing D2 source for a bespoke standalone composition.
1. **Keep source beside exports**: store `.mmd` or `.d2` with its SVG and the prose or deck that owns the claim.

```bash
mmdc -i diagram.mmd -o diagram.svg
d2 diagram.d2 diagram.svg
```
