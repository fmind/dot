# Fmind Deck and Diagram Production

### Decks

1. **Scaffold with pnpm**: keep Slidev, Vue, the default theme, and `playwright-chromium` project-local; start from [package.json.template](references/package.json.template), [pnpm-workspace.yaml](references/pnpm-workspace.yaml), [slides.md](references/slides.md), and [style.css](references/style.css), then copy the logo and WOFF2 fonts into `public/brand/`.
1. **Keep the DOMPurify override**: until Monaco no longer pins a vulnerable release; verify any removal with `pnpm audit`.
1. **One idea per slide**: one claim, mechanism, decision, or artifact; split dense content instead of shrinking type.
1. **Embed diagrams**: Mermaid directly for ordinary diagrams; exported LikeC4 or D2 SVGs only when their specialist boundary applies.
1. **Run, build, export**:

   ```bash
   pnpm exec slidev slides.md
   pnpm exec slidev build slides.md
   pnpm exec slidev export slides.md
   ```

1. **Inspect every view**: browser, projector-sized, and exported; prefer Slidev's browser exporter for review PNGs or PPTX and keep CLI PDF export for automation.

### Diagrams

1. **Start with Mermaid**: apply the portable Fmind frontmatter from [fmind-theme](references/fmind-theme.md); use [d2](../d2/SKILL.md) or LikeC4 only when their composition or model advantages outweigh the loss of direct Markdown rendering.
1. **Keep source beside exports**: near the prose or deck that owns the claim; export SVG only for destinations that cannot render Mermaid.
