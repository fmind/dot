# Outlines and Reader Lenses

Default to a **busy colleague or leader** lens per [humanize](../SKILL.md): check prior messages, avoid surprises, lead with the take-home and mental model, and keep inline clickable sources.

## Message & Short Updates

### Email or chat message

Target `<= 60–80`w (`3–5` lines) for chat and `<= 120–150`w (`~100`w replies) for email. No headings, zero backticks, 1–2 sentences/paragraph, `<= 4` single-line bullets:

1. **Lead signal**: answer, take-home, or ask in sentence 1 with 1–2 bold phrases (skip callouts, `<mark>`, `<hr>`, and tables on routine mail/chat).
1. **Why it matters ("so what")**: 1–2 sentences with 1 decisive figure + baseline and inline link to the backing doc/dashboard; answer every open thread question.
1. **Next step & sources**: one owner + deadline; add a compact `Sources:` line or thread reply only when 2+ references need attribution.

### Status update

1. **One-line pulse**: status pill (🟢 On track · 🟡 Trade-off · 🔴 Blocked) + headline shift.
1. **Key signal & impact**: 1–3 curated figures vs baseline linking the live dashboard, doc, or release (impact, not a task log).
1. **Decisions / Help needed**: exact ask, owner, and deadline.

### PR description

Lead with user/operator effect and preserve technical _why_ for squash-merge history; never dump raw file lists or test transcripts:

1. **Summary & root cause**: user/operator change, root cause, and key trade-offs (add screenshots or diagrams for UI/architecture changes).
1. **Verification**: exact gates, edge cases, and live/browser checks (`<details>` only for benchmark tables or traces).
1. **Rollout / Risks**: migration, feature flag, compatibility, or rollback steps (omit if trivial).

## Decision Docs & Reports

### Colleague note or explainer (default ~150–250 words)

Use for internal notes, meeting prep, tool explainers, or quick comparisons—skip executive-summary boxes, `Do nothing` rows, and methodology annexes:

1. **Lead & mental model**: 1–2 plain sentences stating the answer or familiar contrast before naming tools.
1. **Key takeaways (2–3 points or 1 visual/table)**: short single-line points (`<= 12`w each) or one crisp diagram/table.
1. **Next step & 1-line note**: one dated ask if needed, plus one closing caveat/date line and links if helpful.

### Executive brief or 1-pager (decision default ~250–400 words)

1. **Take-home card**: headline insight + 1–3 figures vs baseline + **Decision needed by DATE**.
1. **Options comparison**: compact 3–4 column table (include _Do nothing_ when comparing investments; highlight the recommended row).
1. **Risks & what would reverse it**: top 2–3 plain risks with mitigations, plus the clear trigger that changes the choice.
1. **Next steps & Sources**: owner + date per action, then visible primary `Sources` (optional annex for formulas).

### Deep-dive analysis, technical RFC, or audit report (opt-in)

1. **Executive summary (or KPI strip, never both)**: 1–2 sentence takeaway, primary metric vs baseline, and explicit decision/scope (keep exclusions in `Sources & Annexes`).
1. **Architecture / Findings**: conclusion-led headings, visuals/tables ([primitives](primitives.md)), exact mechanisms, boundaries, and trade-offs.
1. **Edge cases, risks & sensitivity**: failure modes, security/cost bounds, assumptions, and reversal triggers.
1. **Implementation / Next steps**: sequenced actions with owners, verification gates, and rollback plan.
1. **Sources (& Annexes)**: primary sources with date/version and what each grounds; `<details>` or an `Annexes` tab for raw logs.

## Decks (6–12 Slides, Scaled to Evidence)

Build decks in [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md) (Typst PDF/PPTX) or [draft/slides](../../draft/references/slides/GUIDE.md) (native Slides). Keep **zero prose paragraphs** on slides: every slide uses **kicker pill + assertion title (`<= 10`w) + 1-line takeaway (`<= 15`w) + 1 visual structure** with micro-phrases (`<= 10–15`w/card, `1–3`w/cell; `~40–90`w live / `~60–110`w async, up to `~170`w only on `1–3`w/cell verdict matrices or a closing `Annex · Sources` slide). Put pricing tiers, caveats, and full rationale in **Speaker Notes**:

1. **Cover**: clear title, subject kicker, audience/date metadata.
1. **Situation / Mental model**: 1 core shift, progression strip, or familiar contrast (for example, 3 single-word anchor cards).
1. **Recommendation / Verdict**: decision needed, expected gain, owner, and date (or verdict-grouped comparison matrix with `1–3`w cells).
1. **Proof / Architecture (2–4 slides)**: one bar panel, clean flow diagram, 2x2 matrix, or 2-column Forces vs Prerequisites split per slide.
1. **Next Steps / Debate**: 3 short action cards + 1–2 clear decision/discussion questions.
1. **Annex · Sources (optional closing slide)**: 2 balanced thematic cards (`Entity · short clickable domain` / 1-line scope tags) + 1 global verification-date disclaimer line at the bottom.

## Reader Lenses

Match the opening frame to who decides (default **Colleague / Busy leader** unless writing a peer PR/RFC):

| Reader                     | First question            | Highlight first                                         |
| -------------------------- | ------------------------- | ------------------------------------------------------- |
| Colleague / PM / Ops       | What changes & why?       | Plain mental model, practical impact, 2–3 steps or ask  |
| Busy leader / VP (default) | Take-home, impact, ask?   | Recommendation, 1–3 figures vs baseline, risk, deadline |
| Security lead              | Data movement & controls? | Data boundary, access model, failure/audit controls     |
| Finance / Buyer            | Total cost & lock-in?     | Monthly/annual range, break-even, commitments           |
| Tech lead (opt-in)         | Scale & Day-2 ops?        | Architecture visual, latency/reliability, ops load      |
