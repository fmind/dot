---
name: humanize
description: "Turn dense AI drafts into clear, scannable, visually structured human communication for emails, chat, PRs, docs, reports, and slides."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-08-20"
  updated: "2026-11-14"
  kind: task
---

# Humanize

Respect human reading time. Deliver high-signal, scannable, visually structured messages instead of dense unformatted AI text dumps.

## Mandatory 3-step cut before drafting

Apply these three filters before writing a word:

1. **Name the one point**: finish *"After reading this, the reader should know or do ___."* If there are two goals, split or demote the secondary one.
2. **Keep 1 to 3 signals**: drop setup narration, internal tool mechanics, redundant caveats, and low-value details; every kept fact must change a decision or confirm impact.
3. **Choose one visual structure**: pair text with the strongest native visual the medium supports (summary banner, colored highlight, horizontal separator, comparison table, KPI row, diagram, or collapsible drawer).

Before: _"Checked `loader.py`; bumped `chunk_size=100_000` and `memory=8Gi` in `infra/main.tf`; all `14` `pytest` cases pass; please review PR `#418`."_

After: **Batch imports are healthy again — [approve PR 418](https://example.com/org/repo/pull/418) before 17:00 UTC.** Peak memory now stays well below our 8 GB limit.

## Hard rules

- **Zero prose backticks**: never put backticks around products, formats, acronyms, metrics, files, branches, or status labels in human copy. Write Python 3.14, JSON, BigQuery, Cloud Run, 42 ms, or the config file — never wrap everyday prose words in code spans. Reserve monospace strictly for literal commands, code snippets, or paths a reader must copy verbatim to run.
- **Zero jargon**: translate stack traces, internal flag names, exit codes, and plumbing into business or user outcomes (`service restarted cleanly` beats `OOMKilled exit 137 in ingest-worker`).
- **Signal over completeness**: state the headline outcome first, round numbers cleanly with a baseline (`+18% throughput vs last quarter`), and push logs or raw tables into a collapsible drawer, appendix, or speaker note.
- **Visual hierarchy everywhere**: break up any block taller than three lines with a bold lead-in, color badge, tinted callout banner, separator line, comparison table, or chart following `~/.agents/DESIGN.md`.
- **Keep external voice clean**: adopt the user's or audience's language and tone; never expose internal assistant framing (`Done`, `Confidence`, `Verification`, `Decisions`) in external emails, docs, tickets, PRs, or slides.

## Default length budgets

- **Chat & Slack**: 80 words or fewer; one headline line, up to three bold-lead bullets, explicit ask.
- **Email, PRs, & issues**: 150 words or fewer; bold takeaway, one visual highlight or compact table, collapsible detail if needed, clear decision/date.
- **Docs & reports**: one-screen executive banner plus visual sections; secondary mechanics in appendices.
- **Slides**: max 30 visible words and one focal visual per slide; context lives in speaker notes.

## Choose format by medium

- **HTML reports, newsletters, & email**: follow native visual patterns in [primitives](references/primitives.md) and start standalone HTML briefs from [report.html](templates/report.html). Downstream delivery: [draft-mail](../draft-mail/SKILL.md).
- **Docs, memos, PRs, & tickets**: select a template structure from [outlines](references/outlines.md) (including [report.md](templates/report.md)), pick native Markdown/HTML/ADF visuals from [primitives](references/primitives.md), and inspect rendered pages visually via [playwright](../playwright/SKILL.md). Downstream owners: [draft-doc](../draft-doc/SKILL.md), [acli](../acli/SKILL.md), [gh](../gh/SKILL.md), [documentation-site](../documentation-site/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [repository-docs](../repository-docs/SKILL.md).
- **Decks & branded graphics**: structure 6–10 slide decision arcs in [outlines](references/outlines.md) and render slides or standalone cards via [draft-typst-deck](../draft-typst-deck/SKILL.md) (or [diagrams-as-code](../diagrams-as-code/SKILL.md)).

## Pre-send gate

Read the draft like a busy stakeholder scrolling on a phone: cut any paragraph over three lines, remove every prose backtick and internal jargon word, confirm the key number and next step stand out visually at a glance, and move secondary proof behind a collapse or speaker note.
