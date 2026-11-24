---
name: humanize
description: "Write/edit short, clear prose and visuals for leaders, email, chat, memos, PRs, docs, slides."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-08-20"
  updated: "2026-11-24"
  kind: task
---

# Humanize

Central guide for human-facing writing. **Default reader:** a busy executive or cross-functional leader scanning between meetings who wants the **take-home, business impact, risk, and decision** (_so what_)—not the engineering _how_. **Short, clear, and insightful is default; depth is opt-in** (use peer-engineer depth only on developer PRs/RFCs).

## Core Rules

1. **Read the room & avoid bad surprises**: check prior threads, comments, or notes for priorities, vocabulary, and sensitivities. Surface bad news, delays, cost shifts, or risks early with a mitigation or option—never blindside owners in a broad forum.
1. **Take-home & "so what" first**: open in 1–2 plain sentences with the decision, headline insight, or ask and why it matters (time, cost, risk, customer impact). Drop investigation logs and engineering-trench detail unless asked.
1. **Curated figures, never data dumps**: pick **1–3 decision-bearing numbers** paired with a baseline/delta (`+18% throughput vs Q3`, `~€120k/year`), rounded to decision precision. Move secondary stats, exclusions, methodology, or raw queries to a link, thread reply, or optional `Annex`.
1. **Plain translation & visual calm**: translate acronyms, ticket IDs, repo/table names, and technical mechanisms into reader impact; use monospace only for literal commands/paths. Keep paragraphs `<= 3`–`4` lines, sentences `<= 25`–`30`w, lists `<= 4`–`5` single-line bullets, tables `<= 4` cols / `<= 5` rows, and bold sparse; see [outlines](references/outlines.md) and [primitives](references/primitives.md) for callouts, KPI strips, and brand/type rules.
1. **Balanced clickable sources**: link verified docs, dashboards, tickets, and primary sources inline (never invent URLs or dump link walls). Fit attribution to the medium: inline links (+ compact `Sources:` line on email/Chat), subtle footnote + speaker notes on decks, or a closing `Sources` section on memos/reports.
1. **Authentic voice, zero slop**: drop em dashes (`—`), EN/FR AI clichés, `"not only X, but also Y"` cadences, and assistant framing (`Done`, `Confidence`, `Verification`). Match audience language (`tu`/`vous`) and close with **one** dated next step when action is needed.

## Length Budgets & Channel Guides

- **Budgets**: Chat `<= 60–80`w (`3–5` lines) · Email `<= 120–150`w (`~100`w replies) · Brief/memo `~250–400`w (`<= 1` screen) · PRs/issues `~150–250`w · Slides `~30`w + one focal visual.
- **Tight rewrites**: when shortening a draft, add a 1-line note outside the copy stating what was cut vs kept (for example, `Cut background (~40% shorter); kept trade-offs and numbers`) so over-cuts surface immediately.
- **Guides**: [outlines](references/outlines.md), [primitives](references/primitives.md), [report.html](templates/report.html), [report.md](templates/report.md) · Channels: [draft](../draft/SKILL.md), [docs](../docs/SKILL.md), [github](../github/SKILL.md), [acli](../cloud-ops/references/acli.md), [gws/chat](../gws/references/chat.md), [diagrams-as-code](../diagrams-as-code/SKILL.md), [playwright](../web-frontend/references/playwright.md).

## Pre-Send Gate

Apply these checks to **long-form, public, or high-stakes drafts** (memos, briefs, proposals, decks, public docs, sensitive leadership emails); skip Vale and subagent spawns on short 1:1 replies or quick Chat posts unless requested.

1. **Lint**: `vale --no-global --config ~/.config/vale/.vale.ini --output=JSON <draft.md>` (omit `--config` if repo `.vale.ini` exists; for domain vocabulary, add a repo-local `Terminology.yml` `extends: substitution` rule in your project's Vale styles).
1. **Review & inspect**: freeze and run `fmind-review-human` (plus `fmind-review-completeness` and matching `factcheck`/`docs`/`proposal`/`visuals`/`frontend` roles on substantive deliverables; [subagent](../subagent/SKILL.md)), and inspect `1440x900` & `390x844` or PDF/PNG renders for zero clipping.

## Documentation

- [Vale](https://docs.vale.sh/) · [DESIGN.md](https://github.com/fmind/theme/blob/main/DESIGN.md) · [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) · Companions: [trim](../skillify/references/trim.md), [draft](../draft/SKILL.md), [subagent](../subagent/SKILL.md).
