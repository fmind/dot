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

Respect human reading time without sacrificing substance: deliver clear, complete, visually structured copy instead of AI text walls or shallow summaries.

## Structure before drafting

1. **Name the core takeaway**: finish *"After reading this, the reader should know or do ___."* Lead with that outcome or decision and group supporting points below.
1. **Calibrate depth to the reader**: keep routine chat and mail crisp and outcome-led; give engineering PRs, docs, RFCs, and reports complete analytical depth, baselines, trade-offs, and edge cases. Never drop load-bearing facts to hit a fixed signal count.
1. **Match visual weight to the medium**: use bold lead-ins and short bullets on chat and 1-to-1 mail; use intentional hierarchy (callouts, tables, KPI strips, figures, collapsible log annexes) on multi-stakeholder briefs, PRs, docs, reports, and slides.

Before: _"Checked `loader.py`; bumped `chunk_size=100_000` and `memory=8Gi` in `infra/main.tf`; all `14` `pytest` cases pass; please review PR `#418`."_

After: **Batch imports are healthy again: [approve PR 418](https://example.com/org/repo/pull/418) before 17:00 UTC.** Peak memory stays below 5.4 GB against our 8 GB limit after tuning batch sizing.

## Hard rules

- **Zero em dashes; reader-calibrated monospace**: drop em dashes (`—`) in external copy (use colons, commas, parentheses, or periods). Keep monospace for literal commands/paths in executive, client, and mail prose; allow `< 3` code spans per sentence in developer docs, READMEs, and PRs.
- **Reader-calibrated precision**: frame executive/customer copy around user, cost, risk, and reliability outcomes; keep exact root causes and error codes (`OOMKilled` exit `137` at 8 GiB -> 12 GiB) in engineering PRs, postmortems, and technical docs.
- **Signal first, complete depth underneath**: pair headline outcomes with baselines (`+18% throughput, 1,420 vs 1,200 req/s`), keep methodology, caveats, and a visible closing `Sources` section (`source`, grounded claim, `date/version`) on substantive deliverables, and put raw logs in collapsible annexes.
- **Proportional visual hierarchy & clean voice**: apply project/customer brand tokens when present, else `~/.agents/DESIGN.md` structure (lists, tables, callouts, figures; skip boxes on short 1-to-1 mail); match the audience's language and never leak assistant framing (`Done`, `Confidence`, `Verification`, `Decisions`).

## Default length budgets

Flexible targets—expand whenever nuance, edge cases, or completeness serve the reader:

- **Chat & Slack**: ~80 words; headline, short bold-lead bullets, explicit ask.
- **Email**: ~150 words (~100 for replies); bold takeaway/ask, short `<p>` blocks, optional ≤4-item list, owner/date.
- **PRs & issues**: ~150–300 words scaled to complexity; impact summary, root cause/trade-offs, proof, rollout notes.
- **Docs, RFCs, & reports**: one-screen summary + complete sections, figures/tables, visible `Sources`, collapsible annexes.
- **Slides**: ~30 visible words target (up to ~45 on comparative charts with units and `N`) and one focal visual; details in speaker notes.

## Choose format by medium

- **HTML reports, newsletters, & email**: use [primitives](references/primitives.md) and [report.html](templates/report.html); deliver mail via [draft-mail](../draft-mail/SKILL.md).
- **Docs, memos, PRs, & tickets**: pick structures from [outlines](references/outlines.md) ([report.md](templates/report.md)) and visuals from [primitives](references/primitives.md); inspect rendered pages via [playwright](../playwright/SKILL.md). Owners: [draft-doc](../draft-doc/SKILL.md), [acli](../acli/SKILL.md), [gh](../gh/SKILL.md), [documentation-site](../documentation-site/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [repository-docs](../repository-docs/SKILL.md).
- **Decks & branded graphics**: structure arcs in [outlines](references/outlines.md) and render via [draft-typst-deck](../draft-typst-deck/SKILL.md) or [diagrams-as-code](../diagrams-as-code/SKILL.md).

## Pre-send gate

1. **Lint deterministically**: run `vale --no-global --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` (omit `--config` if repo `.vale.ini` exists) to block AI clichés and em dashes (`—` / `&mdash;`) as errors and flag style, wordiness, prose backticks, `> 40`-word sentences, and `> 65`-word paragraphs (`draft-mail`, `draft-doc`, and `draft-typst-deck` run this automatically).
1. **Verify completeness & visuals**: confirm every question is answered, baselines/owners stand out, substantive docs close with primary `Sources`, HTML/web/docs pages preview cleanly across `1440x900` and `390x844` viewports, and slide/PDF frames fit cleanly at native aspect ratio without clipping.
1. **Audit high-stakes copy adversarially**: freeze external briefs, decks, docs, and announcements and run `fmind-review-human` + `fmind-review-completeness` and matching specialists (`factcheck`, `docs`, `pitch`, `figures`, `design`; [subagent](../subagent/SKILL.md)).

## Documentation

- [Vale](https://docs.vale.sh/) · [fmind/theme DESIGN.md](https://github.com/fmind/theme/blob/main/DESIGN.md) · [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/) · [Vale releases](https://github.com/vale-cli/vale/releases)
- Companions: [trim](../trim/SKILL.md), [draft-mail](../draft-mail/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [draft-typst-deck](../draft-typst-deck/SKILL.md), [subagent](../subagent/SKILL.md).
