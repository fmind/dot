---
name: diagrams-as-code
description: "Create and check Mermaid, SVG, and D2 diagrams and README illustrations."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diagrams-as-code
  created: "2026-09-16"
  updated: "2026-10-05"
---

# Diagrams as Code

Choose the simplest picture that explains the system, or none when prose, a list, or a table is more direct. This skill owns the format choice; [fmind-visuals](../fmind-visuals/SKILL.md) owns brand, decks, and terminal demos.

| Need                                                                       | Format                           | Why                                                        |
| -------------------------------------------------------------------------- | -------------------------------- | ---------------------------------------------------------- |
| Technical docs: AGENTS.md, skills, architecture, contributor, reference    | [Mermaid](references/mermaid.md) | Renders in Markdown and GitHub; maintainers edit structure |
| User docs: README, documentation-site landing and concept pages, courses   | [SVG](references/svg/GUIDE.md)   | Composed, branded illustration that carries one concept    |
| Existing `.d2` sources, Fmind article diagrams, bespoke standalone layouts | [D2](references/d2.md)           | Containers, layers, and exports Mermaid cannot express     |

## Workflow

Read only the matching guide and its required resources. Use a known guide directly when shared prerequisites are not needed.

## Task guides

<!-- guides:start -->

- [d2](references/d2.md): D2 sources, standalone layouts, theming, and exports.
- [mermaid](references/mermaid.md): Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering.
- [svg](references/svg/GUIDE.md): Hand-authored SVG illustrations for READMEs and user docs: composition, branding, embedding, and visual checks.

<!-- guides:end -->
