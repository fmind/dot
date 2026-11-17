---
name: diagrams-as-code
description: "Create and check Typst, D2, Mermaid, and SVG diagrams, VHS terminal demos, and Fmind/client visual variants."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/diagrams-as-code
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Diagrams as Code

Design clear, self-explanatory diagrams and figures whenever architecture boundaries, request/data flows, state lifecycles, or quantitative comparisons benefit from visual intuition (use a clean table or list only when no spatial or sequential relationship exists). Apply customer/employer palette, fonts, and logo when the work belongs to one (ask if missing; never mix brands), preserve existing project identities, or use `~/.agents/DESIGN.md` ([fmind/theme](https://github.com/fmind/theme/blob/main/DESIGN.md)) and pinned `~/.agents/themes/` renderer files (`mise run upgrade` in `fmind/dot` advances them—edit upstream `fmind/theme`, never local copies). Cut decorative chrome, gradients, and generic AI imagery.

| Need                                                                                | Format                                   | Why                                                                 |
| ----------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------- |
| Composed user-doc illustrations: README heroes, landing/concept pages, Docs, slides | [Typst](references/typst.md)             | Pure stdlib + `fmind.typ`; 2× PNG + SVG at ~1/5 raw SVG token cost  |
| Technical architecture & routed graphs: containers, layers, sequences, `.d2` files  | [D2](references/d2.md)                   | Automatic graph routing, nested boundaries, and standalone exports  |
| Platform-locked inline Markdown: GitHub, PRs/issues, `AGENTS.md`, skills, Zensical  | [Mermaid](references/mermaid.md)         | Renders inline where platforms only execute fenced `mermaid` blocks |
| Brand marks, small geometric logos (`96–128 px`), or live-`<text>` `.svg` assets    | [SVG](references/svg/GUIDE.md)           | Self-contained `<svg>` paths/marks and existing `.svg` maintenance  |
| Reproducible CLI / TUI walkthroughs                                                 | [VHS](references/recording/GUIDE.md)     | Executable tape rendered in an isolated HOME                        |
| Open visual direction (logo, cover, hero) or rejected draft                         | [Variants](references/variants/GUIDE.md) | Numbered light/dark contact sheet across distinct axes              |

## Workflow

Load the matching format guide (plus [variants](references/variants/GUIDE.md) when visual direction is open), keep editable sources beside exports, visually read every rendered PNG/SVG frame to verify alignment, unclipped `>= 12px` labels, font loading, `>= 4.5:1` contrast, and dark/light surface legibility, and audit non-trivial figures with `fmind-review-figures` / `fmind-review-design` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [d2](references/d2.md): D2 sources, standalone layouts, theming, and exports.
- [mermaid](references/mermaid.md): Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering.
- [recording](references/recording/GUIDE.md): Record reproducible, isolated terminal demos with VHS, ttyd, and FFmpeg.
- [svg](references/svg/GUIDE.md): Self-contained SVG logos, geometric marks, and live-text SVG assets: branding, embedding, and visual checks.
- [typst](references/typst.md): Composed illustrations and cards in pure Typst stdlib: branding, layout, 2x PNG/SVG export, and checks.
- [variants](references/variants/GUIDE.md): Numbered logo, cover, or illustration variant rounds with a light and dark contact sheet.

<!-- guides:end -->
