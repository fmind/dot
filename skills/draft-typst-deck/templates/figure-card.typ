// Standalone branded visual card (renders safely at width: 640pt for docs, slides, or web).
#import "fmind-slides.typ": *

#show: brand-card.with(width: 640pt)

#stack(
  spacing: 12pt,
  text(size: 18pt, weight: "bold", fill: colors.primary, [Batch ingestion cost drops #hl(role: "success-surface")[38%] after consolidation]),
  grid(
    columns: (1fr, 1fr),
    column-gutter: 12pt,
    kpi-card("$68k", "Annual spend", "Down from $110k baseline", role: "success"),
    kpi-card("42 ms", "P95 latency", "Verified across 10k requests", role: "primary"),
  ),
  callout(role: "selection", title: "Next step:")[Approve vendor cutover before Thursday 17:00 CET.],
)
