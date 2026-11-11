---
name: diagrams-as-code
description: "Create and check Mermaid, SVG, and D2 diagrams, VHS terminal demos, and Fmind/client visual variants."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diagrams-as-code
  created: "2026-09-16"
  updated: "2026-11-11"
---

# Diagrams as Code

Choose the simplest picture that explains the system, or none when prose, a list, or a table is more direct. Apply customer/employer palette, fonts, and logo when the work belongs to one (ask if missing; never mix brands), preserve existing project identities, or use `~/.agents/DESIGN.md` ([fmind/theme](https://github.com/fmind/theme/blob/main/DESIGN.md)) and pinned `~/.agents/themes/` renderer files (`mise run upgrade` in `fmind/dot` advances them—edit upstream `fmind/theme`, never local copies). Cut decorative nodes, gradients, and generic AI imagery.

| Need                                                                          | Format                                   | Why                                                        |
| ----------------------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| Technical docs: AGENTS.md, skills, architecture, contributor, reference       | [Mermaid](references/mermaid.md)         | Renders in Markdown and GitHub; maintainers edit structure |
| User docs: README, documentation-site landing and concept pages, courses      | [SVG](references/svg/GUIDE.md)           | Composed, branded illustration that carries one concept    |
| Existing `.d2` sources, Fmind-branded D2 diagrams, bespoke standalone layouts | [D2](references/d2.md)                   | Containers, layers, and exports Mermaid cannot express     |
| Reproducible CLI / TUI walkthroughs                                           | [VHS](references/recording/GUIDE.md)     | Executable tape rendered in an isolated HOME               |
| Open visual direction (logo, cover, hero) or rejected draft                   | [Variants](references/variants/GUIDE.md) | Numbered light/dark contact sheet across distinct axes     |

## Workflow

Read only the matching guide and its required resources, inspect every rendered frame or image for legibility, clipping, fonts, and contrast, and keep editable sources beside exports.

## Task guides

<!-- guides:start -->

- [d2](references/d2.md): D2 sources, standalone layouts, theming, and exports.
- [mermaid](references/mermaid.md): Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering.
- [recording](references/recording/GUIDE.md): Record reproducible, isolated terminal demos with VHS, ttyd, and FFmpeg.
- [svg](references/svg/GUIDE.md): Hand-authored SVG illustrations for READMEs and user docs: composition, branding, embedding, and visual checks.
- [variants](references/variants/GUIDE.md): Numbered logo, cover, or illustration variant rounds with a light and dark contact sheet.

<!-- guides:end -->
