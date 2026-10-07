---
name: fmind-visuals
description: "Create Typst decks, VHS terminal demos, and logo or cover variants in Fmind or client branding."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fmind-visuals
  created: "2026-07-16"
  updated: "2026-10-07"
---

# Fmind Visual Communication

Apply the customer's brand when the work belongs to one; otherwise the Fmind identity from [fmind-theme.md](references/fmind-theme.md): readable typography, spacious composition, and evidence-backed claims. [Technical publishing](../technical-publishing/SKILL.md) owns article production.

## Workflow

1. **Select the format** while respecting an explicitly requested format or an existing project: Typst for talks and slide decks, VHS for reproducible terminal demonstrations. [Diagrams as code](../diagrams-as-code/SKILL.md) owns diagrams and illustrations (Mermaid, SVG, and D2, including Fmind article diagrams).
1. **Apply the brand**: use the customer's palette, fonts, and logo when the repository or engagement specifies them; ask for its brand guide rather than guessing. Otherwise use Google Sans for headings and body text, Google Sans Code for code, and the palette from [fmind/theme](https://github.com/fmind/theme). Bundle the fonts with their OFL notices and use the existing reviewed logo. Keep colors, text roles, and contrast aligned with the source theme; [fmind-theme.md](references/fmind-theme.md) lists the full palette. Preserve published assets when branding changes.
1. **Explore variants** when the look is open (logo, cover, hero illustration, deck theme) or the user rejects a draft: follow [variants](references/variants.md) instead of iterating on one guess.
1. **Create**: follow [production.md](references/production.md) for decks and Fmind diagram branding, or [recording.md](references/recording.md) for VHS demos; keep the tape and synthetic inputs.
1. **Verify**: compile success is not visual success. Inspect every rendered page, frame, or diagram for legibility, clipping, font loading, and accessibility, and keep editable sources beside their exports.

## Gotchas

- **Cut decoration**: remove decorative nodes, gradients, and generic AI imagery.

## Task guides

<!-- guides:start -->

- [variants](references/variants.md): Numbered logo, cover, illustration, or deck-theme variant rounds with a light and dark contact sheet.

<!-- guides:end -->

## Documentation

- [Fmind website](https://www.fmind.dev/) · [Typst](https://typst.app/docs/) · [Mermaid](https://mermaid.js.org/) · [D2](https://d2lang.com/)
- Releases: [Typst](https://github.com/typst/typst/releases)
- [VHS documentation](https://github.com/charmbracelet/vhs) · Releases: [VHS](https://github.com/charmbracelet/vhs/releases)
- Companion skills: [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid, SVG, and D2) and [technical-publishing](../technical-publishing/SKILL.md) (Fmind articles).
