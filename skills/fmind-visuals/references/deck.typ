// This native Typst deck stays self-contained. For release, vendor Outfit and
// Inter TTF files, change these names, and compile with --font-path fonts.
#let heading-font = "DejaVu Sans"
#let body-font = "DejaVu Sans"

#let background = rgb("#0F172A")
#let panel = rgb("#1E293B")
#let foreground = rgb("#F8FAFC")
#let muted = rgb("#CBD5E1")
#let primary = rgb("#646CFF")
#let border = rgb("#334155")

#set document(title: "Presentation title", author: "Médéric Hurier (Fmind)")
#set page(
  width: 16cm,
  height: 9cm,
  margin: 0cm,
  fill: background,
)
#set text(font: body-font, size: 15pt, fill: foreground)
#set par(leading: 0.7em, spacing: 0.45em)
#set list(indent: 1em, body-indent: 0.5em, spacing: 0.35em, marker: [#text(
  fill: primary,
)[•]])

#let slide(title: none, body) = {
  block(width: 100%, height: 100%, inset: (
    x: 1.2cm,
    top: 0.85cm,
    bottom: 0.65cm,
  ))[
    #if title != none [
      #text(font: heading-font, size: 24pt, weight: "bold")[#title]
      #v(0.45cm)
    ]
    #body
  ]
  pagebreak(weak: true)
}

#slide[
  #align(left + horizon)[
    #text(font: heading-font, size: 34pt, weight: "bold")[Presentation title]
    #v(0.35cm)
    #text(size: 18pt, fill: muted)[One concrete tension, decision, or mechanism]
    #v(0.8cm)
    #text(size: 11pt, fill: primary)[Médéric Hurier · Fmind]
  ]
]

#slide(title: [One idea per slide])[
  - Start from concrete friction.
  - Show the mechanism or evidence.
  - End with a decision boundary.
]

#slide(title: [Portable diagrams stay editable])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.6cm,
    rect(fill: panel, stroke: border, radius: 5pt, inset: 12pt)[
      #text(weight: "bold", fill: primary)[Mermaid]
      #v(0.2cm)
      Flows, sequences, states, classes, and ER diagrams.
    ],
    rect(fill: panel, stroke: border, radius: 5pt, inset: 12pt)[
      #text(weight: "bold", fill: primary)[D2]
      #v(0.2cm)
      Article figures and bespoke standalone compositions.
    ],
  )
]
