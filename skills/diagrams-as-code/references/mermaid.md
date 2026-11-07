---
name: mermaid
description: "Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering."
---

# Mermaid Diagram Standard

Mermaid is the default format for technical documentation because the same editable text renders in GitHub Markdown and documentation renderers with Mermaid support. Keep the source portable, reviewable, and close to the prose it explains. [Diagrams as code](../SKILL.md) owns the choice between Mermaid, [SVG](svg/GUIDE.md), [D2](d2.md), or no diagram.

## Workflow

1. **Write portable source**: a fenced `mermaid` block when the diagram belongs to one Markdown document, a `.mmd` file when it is reused or rendered independently.
1. **Configure in frontmatter**: put configuration in Mermaid frontmatter, never in `%%{init: ...}%%` directives or renderer-specific fence options; apply the Fmind frontmatter from [renderers](../../fmind-visuals/references/renderers.md) when the work represents Médéric or `www.fmind.dev`.
1. **Validate and render** with `mmdc`, declared in the project because the workstation does not install it globally: `mise use --pin npm:@mermaid-js/mermaid-cli`.

   ```bash
   mmdc -i diagram.mmd -o diagram.svg -b transparent
   ```

1. **Inspect the render**: clipping, line crossings, contrast, spelling, label density, and mobile or slide readability.
1. **Ship the source**: keep the Mermaid text; add SVG only when the target cannot render Mermaid and PNG only when a platform requires raster output, and add `accTitle` and `accDescr` or surrounding prose so the conclusion survives without the image.

## Gotchas

- **Point `mmdc` at system Chrome**: `mmdc` fails with `Could not find chrome-headless-shell` because the Puppeteer browser download is disabled; interactive Fish exports `PUPPETEER_EXECUTABLE_PATH`, other shells set it: `PUPPETEER_EXECUTABLE_PATH="$(command -v google-chrome || command -v chromium)" mmdc -i diagram.mmd -o diagram.svg`. Debian arm64 has no Google Chrome build, so it uses Chromium; on macOS use `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- **Review rejected Puppeteer dependencies**: the npm install can reject `chromium-bidi` because Chromium's `chrome-devtools-npm` account publishes it without trusted-publisher evidence. Review that exact version, then exempt only it in the tool's options: `"npm:@mermaid-js/mermaid-cli" = { version = "<exact>", trust_policy_excludes = ["chromium-bidi@<version>"] }`.
- **Set one renderer-stable font stack**: use root-level `config.fontFamily`; late-loading web fonts change label measurements after layout and clip inside fixed bounds. `mmdc` 12 embeds its bundled fonts (about 170 KB) into SVGs that keep the default font; pass `--no-font-embed` when the page supplies the font.
- **Pin the layout and look**: Mermaid 12 (local `mmdc`, Zensical 0.0.73+) defaults to ELK and the `neo` look (drop shadows, heavier arrows), while renderers still on Mermaid 11 use dagre and `classic`; set root-level `config.layout: dagre` and `config.look: classic` so previews match them. ELK also ignores `flowchart.diagramPadding`.
- **Use plain SVG labels in exports**: set root-level `config.htmlLabels: false` when an exported SVG leaves the browser (document import, ImageMagick, librsvg); default labels sit in `<foreignObject>`, which those renderers drop, leaving empty boxes. Omit the deprecated `flowchart.htmlLabels`.
- **Keep shared source portable**: keep remote images, custom JavaScript, click callbacks, and renderer plugins out of shared source.
- **Read at a glance**: self-explanatory labels instead of IDs, the source's own terms, separate views instead of shrunken labels (left-to-right for processes, top-to-bottom for hierarchies), and no metrics, components, or links the evidence does not show.

## Documentation

- [Syntax reference](https://mermaid.js.org/intro/syntax-reference.html) · [Theming](https://mermaid.js.org/config/theming) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
- Releases: [Mermaid](https://github.com/mermaid-js/mermaid/releases) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli/releases)
- Companion skills: [fmind-visuals](../../fmind-visuals/SKILL.md) (Fmind theme), [svg](svg/GUIDE.md) (user-doc illustrations), [d2](d2.md) (bespoke compositions).
