---
name: humanize
description: "Turn dense AI drafts into clear, scannable, visually structured human communication for emails, chat, PRs, docs, reports, and slides."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-08-20"
  updated: "2026-11-17"
  kind: task
---

# Humanize

Respect human reading time without sacrificing substance: deliver clear, complete, visually structured communication instead of AI text walls or shallow summaries.

## Structure before drafting

1. **Name the core takeaway**: finish *"After reading this, the reader should know or do ___."* State that outcome or decision in line one and organize supporting points underneath.
1. **Calibrate depth to the reader**: keep routine chat and mail crisp and outcome-led; give engineering PRs, docs, RFCs, and reports complete analytical depth, baselines, trade-offs, and edge cases. Never drop load-bearing facts to hit a fixed signal count.
1. **Match visual weight to the medium**: use bold lead-ins and short bullets on chat and 1-to-1 mail; use intentional hierarchy (callouts, tables, KPI strips, figures, collapsible log annexes) on multi-stakeholder briefs, PRs, docs, reports, and slides.

Before: _"Checked `loader.py`; bumped `chunk_size=100_000` and `memory=8Gi` in `infra/main.tf`; all `14` `pytest` cases pass; please review PR `#418`."_

After: **Batch imports are healthy again: [approve PR 418](https://example.com/org/repo/pull/418) before 17:00 UTC.** Peak memory stays below 5.4 GB against our 8 GB limit after tuning batch sizing.

## Hard rules

- **Zero em dashes; reader-calibrated monospace**: drop em dashes (`—`) in external copy (use colons, commas, parentheses, or periods). Reserve monospace for literal commands/paths to copy in executive, client, and mail prose; allow clean inline code (`< 3` spans per sentence) in developer docs, READMEs, and technical PRs.
- **Reader-calibrated precision**: frame executive/customer copy around user, cost, risk, and reliability outcomes; keep exact root causes and error codes (`OOMKilled` exit `137` at 8 GiB -> 12 GiB) in engineering PRs, postmortems, and technical docs.
- **Signal first, complete depth underneath**: pair headline outcomes with exact baselines (`+18% throughput, 1,420 vs 1,200 req/s`). Keep methodology, caveats, and a visible closing `Sources` section (`source`, what it grounds, `date/version`) on substantive deliverables; place raw logs in collapsible annexes.
- **Proportional visual hierarchy**: apply `~/.agents/DESIGN.md` structure (lists, tables, callouts, figures) where warranted—never force highlight boxes onto short 1-to-1 mail.
- **Clean external voice**: match the user's or audience's language and tone; never leak assistant framing (`Done`, `Confidence`, `Verification`, `Decisions`) into external deliverables.

## Default length budgets

Treat as flexible targets—expand whenever analytical nuance, edge cases, or technical completeness serve the reader:

- **Chat & Slack**: ~80 words; headline line, short bold-lead bullets, explicit ask.
- **Email**: ~150 words (~100 for replies); bold takeaway/ask, short paragraphs, optional ≤4-item list, owner/date; skip callout boxes and `<mark>` highlights on routine mail.
- **PRs & issues**: ~150–300 words scaled to complexity; bold impact summary, root cause and trade-offs, compact proof, rollout notes.
- **Docs, RFCs, & reports**: one-screen executive summary plus complete sections, figures/tables, visible closing `Sources`, and collapsible raw annexes.
- **Slides**: ~30 visible words target per slide (up to ~45 on label-rich comparative charts with units and `N`) and one focal visual; details in speaker notes.

## Choose format by medium

- **HTML reports, newsletters, & email**: use [primitives](references/primitives.md) and [report.html](templates/report.html); deliver mail via [draft-mail](../draft-mail/SKILL.md).
- **Docs, memos, PRs, & tickets**: pick structures from [outlines](references/outlines.md) ([report.md](templates/report.md)) and visuals from [primitives](references/primitives.md); inspect rendered pages via [playwright](../playwright/SKILL.md). Owners: [draft-doc](../draft-doc/SKILL.md), [acli](../acli/SKILL.md), [gh](../gh/SKILL.md), [documentation-site](../documentation-site/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [repository-docs](../repository-docs/SKILL.md).
- **Decks & branded graphics**: structure arcs in [outlines](references/outlines.md) and render via [draft-typst-deck](../draft-typst-deck/SKILL.md) or [diagrams-as-code](../diagrams-as-code/SKILL.md).

## Pre-send gate

1. **Lint deterministically**: run `vale --no-global --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` (omit `--config` when repo `.vale.ini` exists) to block AI clichés and em dashes (`—` / `&mdash;`) as errors and flag style, wordiness, prose backticks, `> 40`-word sentences, and `> 65`-word paragraphs (`draft-mail`, `draft-doc`'s `compile_markdown_doc.py`, and `draft-typst-deck` run this automatically).
1. **Verify completeness & rendered visuals**: confirm every question is answered, baselines/owners stand out, substantive docs close with visible primary `Sources`, and rendered HTML/PDF/Markdown previews cleanly across desktop (`1440x900`) and mobile (`390x844`) viewports without clipping.
1. **Audit high-stakes copy adversarially**: freeze external briefs, decks, docs, and announcements and run `fmind-review-human` plus `fmind-review-completeness` and matching specialists (`fmind-review-factcheck`, `fmind-review-docs`, `fmind-review-pitch`, `fmind-review-figures`, `fmind-review-design`; [subagent](../subagent/SKILL.md)).
