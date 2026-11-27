// Starter deck: zero prose paragraphs, concise micro-phrases (~40-90w visual live, ~60-110w async; appendix: true for Annex/Sources), one focal visual/slide, and nuance in speaker notes.
#import "fmind-slides.typ": *

#show: fmind-deck.with(
  title: "Q4 Compute Vendor Proposal",
  context-label: "Engineering",
  date: "2026-11-14",
)

#cover-slide(
  kicker: "Decision",
  status-pill: "For decision",
  title: "Approve Provider B before Friday",
  subtitle: [Cuts spend #hl(role: "success-surface")[38%] with identical SLA],
  meta: "Infrastructure · Nov 14",
  note: "Open directly with the decision ask: approve signing Provider B before Friday 17:00 CET to lock Q4 pricing. Emphasize that no customer-facing APIs change.",
)

#slide(
  kicker: "Signal",
  title: [Provider B saves #hl[\$42k] per year],
  takeaway: "14-day shadow replay.",
  note: "Annual baseline spend drops from $110k to $68k under committed capacity. Reliability telemetry matches 99.9% SLA over shadow replay traffic.",
)[
  #v(14pt)
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 18pt,
    kpi-card("-38%", "Annual spend", "$68k vs $110k", role: "success", height: 120pt),
    kpi-card("99.9%", "Shadow SLA", "Zero drops", role: "primary", height: 120pt),
    kpi-card("2 weeks", "Cutover", "Zero downtime", role: "information", height: 120pt),
  )
  #v(14pt)
  #text(size: 11pt, fill: colors.muted)[Source: Q3 telemetry.]
]

#slide(
  kicker: "Benchmark",
  title: "Provider B halves tail latency",
  takeaway: "10k replay requests.",
  note: "Provider A peaked at 96 ms under regional failover; Provider B held 42 ms due to colocated storage nodes. Provider C spiked to 410 ms under regional failover (broken axis).",
)[
  #v(16pt)
  #bar-panel(
    "P95 latency",
    "Lower is better",
    (
      broken-bar-row("Provider B", 32, colors.primary, "42 ms", right-width: 120pt),
      broken-bar-row("Provider A", 74, colors.information, "96 ms", right-width: 120pt),
      broken-bar-row("Provider C", 96, colors.warning, "410 ms", broken: true, right-width: 120pt),
    ),
  )
  #v(10pt)
  #text(size: 11pt, fill: colors.muted)[Source: Replay benchmark.]
]

#slide(
  kicker: "Rollout",
  title: "Cut over in three stages",
  takeaway: "Rollback ready anytime.",
  note: "Step 1 executes legal terms by Nov 20. Step 2 mirrors 50% traffic with automated error budget halts. Step 3 retires Provider A once metrics hold for 7 days.",
)[
  #v(24pt)
  #grid(
    columns: (1fr, auto, 1fr, auto, 1fr),
    align: horizon,
    column-gutter: 8pt,
    step-card(1, "Sign", "Lock Q4 rate", width: 100%, height: 156pt),
    flow-arrow("W1"),
    step-card(2, "Shadow 50%", "Auto rollback", fill: colors.selection, stroke: 1.5pt + colors.primary, width: 100%, height: 156pt),
    flow-arrow("W2"),
    step-card(3, "Cut over", "Dec 1 live", width: 100%, height: 156pt),
  )
]
