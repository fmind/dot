# Fmind Visual Theme

The brand tokens live in [SKILL.md](../SKILL.md) and [www.fmind.dev](https://www.fmind.dev/). Use these snippets when a renderer needs the theme in its own syntax.

Use generous space, crisp geometry, restrained indigo, and evidence-led labels. Avoid gradients, decorative illustration, generic AI imagery, and dense dashboards unless the content requires them.

## Brand Palettes

### Fmind (Articles and Documents)

Calm, exact, spacious, technically grounded. Crisp geometry and editable diagrams over decorative imagery.

| Token      | Value     | Token      | Value     |
| ---------- | --------- | ---------- | --------- |
| Background | `#0F172A` | Muted      | `#CBD5E1` |
| Panel      | `#1E293B` | Primary    | `#646CFF` |
| Foreground | `#F8FAFC` | Border     | `#334155` |

Released artifacts use Outfit headings and Inter body text. The Typst deck template uses an installed sans-serif fallback until those TTF files are copied into the deliverable.

### Bleeding Agent (Media and Podcast)

Forensic, sharp, darkly playful. Cyan, magenta, and red diagnostics; black-box imagery, terminal texture, warning marks, protocol traces, failure boundaries.

| Token      | Value     | Token   | Value     |
| ---------- | --------- | ------- | --------- |
| Background | `#061321` | Cyan    | `#00E5FF` |
| Panel      | `#0B2034` | Magenta | `#FF2AA1` |
| Foreground | `#F7FAFC` | Red     | `#FF3158` |
| Muted      | `#A7BBCB` | Border  | `#16364F` |

## Portable Mermaid Frontmatter

Use Mermaid's `base` theme because it is customizable. This form stays inside the Mermaid source and works in `.mmd` files and Markdown fences when the target renderer supports frontmatter.

```mermaid
---
config:
  fontFamily: "ui-sans-serif, system-ui, sans-serif"
  flowchart:
    diagramPadding: 16
  theme: base
  themeVariables:
    darkMode: true
    background: "#0F172A"
    primaryColor: "#1E293B"
    primaryTextColor: "#F8FAFC"
    primaryBorderColor: "#646CFF"
    secondaryColor: "#334155"
    secondaryTextColor: "#F8FAFC"
    secondaryBorderColor: "#646CFF"
    tertiaryColor: "#0F172A"
    tertiaryTextColor: "#CBD5E1"
    tertiaryBorderColor: "#334155"
    lineColor: "#CBD5E1"
    textColor: "#F8FAFC"
    noteBkgColor: "#1E293B"
    noteTextColor: "#F8FAFC"
    noteBorderColor: "#646CFF"
---
flowchart LR
  Evidence --> Decision --> Outcome
```

For a renderer without Mermaid frontmatter support, move the same configuration into its site-level Mermaid configuration. Keep Mermaid on the root-level system sans stack so label measurements remain stable across renderers.

## D2

An Fmind article diagram imports [diagram.d2](diagram.d2) and uses its classes on a light surface. The diagram surface remains light because the site supports reader-selected light and dark themes, where a light figure still reads as a bounded panel.

| Class       | Means                                              |
| ----------- | -------------------------------------------------- |
| `group`     | A labelled boundary holding other shapes          |
| `container` | A major building block the article names          |
| `component` | A leaf part inside a container                     |
| `actor`     | A human or calling system where the flow enters    |
| `external`  | Something outside the boundary being described    |
| `step`      | One numbered stage of a sequence                   |
| `terminal`  | Where a flow starts or stops                       |

Elsewhere, start from a built-in D2 theme and use `theme-overrides` or `dark-theme-overrides` under `vars.d2-config`. Supply all eight `--font-*` flags together with copied Inter TTF files when exact font rendering matters.
