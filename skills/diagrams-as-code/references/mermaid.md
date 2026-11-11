---
name: mermaid
description: "Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering."
---

# Mermaid Diagram Standard

Default technical-doc diagram format: one portable source renders in GitHub Markdown and Mermaid-enabled docs. [Diagrams as code](../SKILL.md) owns choosing Mermaid, [SVG](svg/GUIDE.md), [D2](d2.md), or prose.

## Workflow

1. **Write portable source**: inline `mermaid` fence for a single page, or `.mmd` when reused or exported standalone.
1. **Configure via frontmatter**: never use `%%{init: ...}%%` or renderer-specific fence flags; apply the Fmind frontmatter from [renderers](../../fmind-visuals/references/renderers.md) for Médéric or `www.fmind.dev`.
1. **Validate and render** with project-pinned `mmdc` (`mise use --pin npm:@mermaid-js/mermaid-cli`; not installed globally):

   ```bash
   mmdc -i diagram.mmd -o diagram.svg -b transparent
   ```

1. **Inspect the render**: check clipping, crossings, contrast, spelling, label density, and mobile/slide legibility.
1. **Ship source first**: add SVG/PNG exports only when the target lacks Mermaid rendering, and include `accTitle`/`accDescr` or surrounding prose stating the conclusion.

## Gotchas

- **Point `mmdc` at system Chrome**: Puppeteer downloads are disabled (`Could not find chrome-headless-shell`). Interactive Fish sets `PUPPETEER_EXECUTABLE_PATH`; elsewhere pass `PUPPETEER_EXECUTABLE_PATH="$(command -v google-chrome || command -v chromium)" mmdc -i diagram.mmd -o diagram.svg` (macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`).
- **Exempt reviewed `chromium-bidi` pins**: `chrome-devtools-npm` publishes `chromium-bidi` without trusted-publisher provenance; review the exact version and scope `"npm:@mermaid-js/mermaid-cli" = { version = "<exact>", trust_policy_excludes = ["chromium-bidi@<version>"] }`.
- **Set a stable font stack**: declare root `config.fontFamily` so late web fonts do not clip labels; pass `--no-font-embed` when the host page provides fonts (`mmdc` 12 embeds ~170 KB of default fonts).
- **Pin layout and look across Mermaid 11/12**: Mermaid 12 (`mmdc`, Zensical 0.0.73+) defaults to ELK (ignoring `flowchart.diagramPadding`) and `neo`; set root `config.layout: dagre` and `config.look: classic` to match Mermaid 11 renderers.
- **Disable HTML labels for non-browser SVG consumers**: set root `config.htmlLabels: false` (omit deprecated `flowchart.htmlLabels`) before importing into docs, ImageMagick, or librsvg, which drop `<foreignObject>` text.
- **Keep source portable and grounded**: no remote images, JS callbacks, renderer plugins, cryptic IDs, or unverified components/metrics; split crowded diagrams (`LR` for processes, `TD` for hierarchies).

## Documentation

- [Syntax reference](https://mermaid.js.org/intro/syntax-reference.html) · [Theming](https://mermaid.js.org/config/theming) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
- Releases: [Mermaid](https://github.com/mermaid-js/mermaid/releases) · [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli/releases)
- Companion skills: [fmind-visuals](../../fmind-visuals/SKILL.md) (Fmind theme), [svg](svg/GUIDE.md) (user-doc illustrations), [d2](d2.md) (bespoke compositions).
