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

## Workflow

1. **Pick the format**: [typst](references/typst.md) for composed doc/README/web illustrations and cards (`fmind.typ`, 2× PNG + SVG); [d2](references/d2.md) for routed architecture/container/sequence graphs; [mermaid](references/mermaid.md) where platforms render only fenced `mermaid` (GitHub, PRs, Zensical); [svg](references/svg/GUIDE.md) for geometric logos/marks (`96–128 px`) and `.svg` assets; [recording](references/recording/GUIDE.md) for isolated VHS CLI/TUI demos; [variants](references/variants/GUIDE.md) when visual direction is open or a draft was rejected.
1. **Render & verify visually**: keep editable sources beside exports, read every rendered PNG/SVG frame to verify alignment, unclipped `>= 12px` labels, font loading, `>= 4.5:1` contrast, and dark/light surface legibility, and audit non-trivial figures with `fmind-review-figures` / `fmind-review-design` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [d2](references/d2.md): D2 sources, standalone layouts, theming, and exports.
- [mermaid](references/mermaid.md): Technical-doc diagrams in Markdown and GitHub: syntax, validation, and rendering.
- [recording](references/recording/GUIDE.md): Record reproducible, isolated terminal demos with VHS, ttyd, and FFmpeg.
- [svg](references/svg/GUIDE.md): Self-contained SVG logos, geometric marks, and live-text SVG assets: branding, embedding, and visual checks.
- [typst](references/typst.md): Composed illustrations and cards in pure Typst stdlib: branding, layout, 2x PNG/SVG export, and checks.
- [variants](references/variants/GUIDE.md): Numbered logo, cover, or illustration variant rounds with a light and dark contact sheet.

<!-- guides:end -->

## Documentation

- [Typst](https://typst.app/docs/) · [D2](https://d2lang.com/tour/intro/) · [Mermaid](https://mermaid.js.org/intro/) · [VHS](https://github.com/charmbracelet/vhs) · [fmind/theme](https://github.com/fmind/theme)
- Releases: [Typst](https://github.com/typst/typst/releases) · [D2](https://github.com/d2lang/d2/releases) · [VHS](https://github.com/charmbracelet/vhs/releases)
- Companions: [draft-typst-deck](../draft-typst-deck/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [documentation-site](../documentation-site/SKILL.md), [repository-docs](../repository-docs/SKILL.md), [web-frontend](../web-frontend/SKILL.md).
