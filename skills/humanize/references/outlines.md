# Outlines and Reader Lenses

Pick the shortest outline that serves the reader's decision. Drop empty sections and keep deep methodology/sources collapsible or in backup annexes.

## Message & Short Updates

### Email or chat message

No headings, zero backtick spam, 1–2 sentences per paragraph:

1. **Lead signal**: the answer, news, or ask in sentence 1 (bolded or in a brief callout when decisive).
1. **Why it matters**: 2–3 sentences with the key figure and baseline.
1. **Next step**: one owner and date/timezone (optional short bullet list of ≤4 items).

### Status update

1. **One-line pulse**: status pill (🟢 On track · 🟡 Trade-off · 🔴 Blocked) plus headline change.
1. **Key signal & proof**: 1–3 highlights achieved since the last update (metric vs baseline).
1. **Decisions / Help needed**: exact ask, owner, and deadline.

### PR description

Lead with operator/user effect — never dump file lists or test-runner transcripts:

1. **Summary**: what changes for users/operators and why (1–3 crisp bullets; include a screenshot or diagram when UI/architecture changes).
1. **Verification**: focused proof run (`mise run check`, affected integration tests) without pasting raw logs.
1. **Rollout / Risks**: migration, feature flag, or rollback notes (omit if trivial).

## Decision Docs & Reports

### Decision memo or 1-pager (target 250–450 words)

1. **Visual summary card**: takeaway + decisive number + **Decision needed by DATE**.
1. **Options comparison**: compact 3-column table (include _Do nothing_; visually highlight the recommended row).
1. **Risks & flip conditions**: top 2–3 risks with mitigations, plus what would reverse the choice.
1. **Next steps**: owner + date per action (optional collapsible annex for formulas/sources).

### Executive analysis or cost estimate

1. **Visual summary + KPI strip**: top 2–3 numbers vs baseline + recommendation.
1. **Findings**: one short literal heading per finding, bold opening takeaway, and one visual chart/table ([primitives](primitives.md)).
1. **Sensitivity / Limits**: key assumptions and uncertain inputs driving the range.
1. **Collapsible Annexes**: methodology, formulas, sources (collapse under details blocks in Markdown or backup section in HTML).

## Decks (6 to 10 Slides)

Build every presentation in [draft-typst-deck](../../draft-typst-deck/SKILL.md) with a clear arc, max 30 visible words, and one focal visual per slide:

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
