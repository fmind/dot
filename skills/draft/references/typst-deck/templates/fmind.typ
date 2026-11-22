// Fmind light theme and diagram components for Typst (standard library only).
// Docs: https://typst.app/docs/reference/styling/ · https://typst.app/docs/reference/scripting/#modules
//
// Copy fmind.typ beside your .typ sources and import it:
//
//   #import "fmind.typ": *
//   #show: fmind-diagram
//
// Colors, typography, chart series and diagram-* components match DESIGN.md.

#let colors = (
  canvas: rgb("#ffffff"),
  panel: rgb("#f1f3f4"),
  border: rgb("#9aa0a6"),
  muted: rgb("#595d62"),
  foreground: rgb("#202124"),
  primary: rgb("#174ea6"),
  focus: rgb("#4285f4"),
  selection: rgb("#d2e3fc"),
  error: rgb("#a50e0e"),
  error-accent: rgb("#ea4335"),
  error-surface: rgb("#fad2cf"),
  warning: rgb("#934900"),
  warning-accent: rgb("#e37400"),
  highlight: rgb("#fbbc04"),
  warning-surface: rgb("#feefc3"),
  success: rgb("#0d652d"),
  success-accent: rgb("#34a853"),
  success-surface: rgb("#ceead6"),
  type: rgb("#681da8"),
  information: rgb("#00636d"),
)

// Categorical chart order from DESIGN.md: neutral hues precede green and red.
#let chart-series = (
  colors.primary,
  colors.information,
  colors.warning,
  colors.type,
  colors.success,
  colors.error,
)

#let sans-font = "Google Sans"
#let mono-fonts = ("Google Sans Code", "DejaVu Sans Mono")

// Paged document show rule for reports, notes and handouts.
// Pass code-theme: "fmind.tmTheme" (from themes/bat/) for syntax-highlighted code blocks;
// the default `none` keeps fenced blocks monochrome on palette colors instead of Typst's stock theme.
#let fmind-doc(paper: "a4", margin: 24mm, size: 11pt, code-theme: none, body) = {
  set page(paper: paper, margin: margin, fill: colors.canvas)
  set text(font: sans-font, size: size, fill: colors.foreground)
  set par(leading: 0.65em)
  set raw(theme: code-theme)
  show heading: set text(font: sans-font, weight: "bold", fill: colors.foreground)
  show heading.where(level: 1): set text(size: 20pt, fill: colors.primary)
  show heading.where(level: 2): set text(size: 15pt, fill: colors.primary)
  show heading.where(level: 3): set text(size: 12.5pt, fill: colors.primary)
  show link: set text(fill: colors.primary)
  show raw.where(block: false): set text(font: mono-fonts, size: 0.92em, fill: colors.primary)
  show raw.where(block: true): it => block(
    width: 100%,
    fill: colors.panel,
    radius: 9pt,
    inset: 10pt,
    text(font: mono-fonts, size: 9.5pt, fill: colors.foreground, it),
  )
  set table(
    stroke: 0.75pt + colors.border,
    inset: (x: 8pt, y: 6pt),
    fill: (_, y) => if y == 0 { colors.panel } else { colors.canvas },
  )
  show table.cell.where(y: 0): set text(weight: "semibold", fill: colors.foreground)
  set quote(block: true)
  show quote.where(block: true): it => block(
    width: 100%,
    stroke: (left: 2pt + colors.primary),
    inset: (left: 12pt, y: 3pt),
    if it.attribution != none {
      stack(spacing: 4pt, it.body, text(size: 0.9em, fill: colors.muted)[— #it.attribution])
    } else {
      it.body
    },
  )
  show figure.caption: set text(size: 9.5pt, fill: colors.muted)
  body
}

// Auto-sized canvas show rule for composed diagrams and illustrations.
#let fmind-diagram(margin: 4pt, fill: colors.canvas, size: 11pt, body) = {
  set page(width: auto, height: auto, margin: margin, fill: fill)
  set text(font: sans-font, size: size, fill: colors.foreground)
  set raw(theme: none)
  show link: set text(fill: colors.primary)
  show raw.where(block: false): set text(font: mono-fonts, size: 0.92em, fill: colors.primary)
  body
}

#let muted(body) = text(size: 0.89em, fill: colors.muted, body)
#let mono(body, fill: colors.primary, weight: "bold") = text(font: mono-fonts, weight: weight, fill: fill, body)
#let section-label(body) = align(center, text(size: 0.86em, weight: "semibold", fill: colors.muted, body))

#let frame(
  fill: colors.canvas,
  stroke: 1pt + colors.border,
  radius: 12pt,
  inset: (x: 24pt, y: 20pt),
  body,
) = box(fill: fill, stroke: stroke, radius: radius, inset: inset, body)

#let status-badge(role: "primary", body) = {
  let bg = (
    primary: colors.primary,
    error: colors.error,
    warning: colors.warning,
    success: colors.success,
    information: colors.information,
    type: colors.type,
  ).at(role, default: colors.primary)
  box(
    fill: bg,
    radius: 999pt,
    inset: (x: 8pt, y: 3pt),
    text(size: 0.82em, weight: "semibold", fill: colors.canvas, body),
  )
}

#let step-badge(n, fill: colors.primary) = circle(
  radius: 8.5pt,
  fill: fill,
  align(center + horizon, text(fill: colors.canvas, weight: "bold", size: 9.5pt, str(n))),
)

// The seven semantic diagram-* components from DESIGN.md.
#let diagram-group(title, width: auto, inset: 12pt, radius: 9pt, body) = box(
  width: width,
  fill: colors.panel,
  stroke: 1pt + colors.border,
  radius: radius,
  inset: inset,
  stack(
    spacing: 8pt,
    text(size: 0.86em, weight: "semibold", fill: colors.muted, title),
    body,
  ),
)

#let diagram-container(
  width: auto,
  fill: colors.selection,
  inset: 12pt,
  radius: 9pt,
  body,
) = box(
  width: width,
  fill: fill,
  stroke: 1.6pt + colors.primary,
  radius: radius,
  inset: inset,
  text(fill: colors.foreground, body),
)

#let diagram-component(
  width: auto,
  inset: (x: 10pt, y: 7pt),
  radius: 6pt,
  body,
) = box(
  width: width,
  fill: colors.canvas,
  stroke: 1pt + colors.border,
  radius: radius,
  inset: inset,
  text(fill: colors.foreground, body),
)

#let diagram-actor(
  width: auto,
  inset: (x: 12pt, y: 7pt),
  radius: 999pt,
  body,
) = box(
  width: width,
  fill: colors.success-surface,
  stroke: 1.6pt + colors.success,
  radius: radius,
  inset: inset,
  text(fill: colors.foreground, body),
)

#let diagram-external(
  width: auto,
  inset: (x: 10pt, y: 7pt),
  radius: 6pt,
  body,
) = box(
  width: width,
  fill: colors.canvas,
  stroke: (paint: colors.border, thickness: 1pt, dash: (4pt, 3pt)),
  radius: radius,
  inset: inset,
  text(fill: colors.muted, body),
)

#let diagram-step(
  width: auto,
  inset: (x: 10pt, y: 7pt),
  radius: 6pt,
  body,
) = box(
  width: width,
  fill: colors.warning-surface,
  stroke: 1pt + colors.warning,
  radius: radius,
  inset: inset,
  text(fill: colors.foreground, body),
)

#let diagram-terminal(
  width: auto,
  inset: (x: 12pt, y: 7pt),
  radius: 6pt,
  body,
) = box(
  width: width,
  fill: colors.foreground,
  stroke: 1pt + colors.foreground,
  radius: radius,
  inset: inset,
  text(fill: colors.canvas, body),
)

// Composed card, chip, tile and flow helpers for concept illustrations.
#let chip(width: 176pt, radius: 999pt, body) = box(
  width: width,
  fill: colors.panel,
  radius: radius,
  inset: (x: 10pt, y: 6.5pt),
  align(center, text(fill: colors.foreground, body)),
)

#let tile(
  title,
  subtitle,
  width: 220pt,
  fill: colors.selection,
  stroke: none,
  title-fill: colors.primary,
) = box(
  width: width,
  fill: fill,
  stroke: stroke,
  radius: 8pt,
  inset: (x: 10pt, y: 7pt),
  align(center, stack(spacing: 4pt, mono(title, fill: title-fill), muted(subtitle))),
)

#let flow-arrow(step: none, caption: none, length: 34pt, dir: ltr) = {
  let shaft = if dir in (ltr, rtl) {
    line(length: length, stroke: 1.6pt + colors.primary)
  } else {
    line(angle: 90deg, length: length, stroke: 1.6pt + colors.primary)
  }
  let tip = if dir == ltr {
    polygon(fill: colors.primary, (0pt, 0pt), (7pt, 3.8pt), (0pt, 7.6pt))
  } else if dir == rtl {
    polygon(fill: colors.primary, (7pt, 0pt), (0pt, 3.8pt), (7pt, 7.6pt))
  } else if dir == ttb {
    polygon(fill: colors.primary, (0pt, 0pt), (7.6pt, 0pt), (3.8pt, 7pt))
  } else {
    polygon(fill: colors.primary, (3.8pt, 0pt), (7.6pt, 7pt), (0pt, 7pt))
  }
  let arrow = if dir == ltr {
    stack(dir: ltr, spacing: 0pt, align(horizon, shaft), align(horizon, tip))
  } else if dir == rtl {
    stack(dir: ltr, spacing: 0pt, align(horizon, tip), align(horizon, shaft))
  } else if dir == ttb {
    stack(dir: ttb, spacing: 0pt, align(center, shaft), align(center, tip))
  } else {
    stack(dir: ttb, spacing: 0pt, align(center, tip), align(center, shaft))
  }
  let items = ()
  if step != none { items.push(step-badge(step)) }
  items.push(arrow)
  if caption != none { items.push(muted(caption)) }
  align(center + horizon, stack(spacing: 5pt, ..items))
}

#let loop-back(caption, step: none, inset-x: 88pt, fill: colors.canvas, body) = context {
  let w = calc.max(0pt, measure(body).width - 2 * inset-x)
  let tag = if step != none {
    stack(dir: ltr, spacing: 6pt, step-badge(step), align(horizon, caption))
  } else {
    caption
  }
  stack(
    spacing: 6pt,
    body,
    pad(
      left: inset-x,
      right: inset-x,
      bottom: 8pt,
      box(
        width: w,
        height: 22pt,
        stroke: (
          left: 1.6pt + colors.primary,
          right: 1.6pt + colors.primary,
          bottom: 1.6pt + colors.primary,
        ),
        radius: (bottom: 7pt),
      )[
        #place(
          top + left,
          dx: -3.8pt,
          dy: -2pt,
          polygon(fill: colors.primary, (3.8pt, 0pt), (7.6pt, 7pt), (0pt, 7pt)),
        )
        #place(
          bottom + center,
          dy: 8.5pt,
          box(fill: fill, inset: (x: 8pt, y: 1pt), tag),
        )
      ],
    ),
  )
}
