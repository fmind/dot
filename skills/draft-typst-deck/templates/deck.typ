// Starter 4-slide Fmind executive deck template: one signal and one focal visual per slide.
#import "fmind-slides.typ": *

#show: fmind-deck.with(
  title: "Project Alpha · Q4 Batch Runner Review",
  context-label: "Architecture decision",
  date: "2026-11-13",
)

#cover-slide(
  kicker: "Platform engineering · Decision briefing",
  status-pill: "For decision",
  title: "Promote Worker v3 to cut nightly run cost by 62%",
  subtitle: "Four calm slides: pilot metrics, option comparison, and rollout decision.",
  meta: "Author: Example Team (team@example.com) · Synthetic example",
  note: "Open with the 30-second ask: approve moving nightly batch jobs to Worker v3 with a EUR 200 monthly ceiling.",
)

#slide(
  kicker: "Executive signal",
  title: "Pilot meets 99% reliability while saving 62% per run",
  takeaway: "Measured across 50 nightly workloads in Europe compared against legacy fixed VMs.",
)[
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 16pt,
    kpi-card("EUR 0.42", "Cost per run", "Down from EUR 1.10 baseline", role: "primary", height: 144pt),
    kpi-card("99.2%", "Pass rate", "Up from 84.0% on legacy pool", role: "success", height: 144pt),
    kpi-card("18 min", "Median finish", "Inside the 30-min SLA", role: "information", height: 144pt),
  )
  #v(24pt)
  #callout(role: "selection", title: "Decision needed:")[
    Approve #hl[EUR 200/month compute cap] and pilot cohort by Friday to start Q4 savings next week.
  ]
  #speaker-note("Trade-offs kept off-slide: cold starts add 8-12s on first run, and monorepos over 20 modules split across two runs.")
]

#slide(
  kicker: "Comparative benchmark",
  title: "Eight times fewer manual escalations on identical jobs",
  takeaway: "Worker v3 removes overnight retries and eliminates idle standby compute.",
)[
  #bar-panel(
    "Manual escalations per 50 weekly runs",
    "Lower is better · identical commit triggers in Europe",
    (
      broken-bar-row("Legacy v1", 100, colors.error, "140  (out of scale)", val-color: colors.error, broken: true),
      broken-bar-row("Baseline v2", 44, colors.warning, "22  (non-blocking)", val-color: colors.warning),
      broken-bar-row(
        "Worker v3",
        14,
        colors.success,
        "7  (scoped queue)",
        label-weight: "bold",
        val-color: colors.success,
      ),
    ),
  )
  #v(18pt)
  #split-cards(
    "Stay on Baseline v2",
    [Requires *22 manual interventions* each month and keeps standby VMs idle overnight.],
    "Promote Worker v3",
    [Cuts escalations to *7 scoped items*, enforces schema checks, and costs #hl[EUR 0 idle overnight].],
    left-badge: "Baseline",
    right-badge: "Recommended",
    height: 118pt,
  )
  #speaker-note("Legacy v1 completed 12/50 jobs reliably vs 37/50 on v2 and 50/50 (43 direct + 7 verified fallback) on v3.")
]

#slide(
  kicker: "Rollout plan",
  title: "Three controlled steps from pilot to production",
  takeaway: "Every external write stays gated behind explicit owner approval.",
)[
  #v(8pt)
  #align(center)[
    #grid(
      columns: (auto, auto, auto, auto, auto),
      align: (horizon, horizon, horizon, horizon, horizon),
      column-gutter: 10pt,
      step-card(
        1,
        "Run worker",
        "Deterministic checks inside an isolated job.",
      ),
      flow-arrow("Signal"),
      step-card(
        2,
        "Owner review",
        "Verify scope across 10 volunteer teams.",
        fill: colors.selection,
        stroke: 1.6pt + colors.primary,
      ),
      flow-arrow("Approve"),
      step-card(
        3,
        "Expand cohort",
        "Promote after 30-day stability check.",
        fill: colors.success-surface,
        stroke: 1.6pt + colors.success,
        badge-bg: colors.success,
      ),
    )
  ]
  #v(24pt)
  #callout(role: "success", title: "Owner & next review:")[
    Platform team starts cohort 1 on Monday · acceptance review scheduled at Day 30.
  ]
  #speaker-note("Rollback takes under two minutes by switching the scheduler target back to Baseline v2.")
]
