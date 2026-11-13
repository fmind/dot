// Starter 4-slide Fmind executive deck template (compile and inspect PNGs before sharing).
#import "fmind-slides.typ": *

#show: fmind-deck.with(
  title: "Project Alpha · Q4 Batch Runner Review",
  context-label: "Architecture decision",
  date: "2026-11-13",
)

#cover-slide(
  kicker: "Platform engineering · Architecture review",
  status-pill: "For decision",
  title: "Project Alpha: Q4 Rollout and FinOps Verdict",
  subtitle: "Four slides to decide production promotion, monthly compute ceiling, and target operational ownership.",
  meta: "Author: Example Team (team@example.com) · Pilot Benchmark · Synthetic Example",
)

#slide(
  kicker: "Executive summary",
  title: "Promote Worker v3 to cut nightly unit cost by 62%",
  takeaway: "Headless batch execution lowers spend to EUR 0.42 per run while meeting the 99% verification SLA.",
)[
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 16pt,
    kpi-card("EUR 0.42", "Cost per run", "Measured on 50 pilot jobs", role: "primary", height: 128pt),
    kpi-card("99.2%", "Check pass rate", "Up from 84.0% on legacy pool", role: "success", height: 128pt),
    kpi-card("18 min", "Median turnaround", "Inside the 30-min SLA ceiling", role: "information", height: 128pt),
  )
  #v(12pt)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    card(title: "What changes in production", badge: "Validated", badge-role: "success", height: 164pt)[
      - Nightly jobs run on managed workers in `europe-west1`.
      - Strict schema check blocks broken downstream exports.
      - Zero idle VMs overnight (*EUR 0* baseline spend).
    ],
    card(title: "Measured trade-offs and limits", badge: "To monitor", badge-role: "warning-surface", height: 164pt)[
      - Cold starts add *8–12 s* on the first regional run.
      - Monorepos (>20 modules) need split scheduling.
      - Partner approval remains human before write actions.
    ],
  )
]

#slide(
  kicker: "Comparative benchmark",
  title: "Higher pass rate with 8x fewer manual escalations",
  takeaway: "Worker v3 eliminates manual retries while keeping monthly spend under the EUR 200 cap.",
)[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 18pt,
    bar-panel(
      "Validated completions (out of 50)",
      "Worker v3 native (43) + fallback check (7) = 50 / 50",
      (
        stacked-bar-row("Legacy v1", ((24.0, colors.muted),), "12  (24%)", val-color: colors.muted),
        stacked-bar-row("Baseline v2", ((74.0, colors.focus),), "37  (74%)", val-color: colors.primary),
        stacked-bar-row(
          "Worker v3",
          ((86.0, colors.primary), (14.0, colors.success)),
          "43 + 7 (100%)",
          label-weight: "bold",
          val-color: colors.success,
        ),
      ),
    ),
    bar-panel(
      "Manual escalations required",
      "Lower is better · broken bar = legacy outlier",
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
    ),
  )
  #v(14pt)
  #callout(role: "selection", title: "Scope note:")[
    Measured on 50 representative test workloads in `europe-west1`; unit counts compare identical job triggers (`1` run per commit).
  ]
]

#slide(
  kicker: "Target workflow and decisions",
  title: "Three steps to production without team friction",
  takeaway: "Isolate compute in one worker, triage in one queue, and act only after explicit owner approval.",
)[
  #align(center)[
    #grid(
      columns: (auto, auto, auto, auto, auto),
      align: (horizon, horizon, horizon, horizon, horizon),
      column-gutter: 10pt,
      step-card(
        1,
        "Run worker",
        "Executes deterministic checks inside an isolated container.",
      ),
      flow-arrow("Report"),
      step-card(
        2,
        "Owner review",
        "Service owners validate exposure before widening scope.",
        fill: colors.selection,
        stroke: 1.6pt + colors.primary,
      ),
      flow-arrow("Approve"),
      step-card(
        3,
        "Target fix",
        "Opens a verified change only after explicit sign-off.",
        fill: colors.success-surface,
        stroke: 1.6pt + colors.success,
        badge-bg: colors.success,
      ),
    )
  ]
  #v(14pt)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 16pt,
    card(title: "Decision 1 — Monthly ceiling", badge: "Required", badge-role: "primary")[
      Approve *EUR 200/month* worker alert cap on `project-alpha` (`Recommended`).
    ],
    card(title: "Decision 2 — Rollout cohort", badge: "Next sprint", badge-role: "selection")[
      Start with *10 volunteer pilot teams*, then review acceptance rate after 30 days.
    ],
  )
]
