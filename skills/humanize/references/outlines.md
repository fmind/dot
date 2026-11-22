# Outlines and Reader Lenses

Default to a **busy executive or cross-functional leader** lens following [humanize](../SKILL.md) (check prior messages for sensitivities, avoid bad surprises, lead with take-home/impact, and keep inline clickable sources).

## Message & Short Updates

### Email or chat message

Target `<= 60–80`w (`3–5` lines) for chat and `<= 120–150`w (`~100`w replies) for email. No headings, zero backticks, 1–2 sentences/paragraph, `<= 4` single-line bullets:

1. **Lead signal**: answer, take-home, or ask in sentence 1 with 1–2 bold phrases (skip callouts, `<mark>`, `<hr>`, and tables on routine mail/chat).
1. **Why it matters ("so what")**: 1–2 sentences with 1 decisive figure + baseline and inline link to the backing dashboard/doc; answer every open thread question.
1. **Next step & sources**: one owner + weekday/timezone deadline; add a compact `Sources:` line or thread reply only when 2+ references need attribution.

### Status update

1. **One-line pulse**: status pill (🟢 On track · 🟡 Trade-off · 🔴 Blocked) + headline shift.
1. **Key signal & impact**: 1–3 curated milestones/figures vs baseline linking the live dashboard, doc, or release (impact, not a task log).
1. **Decisions / Help needed**: exact ask, owner, and deadline.

### PR description

Lead with user/operator effect and preserve technical _why_ for squash-merge history — never dump raw file lists or test transcripts:

1. **Summary & root cause**: what changes for users/operators, why the root cause occurred, and key design trade-offs (include screenshots or diagrams when UI or architecture changes).
1. **Verification**: exact gates, edge cases, and live/browser checks executed (use `<details>` only for benchmark tables or trace summaries).
1. **Rollout / Risks**: migration, feature flag, backwards compatibility, or rollback steps (omit if trivial).

## Decision Docs & Reports

### Executive brief or 1-pager (default target ~250–400 words)

1. **Take-home card**: headline insight + 1–3 curated figures vs baseline + **Decision needed by DATE**.
1. **Options comparison**: compact 3–4 column table (include _Do nothing_; visually highlight the recommended row).
1. **Risks & flip conditions**: top 2–3 risks with mitigations, plus what would reverse the choice.
1. **Next steps & Sources**: owner + date per action, followed by visible primary `Sources` (optional collapsible annex for long formulas).

### Deep-dive analysis, technical RFC, or audit report (opt-in when depth is requested)

1. **Executive summary (or KPI strip, never both stacked)**: plain 1–2 sentence takeaway, primary metric vs baseline, and explicit decision or scope (keep filter exclusions and denominator methodology in `Sources & Annexes`).
1. **Architecture / Findings**: literal conclusion-led headings, clean diagrams/charts/tables ([primitives](primitives.md)), exact mechanisms, boundaries, and trade-offs.
1. **Edge cases, risks, & sensitivity**: failure modes, security/cost bounds, assumptions, and flip conditions.
1. **Implementation / Next steps**: sequenced actions with owners, verification gates, and rollback plan.
1. **Sources (& Annexes)**: visible primary sources naming what each link grounds plus date/version; `<details>` or a dedicated `Annexes` tab for filter exclusions, formulas, and raw benchmarks/logs.

## Decks (Typically 6 to 12 Slides, Scaled to Evidence)

Build presentations in [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md) (Typst PDF/Retina PPTX) or [draft/slides](../../draft/references/slides/GUIDE.md) (native editable Slides) with an assertion-evidence spine, ~30 visible words target per slide (up to ~45 on label-rich comparative charts with units and sample sizes), and one focal visual per slide:

1. **Cover**: clear title, subject kicker, audience/date metadata.
1. **Situation / Signal**: 1 core shift or baseline metric vs target.
1. **Recommendation**: decision needed, expected gain, owner, and date.
1. **Comparison / Proof (2 to 4 slides)**: one bar panel, flow diagram, or 2–3-card trade-off per slide.
1. **Risks & Next Steps**: top mitigation paired with dated actions; put subtle source footnotes/links on data slides and full references/nuance in speaker notes (or an Appendix slide).

## Reader Lenses

Match the opening frame to who decides (default to **Busy leader / Executive** unless writing a peer-engineer PR/RFC):

| Reader                     | First question                      | Highlight first                                                 |
| -------------------------- | ----------------------------------- | --------------------------------------------------------------- |
| Busy leader / VP (default) | What is the take-home, impact, ask? | Recommendation, 1–3 curated figures vs baseline, risk, deadline |
| Security lead              | What data moves and who controls?   | Data boundary, access model, failure/audit controls             |
| Finance / Buyer            | Total cost, drivers, commitments?   | Monthly/annual range, break-even, lock-in                       |
| Tech lead (opt-in)         | Does it scale and how painful ops?  | Architecture visual, latency/reliability, ops load              |
