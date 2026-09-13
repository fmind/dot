---
name: fmind-visuals
description: Create Fmind decks, diagrams, and terminal demos with Typst, Mermaid, D2, and VHS. Use for talks, article visuals, recordings, and site assets.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fmind-visuals
  created: "2026-07-16"
  updated: "2026-09-13"
---

# Fmind Visual Communication

Apply the Fmind identity from [fmind-theme.md](references/fmind-theme.md): readable typography, spacious composition, and evidence-backed claims. [Technical publishing](../technical-publishing/SKILL.md) owns article production.

## Workflow

1. **Select the format** from the table while respecting an explicitly requested format or an existing project.
1. **Apply the brand**: use Google Sans for headings and body text, Google Sans Code for code, and the palette from [fmind/theme](https://github.com/fmind/theme). Bundle the fonts with their OFL notices and use the existing reviewed logo. Keep colors, text roles, and contrast aligned with the source theme; [fmind-theme.md](references/fmind-theme.md) lists the full palette. Preserve published assets when branding changes.
1. **Create**: follow [production.md](references/production.md); start decks from [deck.typ](references/deck.typ), ordinary diagrams with [Mermaid](../mermaid/SKILL.md), and article diagrams from the light-surface [D2 template](references/diagram.d2).
1. **Verify**: run `typstyle`, compile with `typst`, and inspect every rendered page or diagram for legibility, clipping, font loading, and accessibility. Keep editable sources beside their exports.

## Canonical Tool Choice

| Need                                                        | Tool                           | Boundary                                                                                                                   |
| ----------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| Fmind talk or slide deck                                    | Typst                          | Start from [deck.typ](references/deck.typ); retain source and export PDF                                                   |
| Flow, sequence, state, class, ER, compact technical diagram | [Mermaid](../mermaid/SKILL.md) | Default for every new diagram                                                                                              |
| Fmind article diagram                                       | [D2](../d2/SKILL.md)           | Import [diagram.d2](references/diagram.d2), light surface                                                                  |
| Existing D2 source or bespoke standalone composition        | [D2](../d2/SKILL.md)           | Specialist fallback                                                                                                        |
| Reproducible terminal demonstration                         | VHS                            | Follow [recording](references/recording.md) and adapt [demo.tape](templates/demo.tape); keep the tape and synthetic inputs |

## Gotchas

- **Compile success is not visual success**: inspect the PDF or PNG at projector and mobile-preview sizes; fixed bounds can clip dense content.
- **One thesis per page**: use one claim, mechanism, decision, or artifact; split dense content instead of shrinking type.
- **Decoration**: remove decorative nodes, gradients, and generic AI imagery.
- **Accessibility**: diagrams need a prose equivalent or alt text, and text must retain readable contrast and size.
- **External diagrams**: render Mermaid or D2 to SVG before embedding it in Typst; keep the `.mmd` or `.d2` source beside the export.

## Official Skills

Typst is invoked directly for decks; Mermaid and D2 use their companion skills in this catalog. No additional upstream skill bundle is required.

## Documentation

- [Fmind website](https://www.fmind.dev/) · [Typst](https://typst.app/docs/) · [Mermaid](https://mermaid.js.org/) · [D2](https://d2lang.com/)
- Releases: [Typst](https://github.com/typst/typst/releases)
- [VHS documentation](https://github.com/charmbracelet/vhs) · Releases: [VHS](https://github.com/charmbracelet/vhs/releases)
- Companion skills: [mermaid](../mermaid/SKILL.md) (default diagrams), [d2](../d2/SKILL.md) (specialist diagrams), and [technical-publishing](../technical-publishing/SKILL.md) (Fmind articles).
