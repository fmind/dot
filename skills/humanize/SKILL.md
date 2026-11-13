---
name: humanize
description: "Turn dense AI drafts into clear, visual human communication: emails, memos, docs, PRs, slides, and reports."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/humanize
  created: "2026-09-16"
  updated: "2026-11-13"
---

# Humanize

Respect human time. Turn raw technical output into scannable, visually structured communication people act on in seconds. Delivery tools: [draft-mail](../draft-mail/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [draft-typst-deck](../draft-typst-deck/SKILL.md), [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md).

## Core Rules

1. **Signal first, zero noise**: before drafting, choose the **1–3 insights or decisions** that change what this reader does. Cut implementation plumbing, intermediate reasoning, tool logs, and caveats that do not alter the decision (move deep evidence into collapsible sections or annexes).
1. **Write for humans, not terminals**:
   - **Zero backtick spam**: never wrap product names, services, cloud regions, environments, statuses, metrics, or field concepts in backticks. Reserve monospace strictly for literal commands or paths an engineer must copy-paste.
   - **Plain words, zero jargon**: translate internal architecture into cost, latency, reliability, or user effect. Ban arrow chains (`A -> B -> C`), slash-stacked nouns, coined labels, throat-clearing intros, and agent session trailers (`Verification`, `Decisions`, `Suggestions`, tool names, local paths, bare IDs).
1. **Format visually for the medium (never send a grey wall of plain text)**:
   - **Highlight** the decisive number, phrase, or ask (`<mark>` / highlight pills, colored callout banners, bold lead-ins).
   - **Separate & group** with whitespace, horizontal rules (`---`), 2–3 KPI tiles, tinted boxes with 4px left accent borders, pill status badges with words (`🟢 Ready`, `🟡 Trade-off`, `🔴 Blocker`), and compact comparison tables.
   - **Illustrate** flows and trade-offs with branded [Typst](../diagrams-as-code/references/typst.md), Mermaid, or SVG visuals instead of dense paragraphs.
1. **Fact-check & protect privacy (firm)**: invent zero facts, URLs, owners, or dates; round figures against named baselines; run [`betterleaks stdin --redact`](../code-security/references/betterleaks.md#commands) and strip internal/customer identifiers.

## Default length

Measure main text via `wc -w`; expand only when complexity or risk demands it:

- **Chat / Slack**: ≤80 words (signal, why it matters, next step).
- **Email**: ~150 words (~100 for replies; ≤3 short paragraphs + optional callout).
- **Status update or PR description**: 100–250 words (change, impact, proof, risk).
- **Decision memo / teammate doc**: ~100-word visual summary + 250–450 words.
- **Slide deck**: 4–10 slides (≤30 words and **one** focal visual per slide; detail in speaker notes).
- **Executive report**: ~100-word visual summary + 600–1,200 words + collapsible annexes.

## Workflows & Resources

- **Short messages (chat, email, PRs)**: apply [style](references/style.md) (Before/After rewrites and medium primitives) and [outlines](references/outlines.md), then pass [checklist](references/checklist.md).
- **Docs, memos, reports, & decks**: structure with [outlines](references/outlines.md) (or [slides](references/slides.md)), build with [HTML](templates/report.html) or [Markdown](templates/report.md) templates styled via `~/.agents/DESIGN.md` (or customer brand), and inspect rendered frames ([playwright](../playwright/SKILL.md)).

## Documentation

- [Plain language guidelines](https://digital.gov/guides/plain-language) · [BLUF](https://en.wikipedia.org/wiki/BLUF_(communication)) · [diagrams-as-code](../diagrams-as-code/SKILL.md)
- Companions: [draft-doc](../draft-doc/SKILL.md), [draft-mail](../draft-mail/SKILL.md), [draft-typst-deck](../draft-typst-deck/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [code-security](../code-security/SKILL.md).
