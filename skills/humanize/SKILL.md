---
name: humanize
description: "Write/edit short, clear prose and anti-slop briefs for leaders, email, chat, memos, PRs, docs, slides (Vale)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-08-20"
  updated: "2026-11-25"
---

# Humanize

Central guide for human-facing writing. **Default reader:** a busy colleague or leader scanning between meetings who wants the **take-home, practical impact, risk, and decision** (_so what_)—not the engineering _how_. Optimize for **low cognitive load** (mental energy, not just raw word count): a calm 90-word visual diagram beats a cramped 40-word prose wall. **Short, plain, and visually structured is default; depth is opt-in.**

## Core Rules

1. **Read the room & avoid bad surprises**: check prior threads, comments, or notes for priorities, vocabulary, and sensitivities. Surface bad news, delays, cost shifts, or risks early with a mitigation or option—never blindside owners in a broad forum.
1. **Take-home & "so what" first**: open in 1–2 plain sentences with the decision, mental model, or ask and why it matters (time, cost, risk, customer impact). Drop investigation logs and engineering-trench detail unless asked.
1. **Select, don't compress (two-layer disclosure)**: pick only the **2–3 points** and **1–3 baseline-anchored numbers** (`+18% throughput vs Q3`, `~€120k/year`) that change the reader's decision. Keep **one idea per sentence**, group dates/caveats into **one bottom note**, and park nuance, pricing tiers, or raw detail in speaker notes, a link, a thread reply, or a closing `Annex · Sources`—never cram 10 details into terse shorthand.
1. **Plain mental models, low cognitive load**: open unfamiliar topics with a familiar contrast or 1-word anchors before naming tools. Drop dev jargon, architect buzzwords (*"flip conditions"*, _"bounded contexts"_, _"blast radius"_), nested parentheticals, slash-chains (`A/B/C`), unrequested report chrome (`Do nothing` tables or `Methodology` annexes on simple notes), and prose backticks (reserve monospace for literal commands/paths).
1. **Visual calm**: keep prose paragraphs `1–3` sentences (`<= 45–50`w), sentences `<= 20–25`w, lists `<= 4–5` single-line bullets (`<= 12`w each), prose tables `<= 4` cols / `<= 5` rows (scannable `1–3`w/cell verdict matrices up to `6x6` are fine when grouped by a bottom verdict), and bold sparse; see [outlines](references/outlines.md) and [primitives](references/primitives.md).
1. **Balanced clickable sources**: link verified docs, dashboards, tickets, and primary sources inline (never invent URLs or dump link walls). Fit attribution to the medium: inline links (+ compact `Sources:` line on email/Chat), one closing `Annex · Sources` slide + speaker notes on decks, or a closing `Sources` section on memos/reports.
1. **Authentic voice, zero slop**: drop em dashes (`—`), EN/FR AI clichés, `"not only X, but also Y"` cadences, and assistant framing (`Done`, `Confidence`, `Verification`). Match audience language (`tu`/`vous`) and close with **one** dated next step when action is needed.

## Length Budgets & Channel Guides

- **Chat / Slack**: `<= 60–80`w (`3–5` lines); park detail in a thread reply or linked doc.
- **Email**: `<= 120–150`w (`~100`w replies); park detail in a linked doc or attachment.
- **Colleague note / explainer**: `~150–250`w; add one closing caveat/date line or link.
- **Brief / memo / pitch / ADR / feature brief**: `~250–400`w (`<= 1` page; formal SOW/PRD/RFC opt-in only); park breakdowns in an optional `Annex`.
- **PRs / issues**: `~150–250`w; fold benchmarks or logs into `<details>`.
- **Slides**: zero prose paragraphs (`<= 15`w takeaway, `<= 10–15`w/card); `~40–90`w live / `~60–110`w async (up to `~170`w only on `1–3`w/cell verdict matrices or a closing `Annex · Sources` slide; nuance in speaker notes).
- **Tight rewrites**: when shortening a draft, add a 1-line note outside the copy stating what was cut vs kept (for example, `Cut background (~40% shorter); kept trade-offs and numbers`) so over-cuts surface immediately.
- **Guides**: [outlines](references/outlines.md), [primitives](references/primitives.md), [report.html](templates/report.html), [report.md](templates/report.md) · Channels: [draft](../draft/SKILL.md), [docs](../docs/SKILL.md), [github](../github/SKILL.md), [acli](../cloud-ops/references/acli.md), [gws/chat](../gws/references/chat.md), [diagrams-as-code](../diagrams-as-code/SKILL.md), [playwright](../web-frontend/references/playwright.md).

## Pre-Send Gate

Apply to **long-form, public, or high-stakes drafts** (memos, briefs, proposals, decks, public docs, sensitive leadership emails); skip Vale and subagents on short 1:1 replies or quick Chat posts unless requested.

1. **Lint**: `vale --no-global --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` (omit `--config` if repo `.vale.ini` exists; add repo `Terminology.yml` for domain terms). Vale checks em dashes/slop everywhere and `ProseBackticks` only on `.md`; tighter sentence/paragraph/HTML-code bounds rely on `fmind-review-human`.
1. **Review & inspect**: run `fmind-review-human` (+ matching roles per [subagent](../subagent/SKILL.md)) and inspect `1440x900`/`390x844` or PDF/PNG renders for zero clipping.

## Documentation

- [Vale](https://docs.vale.sh/) · [DESIGN.md](https://github.com/fmind/theme/blob/main/DESIGN.md) · [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) · Companions: [trim](../skillify/references/trim.md), [draft](../draft/SKILL.md), [subagent](../subagent/SKILL.md).
