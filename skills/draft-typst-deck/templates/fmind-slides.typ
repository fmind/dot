// Fmind light presentation & chart theme for Typst (pure standard library).
// Colors, typography, and flat hierarchy match DESIGN.md.

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

#let fmind-deck(
  title: "",
  context-label: "",
  date: "",
  body,
) = {
  set document(title: title)
  set page(
    width: 960pt,
    height: 540pt,
    margin: (x: 42pt, top: 32pt, bottom: 42pt),
    fill: colors.canvas,
    footer-descent: 12pt,
    footer: context {
      let p = counter(page).get().first()
      let total = counter(page).final().first()
      if p > 1 {
        set text(font: sans-font, size: 10.5pt, fill: colors.muted)
        grid(
          columns: (1fr, auto),
          align: (left + horizon, right + horizon),
          column-gutter: 14pt,
          [#title #if context-label != "" [#h(6pt)·#h(6pt) #context-label] #if date != "" [#h(6pt)·#h(6pt) #date]],
          [*#p* / #total],
        )
      }
    },
  )
  set text(font: sans-font, size: 16pt, fill: colors.foreground)
  set par(leading: 0.6em, spacing: 0.75em)
  set raw(theme: none)
  show raw: set text(font: mono-fonts)
  show raw.where(block: false): it => text(
    font: mono-fonts,
    size: 0.88em,
    fill: colors.primary,
    weight: "semibold",
    it,
  )
  show link: set text(fill: colors.primary, weight: "semibold")
  body
}

#let pill(role: "selection", body) = {
  let styles = (
    primary: (bg: colors.primary, fg: colors.canvas),
    selection: (bg: colors.selection, fg: colors.primary),
    success: (bg: colors.success, fg: colors.canvas),
    success-surface: (bg: colors.success-surface, fg: colors.success),
    warning: (bg: colors.warning, fg: colors.canvas),
    warning-surface: (bg: colors.warning-surface, fg: colors.warning),
    error: (bg: colors.error, fg: colors.canvas),
    error-surface: (bg: colors.error-surface, fg: colors.error),
    information: (bg: colors.information, fg: colors.canvas),
    type: (bg: colors.type, fg: colors.canvas),
    muted: (bg: colors.panel, fg: colors.muted),
  ).at(role, default: (bg: colors.selection, fg: colors.primary))
  box(
    fill: styles.bg,
    radius: 999pt,
    inset: (x: 10pt, y: 3.5pt),
    text(font: sans-font, size: 10pt, weight: "semibold", fill: styles.fg, body),
  )
}

#let cover-slide(
  kicker: none,
  status-pill: "For decision",
  title: "",
  subtitle: "",
  meta: "",
) = {
  set page(
    margin: (x: 54pt, y: 46pt),
    fill: colors.canvas,
    footer: none,
  )
  grid(
    rows: (auto, 1fr, auto),
    row-gutter: 18pt,
    grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      if kicker != none {
        pill(role: "selection", kicker)
      } else {
        none
      },
      if status-pill != none {
        pill(role: "primary", status-pill)
      } else {
        none
      },
    ),
    align(left + horizon)[
      #box(
        width: 100%,
        stroke: (left: 4pt + colors.primary),
        inset: (left: 24pt, y: 8pt),
      )[
        #block(width: 780pt)[
          #set par(leading: 0.45em)
          #text(
            font: sans-font,
            size: 38pt,
            weight: "bold",
            fill: colors.primary,
            title,
          )
          #v(16pt)
          #par(leading: 0.62em)[
            #text(
              font: sans-font,
              size: 18pt,
              weight: "regular",
              fill: colors.foreground,
              subtitle,
            )
          ]
        ]
      ]
    ],
    box(
      width: 100%,
      fill: colors.panel,
      stroke: 1pt + colors.border,
      radius: 12pt,
      inset: (x: 18pt, y: 12pt),
      text(font: sans-font, size: 12pt, weight: "semibold", fill: colors.muted, meta),
    ),
  )
}

#let slide(
  kicker: none,
  title: "",
  takeaway: none,
  body,
) = {
  pagebreak(weak: true)
  if kicker != none {
    pill(role: "selection", kicker)
    v(6pt)
  }
  text(
    font: sans-font,
    size: 26pt,
    weight: "bold",
    fill: colors.primary,
    title,
  )
  if takeaway != none {
    v(5pt)
    text(font: sans-font, size: 15.5pt, weight: "regular", fill: colors.muted, takeaway)
  }
  v(10pt)
  line(length: 100%, stroke: 1pt + colors.border)
  v(14pt)
  body
}

#let kpi-card(value, label, sublabel, role: "primary", height: auto) = {
  let cfg = (
    primary: (fg: colors.primary, pill-bg: colors.selection, pill-fg: colors.primary),
    success: (fg: colors.success, pill-bg: colors.success-surface, pill-fg: colors.success),
    warning: (fg: colors.warning, pill-bg: colors.warning-surface, pill-fg: colors.warning),
    error: (fg: colors.error, pill-bg: colors.error-surface, pill-fg: colors.error),
    information: (fg: colors.information, pill-bg: colors.canvas, pill-fg: colors.information),
  ).at(role, default: (fg: colors.primary, pill-bg: colors.selection, pill-fg: colors.primary))
  box(
    width: 100%,
    height: height,
    fill: colors.panel,
    stroke: 1pt + colors.border,
    radius: 16pt,
    inset: (x: 18pt, y: 14pt),
    align(left, stack(
      spacing: 8pt,
      box(
        fill: cfg.pill-bg,
        radius: 999pt,
        inset: (x: 10pt, y: 3.5pt),
        text(size: 10.5pt, weight: "semibold", fill: cfg.pill-fg, label),
      ),
      text(font: sans-font, size: 38pt, weight: "bold", fill: cfg.fg, value),
      text(size: 14pt, fill: colors.muted, sublabel),
    )),
  )
}

#let card(
  title: none,
  badge: none,
  badge-role: "selection",
  fill: colors.panel,
  stroke: 1pt + colors.border,
  inset: 16pt,
  height: auto,
  body,
) = box(
  width: 100%,
  height: height,
  fill: fill,
  stroke: stroke,
  radius: 16pt,
  inset: inset,
  {
    if title != none {
      grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        column-gutter: 8pt,
        text(font: sans-font, size: 17pt, weight: "bold", fill: colors.foreground, title),
        if badge != none { pill(role: badge-role, badge) },
      )
      v(9pt)
    }
    set text(size: 15.5pt, fill: colors.foreground)
    body
  },
)

#let callout(role: "selection", title: none, body) = {
  let cfg = (
    selection: (bg: colors.selection, border: colors.primary, title-fg: colors.primary),
    success: (bg: colors.success-surface, border: colors.success, title-fg: colors.success),
    warning: (bg: colors.warning-surface, border: colors.warning, title-fg: colors.warning),
    error: (bg: colors.error-surface, border: colors.error, title-fg: colors.error),
    panel: (bg: colors.panel, border: colors.border, title-fg: colors.foreground),
  ).at(role, default: (bg: colors.selection, border: colors.primary, title-fg: colors.primary))
  box(
    width: 100%,
    fill: cfg.bg,
    stroke: (left: 4pt + cfg.border),
    radius: (right: 12pt),
    inset: (x: 18pt, y: 12pt),
    {
      if title != none {
        text(size: 15pt, weight: "bold", fill: cfg.title-fg, title)
        h(6pt)
      }
      set text(size: 14.5pt, fill: colors.foreground)
      body
    },
  )
}

// Pure-Typst comparative chart and step helpers (fixed heights prevent slide overflow).

#let bar-panel(title, subtitle, rows, width: 100%, height: auto) = box(
  width: width,
  height: height,
  fill: colors.panel,
  stroke: 1pt + colors.border,
  radius: 16pt,
  inset: (x: 16pt, y: 12pt),
  stack(
    spacing: 6pt,
    stack(
      spacing: 4pt,
      text(size: 15.5pt, weight: "bold", fill: colors.foreground, title),
      text(size: 12pt, fill: colors.muted, subtitle),
    ),
    line(length: 100%, stroke: 0.75pt + colors.border),
    v(1pt),
    ..rows,
  ),
)

#let stacked-bar-row(
  label,
  segments,
  val-text,
  label-weight: "semibold",
  val-color: colors.foreground,
  left-width: 106pt,
  right-width: 112pt,
) = grid(
  columns: (left-width, 1fr, right-width),
  column-gutter: 10pt,
  align: (left + horizon, left + horizon, right + horizon),
  text(size: 13pt, weight: label-weight, fill: colors.foreground, label),
  box(
    width: 100%,
    height: 18pt,
    radius: 8pt,
    fill: colors.canvas,
    stroke: 0.75pt + colors.border,
    clip: true,
    stack(
      dir: ltr,
      spacing: 0pt,
      ..segments.map(((pct, col)) => rect(width: pct * 1%, height: 18pt, fill: col)),
    ),
  ),
  text(size: 12.5pt, weight: "bold", fill: val-color, val-text),
)

#let broken-bar-row(
  label,
  pct,
  fill-col,
  val-text,
  label-weight: "semibold",
  val-color: colors.foreground,
  broken: false,
  left-width: 102pt,
  right-width: 136pt,
) = grid(
  columns: (left-width, 1fr, right-width),
  column-gutter: 8pt,
  align: (left + horizon, left + horizon, right + horizon),
  text(size: 13pt, weight: label-weight, fill: colors.foreground, label),
  box(
    width: 100%,
    height: 18pt,
    radius: 8pt,
    fill: colors.canvas,
    stroke: 0.75pt + colors.border,
    clip: true,
    {
      if pct > 0 { rect(width: pct * 1%, height: 18pt, fill: fill-col) }
      if broken {
        place(right + horizon, dx: -14pt, rect(width: 4pt, height: 22pt, fill: colors.canvas))
        place(right + horizon, dx: -20pt, rect(width: 4pt, height: 22pt, fill: colors.canvas))
      }
    },
  ),
  text(size: 12.5pt, weight: "bold", fill: val-color, val-text),
)

#let step-card(
  num,
  title,
  desc,
  fill: colors.panel,
  stroke: 1pt + colors.border,
  badge-bg: colors.primary,
  badge-fg: colors.canvas,
  width: 248pt,
  height: 146pt,
) = box(
  width: width,
  height: height,
  fill: fill,
  stroke: stroke,
  radius: 16pt,
  inset: 16pt,
  align(left, stack(
    spacing: 10pt,
    grid(
      columns: (auto, 1fr),
      column-gutter: 10pt,
      align: (left + horizon, left + horizon),
      circle(
        radius: 14pt,
        fill: badge-bg,
        align(center + horizon, text(size: 13.5pt, weight: "bold", fill: badge-fg, str(num))),
      ),
      text(size: 16.5pt, weight: "bold", fill: colors.foreground, title),
    ),
    text(size: 14pt, fill: colors.muted, desc),
  )),
)

#let flow-arrow(label) = align(
  center + horizon,
  stack(
    spacing: 6pt,
    stack(
      dir: ltr,
      spacing: 0pt,
      align(horizon, line(length: 34pt, stroke: 2pt + colors.primary)),
      align(horizon, polygon(fill: colors.primary, (0pt, 0pt), (8pt, 4.5pt), (0pt, 9pt))),
    ),
    text(size: 12pt, weight: "semibold", fill: colors.primary, label),
  ),
)
