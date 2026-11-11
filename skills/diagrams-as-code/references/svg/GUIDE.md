---
name: svg
description: "Hand-authored SVG illustrations for READMEs and user docs: composition, branding, embedding, and visual checks."
---

# SVG Illustration Standard

Hand-authored, diffable SVG illustrations for user-facing docs ([Brain Framework's README](https://github.com/fmind/brain-framework#readme) shows reference loop, before/after, and vocabulary views). [Diagrams as code](../../SKILL.md) owns format selection.

## Workflow

1. **Pick one concept**: loop, before/after, mapping, boundary, or layers—at most 3–7 items per group (split instead of shrinking); READMEs earn a hero plus one SVG per core concept.
1. **Apply the brand**: use customer branding when applicable (ask if missing; never guess or mix brands), else `~/.agents/DESIGN.md`.
1. **Copy [illustration.svg](templates/illustration.svg)**: place in `docs/assets/<concept>.svg` (or dot-prefixed `.github/assets/` in chezmoi repos). Swap only `<style>` hex values and font names for customer brands; preserve the 960px `viewBox` (600px for Google Docs per [draft-doc](../../../draft-doc/SKILL.md)), `role="img"`, `<title>`, `<desc>`, opaque light card, and semantic classes.
1. **Compose on the grid**: columns at `x=32, 320, 704` (64px gutters) or even 2/3-column splits, 34px chips stepping by 42, numbered flow badges, sentence-case headings, code font only for commands/paths/fields, real source names, synthetic examples, and zero invented metrics.
1. **Provide text equivalents**: full mechanism in `<desc>`, conclusion in `alt`, and standalone claim in surrounding prose.
1. **Embed wrapped in a full-size link** (relative path, or raw URL only when republished to PyPI/registries):

   ```html
   <a href="docs/assets/concept.svg">
     <img src="docs/assets/concept.svg" alt="Conclusion the reader should take away" width="960">
   </a>
   ```

1. **Validate and inspect**: run [check_svg.py](scripts/check_svg.py) (`CHROME` overrides browser; else use [playwright](../../../playwright/SKILL.md) with JS and network off) to verify XML, a11y, 12px floor, and `<img>`-sandbox safety, then visually inspect both brand-font and fallback-font renders for overflow, collisions, contrast, and typos:

   ```bash
   python -I ~/.agents/skills/diagrams-as-code/references/svg/scripts/check_svg.py docs/assets/*.svg --render "$(mktemp -d)"
   ```

## Gotchas

- **SVG `<text>` never wraps**: break lines manually and leave ~15% horizontal slack for wider fallback fonts.
- **Design for `<img>` sandboxing**: GitHub and docs strip scripts, external fonts/stylesheets, links, and remote images; never use `<foreignObject>`, raster embeds, or base64 fonts.
- **Preview isolation is not sanitization**: `check_svg.py` blocks scripts and network in Chrome previews, not OS egress; keep its Chrome flags paired.
- **Mask lines behind captions**: place a canvas-colored `<rect>` under text instead of detouring paths.
- **Floor and contrast**: ≥12px type at 960px width and ≥4.5:1 contrast against actual fills; the `<a href>` link handles mobile zoom.

## Documentation

- [MDN SVG reference](https://developer.mozilla.org/en-US/docs/Web/SVG) · [Complex images](https://www.w3.org/WAI/tutorials/images/complex/)
- Companion skills: [fmind-visuals](../../../fmind-visuals/SKILL.md) (brand and template), [repository-docs](../../../repository-docs/SKILL.md) (README journey), [mermaid](../mermaid.md) (technical diagrams).
