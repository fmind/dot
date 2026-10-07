---
name: mermaid
description: "Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering."
---

# Mermaid Diagram Standard

Mermaid is the default format for technical documentation because the same editable text renders in GitHub Markdown and documentation renderers with Mermaid support. Keep the source portable, reviewable, and close to the prose it explains. [Diagrams as code](../SKILL.md) owns the choice between Mermaid, [SVG](svg/GUIDE.md), [D2](d2.md), or no diagram.

## Workflow

1. **Write portable source**: a fenced `mermaid` block when the diagram belongs to one Markdown document, a `.mmd` file when it is reused or rendered independently.
1. **Configure in frontmatter**: put configuration in Mermaid frontmatter, never in `%%{init: ...}%%` directives or renderer-specific fence options; apply the Fmind theme from [fmind-theme](../../fmind-visuals/references/fmind-theme.md) when the work represents Médéric or `www.fmind.dev`.
1. **Validate and render**:

   ```bash
   mmdc -i diagram.mmd -o diagram.svg -b transparent
   ```

1. **Inspect the render**: clipping, line crossings, contrast, spelling, label density, and mobile or slide readability.
1. **Ship the source**: keep the Mermaid text; add SVG only when the target cannot render Mermaid and PNG only when a platform requires raster output, and add `accTitle` and `accDescr` or surrounding prose so the conclusion survives without the image.

## Gotchas

- **Point `mmdc` at system Chrome**: `mmdc` fails with `Could not find chrome-headless-shell` because the Puppeteer browser download is disabled; interactive Fish exports `PUPPETEER_EXECUTABLE_PATH`, otherwise point it at system Chrome: `PUPPETEER_EXECUTABLE_PATH="$(command -v google-chrome)" mmdc -i diagram.mmd -o diagram.svg` (macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`).
- **Set one renderer-stable font stack**: use root-level `config.fontFamily`; late-loading web fonts change label measurements after layout and clip inside fixed bounds.
- **Label clearly, never cryptically**: use clear, self-explanatory labels for nodes, edges, and subgraphs instead of cryptic IDs or abbreviations; diagrams must be effortless for humans to read at a glance in documentation.
- **Omit deprecated `flowchart.htmlLabels`** from new diagrams.
- **Keep shared source portable**: keep remote images, custom JavaScript, click callbacks, and renderer plugins out of shared source.
- **Split dense diagrams**: use separate views instead of shrinking labels; left-to-right for slide-sized processes, top-to-bottom for document hierarchies.
- **Never invent structure**: preserve source terminology; never add metrics, components, trust boundaries, or causal links the evidence does not show.

## Documentation

- [Syntax reference](https://mermaid.js.org/intro/syntax-reference.html) · [Theming](https://mermaid.js.org/config/theming) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
- Releases: [Mermaid](https://github.com/mermaid-js/mermaid/releases) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli/releases)
- Companion skills: [fmind-visuals](../../fmind-visuals/SKILL.md) (Fmind theme), [svg](svg/GUIDE.md) (user-doc illustrations), [d2](d2.md) (bespoke compositions).
