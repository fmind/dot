# Outlines and Reader Lenses

Pick the outline matching the reader's decision and required technical depth. Drop empty sections, close substantive deliverables with a visible `Sources` section (primary link, what it grounds, and date/version), and collapse bulky raw logs or derivations into annexes.

## Message & Short Updates

### Email or chat message

No headings, zero backtick spam, 1–2 sentences per paragraph:

1. **Lead signal**: the answer, news, or ask in sentence 1 with the key phrase bolded (skip callout boxes on routine mail and chat; reserve a brief callout for formal multi-stakeholder approvals or incident notices).
1. **Why it matters**: 2–3 sentences with the key figure and baseline, answering every question raised in the thread.
1. **Next step**: one owner and date/timezone (optional short bullet list of ≤4 items).

### Status update

1. **One-line pulse**: status pill (🟢 On track · 🟡 Trade-off · 🔴 Blocked) plus headline change.
1. **Key signal & proof**: concrete milestones achieved since the last update (metric vs baseline).
1. **Decisions / Help needed**: exact ask, owner, and deadline.

### PR description

Lead with user/operator effect and preserve technical _why_ for squash-merge history — never dump raw file lists or test transcripts:

1. **Summary & root cause**: what changes for users/operators, why the root cause occurred, and key design trade-offs (include screenshots or diagrams when UI or architecture changes).
1. **Verification**: exact gates, edge cases, and live/browser checks executed (use `<details>` only for benchmark tables or trace summaries).
1. **Rollout / Risks**: migration, feature flag, backwards compatibility, or rollback steps (omit if trivial).

## Decision Docs & Reports

### Decision memo or 1-pager (flexible target ~300–500 words)

1. **Visual summary card**: takeaway + decisive number + **Decision needed by DATE**.
1. **Options comparison**: compact 3–4 column table (include _Do nothing_; visually highlight the recommended row).
1. **Risks & flip conditions**: top 2–3 risks with mitigations, plus what would reverse the choice.
1. **Next steps & Sources**: owner + date per action, followed by visible primary `Sources` (optional collapsible annex for long formulas).

### Executive analysis, technical RFC, or audit report

1. **Executive summary (or KPI strip, never both stacked)**: plain 1–2 sentence takeaway, primary metric vs baseline, and explicit decision or scope (keep filter exclusions and denominator methodology in `Sources & Annexes`).
1. **Architecture / Findings**: literal conclusion-led headings, clean diagrams/charts/tables ([primitives](primitives.md)), exact mechanisms, boundaries, and trade-offs.
1. **Edge cases, risks, & sensitivity**: failure modes, security/cost bounds, assumptions, and flip conditions.
1. **Implementation / Next steps**: sequenced actions with owners, verification gates, and rollback plan.
1. **Sources (& Annexes)**: visible primary sources naming what each link grounds plus date/version; `<details>` or a dedicated `Annexes` tab for filter exclusions, formulas, and raw benchmarks/logs.

## Decks (Typically 6 to 12 Slides, Scaled to Evidence)

Build presentations in [draft-typst-deck](../../draft-typst-deck/SKILL.md) with an assertion-evidence spine, ~30 visible words target per slide (up to ~45 on label-rich comparative charts with units and sample sizes), and one focal visual per slide:

1. **Cover**: clear title, subject kicker, audience/date metadata.
1. **Situation / Signal**: 1 core shift or baseline metric vs target.
1. **Recommendation**: decision needed, expected gain, owner, and date.
1. **Comparison / Proof (2 to 4 slides)**: one bar panel, flow diagram, or 2–3-card trade-off per slide.
1. **Risks & Next Steps**: top mitigation paired with dated actions; full nuance goes in speaker notes.

## Reader Lenses

Match the opening frame to who decides:

| Reader          | First question                     | Highlight first                                     |
| --------------- | ---------------------------------- | --------------------------------------------------- |
| Executive / VP  | What decision, cost, or risk?      | Recommendation, net impact range, deadline          |
| Security lead   | What data moves and who controls?  | Data boundary, access model, failure/audit controls |
| Finance / Buyer | Total cost, drivers, commitments?  | Monthly/annual range, break-even, lock-in           |
| Tech lead       | Does it scale and how painful ops? | Architecture visual, latency/reliability, ops load  |
