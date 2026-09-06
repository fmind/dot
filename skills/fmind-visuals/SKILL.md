---
name: fmind-visuals
description: Apply the Fmind visual identity and route slide or diagram work to Slidev, Mermaid, LikeC4, or D2. Use for Fmind talks, decks, article diagrams, site assets.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fmind-visuals
  created: "2026-07-16"
  updated: "2026-09-05"
---

# Fmind Visual Communication

Apply the Fmind visual identity from [fmind-theme.md](references/fmind-theme.md). Preserve readable typography, spacious composition, and evidence-backed claims; [technical-publishing](../technical-publishing/SKILL.md) owns article production.

## Workflow

1. **Select the format** from the table and respect an explicitly requested format or existing project.
1. **Apply the brand**: use Outfit headings, Inter body text, and the reference's tokens; article diagrams use the light-surface [D2 template](references/diagram.d2). Copy fonts and logos into the deliverable.
1. **Create**: follow [production.md](references/production.md) for deck setup and exports; start decks from [package.json.template](references/package.json.template), [pnpm-workspace.yaml](references/pnpm-workspace.yaml), [slides.md](references/slides.md), and [style.css](references/style.css).
1. **Verify**: inspect every rendered and exported view for legibility, clipping, loading fonts, and accessibility; keep editable source with its exports.

## Canonical Tool Choice

| Need                                                        | Tool                           | Boundary                                                  |
| ----------------------------------------------------------- | ------------------------------ | --------------------------------------------------------- |
| Slides, talks, workshops, LinkedIn documents                | [Slidev](https://sli.dev)      | Default for every new deck                                |
| Flow, sequence, state, class, ER, compact technical diagram | [Mermaid](../mermaid/SKILL.md) | Default for every new diagram                             |
| Fmind article diagram                                       | [D2](../d2/SKILL.md)           | Import [diagram.d2](references/diagram.d2), light surface |
| Durable architecture model with multiple generated views    | [LikeC4](https://likec4.dev/)  | Use when the model, not one image, is the source of truth |
| Existing D2 source or bespoke standalone composition        | [D2](../d2/SKILL.md)           | Specialist fallback                                       |

Do not create a custom HTML deck, Typst deck, PowerPoint source, or generated raster diagram unless the user explicitly requests that format or an existing project requires it.

## Gotchas

- **Interactive success is not export success**: inspect the PDF or PNG; fixed bounds clip late-loading fonts.
- **Decoration**: every node and slide carries one evidence-backed thesis; remove decorative nodes, gradients, and generic AI imagery.
- **Accessibility**: diagrams need a prose equivalent or alt text; text stays legible on a laptop, projector, mobile preview, and exported page.
- **Private paths**: copy brand assets into the deliverable; never link local workspace paths from a published artifact.

## Official Skills

For a LikeC4 model, install the CLI with `pnpm add -D likec4` in its project, commit `pnpm-lock.yaml`, and invoke it with `pnpm exec likec4`.

Upstream: `slidevjs/slidev` (decks) and `likec4/likec4` (architecture models). List the current release, then install what the task needs at project scope after reviewing the snapshot (see [native skill tooling](https://skills.sh/docs/cli)):

```bash
skills add slidevjs/slidev --list
skills add slidevjs/slidev --skill <name> -y
skills add likec4/likec4 --list
skills add likec4/likec4 --skill <name> -y
```

## Documentation

- [Fmind website](https://www.fmind.dev/) · [Slidev](https://sli.dev) · [Mermaid](https://mermaid.js.org/) · [LikeC4](https://likec4.dev/) · [D2](https://d2lang.com/)
- Companion skills: [mermaid](../mermaid/SKILL.md) (default diagrams), [d2](../d2/SKILL.md) (specialist diagrams), [technical-publishing](../technical-publishing/SKILL.md) (Fmind articles), [native skill tooling](https://skills.sh/docs/cli) (upstream skill install).
