---
name: humanize
description: "Turn dense AI drafts into clear, scannable, visually structured human communication for emails, chat, PRs, docs, reports, and slides."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-08-20"
  updated: "2026-11-18"
  kind: task
---

# Humanize

Respect reading time without losing substance: deliver clear, complete, visually structured copy instead of AI text walls, telegraphic caveat soup, or shallow summaries.

## Structure before drafting

1. **Open in plain English**: finish *"After reading this, the reader should know or do ___."* State what the subject is and the core outcome or decision in 1–2 plain, conversational sentences (never a noun-stacked feature list or filter dump).
1. **Separate overview clarity from annex proof (progressive disclosure)**: keep the opening, main chat/mail message, or `Overview` focused on the primary signal and baseline (`+18% throughput, 1,420 vs 1,200 req/s`). Put filter exclusions, SKU breakdowns, formulas, and raw queries in `Sources`, `Annexes`, or a thread reply so nothing is lost and the main flow reads fast.
1. **Match visual weight to the medium (zero box fatigue)**: use bold lead-ins and short bullets on chat and mail; on reports and docs, pick **either** a summary callout **or** a 3-tile KPI strip (never stack summary + KPI tiles + take-home + key-terms boxes on one page), and keep body text at `>= 10.5pt` (`>= 10pt` in tables).

Before: _"Checked `loader.py`; bumped `chunk_size=100_000` and `memory=8Gi` in `infra/main.tf`; all `14` `pytest` cases pass; please review PR `#418`."_

After: **Batch imports are healthy again: [approve PR 418](https://example.com/org/repo/pull/418) before 17:00 UTC.** Peak memory stays below 5.4 GB against our 8 GB limit after tuning batch sizing.

## Hard rules

- **Zero em dashes & telegraphic fact-stuffing**: drop em dashes (`—`) in external copy and write natural sentences with one main idea (`<= 25–30` words); never pack 4+ colons, semicolons, timestamps, SKU exclusions, and sub-tier breakdowns into one sentence or cell.
- **Reader-calibrated monospace & precision**: keep monospace for literal commands/paths in executive, client, and mail prose (`< 3` code spans per sentence in developer docs/PRs); frame executive copy around user, cost, risk, and reliability outcomes while keeping exact root causes (`OOMKilled` exit `137` at 8 GiB -> 12 GiB) in technical docs.
- **Signal first, depth underneath**: pair headline outcomes with baselines, close substantive deliverables with a `Sources` section (`source`, claim, `date/version`), and put raw logs, filter exclusions, and derivations in annexes or thread replies.
- **Proportional hierarchy & clean voice**: apply project/customer brand tokens when present, else `~/.agents/DESIGN.md` (skip boxes on short 1-to-1 mail); match the audience's language and never leak assistant framing (`Done`, `Confidence`, `Verification`, `Decisions`).

## Default length budgets

Flexible targets—keep main copy scannable and move derivations or filters to annexes or thread replies:

- **Chat & Slack**: `<= 60–80` words (`3–5` lines: bold headline, 2–3 plain bullets, ask); sources, caveats, and query links go in a thread reply.
- **Email**: ~150 words (~100 for replies); bold takeaway/ask, short `<p>` blocks, optional ≤4-item list, owner/date.
- **PRs & issues**: ~150–300 words scaled to complexity; impact summary, root cause/trade-offs, proof, rollout notes.
- **Docs, RFCs, & reports**: plain one-screen `Overview` + focused sections, figures/tables, `Sources`, and `Annexes` (`<details>` or tab).
- **Slides**: ~30 visible words target (~45 on charts with units and `N`) and one focal visual; details in speaker notes.

## Choose format by medium

- **HTML reports, newsletters, & email**: use [primitives](references/primitives.md) and [report.html](templates/report.html); deliver mail via [draft-mail](../draft-mail/SKILL.md).
- **Docs, memos, PRs, & tickets**: pick structures from [outlines](references/outlines.md) ([report.md](templates/report.md)) and visuals from [primitives](references/primitives.md); inspect pages via [playwright](../playwright/SKILL.md). Owners: [draft-doc](../draft-doc/SKILL.md), [acli](../acli/SKILL.md), [gh](../gh/SKILL.md), [documentation-site](../documentation-site/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [repository-docs](../repository-docs/SKILL.md).
- **Decks & graphics**: structure arcs in [outlines](references/outlines.md) and render via [draft-typst-deck](../draft-typst-deck/SKILL.md) or [diagrams-as-code](../diagrams-as-code/SKILL.md).

## Pre-send gate

1. **Lint deterministically**: run `vale --no-global --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` (omit `--config` if repo `.vale.ini` exists) to block AI clichés and em dashes (`—` / `&mdash;`) and flag style, wordiness, prose backticks, `> 40`-word sentences, and `> 65`-word paragraphs.
1. **Verify completeness & visuals**: confirm every question is answered, baselines/owners stand out, substantive docs close with `Sources`, HTML/web/docs preview cleanly across `1440x900` and `390x844`, and slide/PDF frames fit without clipping.
1. **Audit high-stakes copy**: freeze external briefs, decks, docs, and announcements and run `fmind-review-human` + `fmind-review-completeness` and matching specialists (`factcheck`, `docs`, `pitch`, `figures`, `design`; [subagent](../subagent/SKILL.md)).

## Documentation

- [Vale](https://docs.vale.sh/) · [fmind/theme DESIGN.md](https://github.com/fmind/theme/blob/main/DESIGN.md) · [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/) · [Vale releases](https://github.com/vale-cli/vale/releases)
- Companions: [trim](../trim/SKILL.md), [draft-mail](../draft-mail/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [draft-typst-deck](../draft-typst-deck/SKILL.md), [subagent](../subagent/SKILL.md).
