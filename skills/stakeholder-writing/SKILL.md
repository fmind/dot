---
name: stakeholder-writing
description: "Write concise stakeholder emails, messages, docs, slides, reports, and proposals; fact-check drafts."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-11-11"
---

# Stakeholder Writing

Write text busy people can read in seconds and send without rewriting. Delivery belongs to [draft-mail](../draft-mail/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md), [documentation-site](../documentation-site/SKILL.md), and [repository-docs](../repository-docs/SKILL.md).

**Short beats complete.** Put the message first and move depth to annexes or links. Keep only what changes what the reader understands, decides, or does; adapt any guideline that hurts this reader and tell the user why. Three rules never bend: invent no facts, disclose no secrets or private data, and never let a figure mislead.

## Default length

Count main text with `wc -w` (excluding annexes). Exceed defaults only when complexity, multiple options, or real risk requires it:

- **Chat message**: ~50 words.
- **Email**: ~150 words (~100 for a reply).
- **Status update, PR, or issue text**: ~200 words.
- **Document for teammates**: 2–3 sentence summary + ~400 words.
- **Decision memo or proposal**: ~100-word summary + ~500 words.
- **Slide deck**: 8–12 core slides (~25–40 on-slide words per slide; detail in notes/backup slides).
- **Report or analysis**: ~100-word summary + ~800 words.

## Short messages, emails, and PRs

Stay in this file for chat, email, status updates, and PR/issue text:

1. **Put the message first**: sentence 1 states the answer, change, or ask; follow with 2–3 plain sentences of context and one dated next step (PRs cover user/operator impact, verification, and rollout/rollback).
1. **Keep prose plain**: active everyday words, no headings in mail/chat, at most one short list, and backticks only for copyable commands, paths, or literal values.
1. **Ground facts and check**: link accessible primary sources inline without exposing internal URLs/slugs, turn unknowns into labeled assumptions or placeholders, run `wc -w` and `betterleaks` before sharing, and strip session habits ("as discussed", agent/tool names, local paths, verification/Decisions/Suggestions).

## Formal documents, slides, and fact-checks

Load deeper guides only when drafting formal deliverables or fact-checking:

1. **Frame reader and outline**: pick the decider's lens and structure from [outlines](references/outlines.md) (or [slides](references/slides.md) for decks). Ask when an unknown reader or goal changes content.
1. **Style and visuals**: apply [style](references/style.md) (numbers, section-opening bold conclusions, accessible links, conclusion-captioned SVG/Mermaid/matplotlib figures) and render with [HTML](templates/report.html) or [Markdown](templates/report.md) templates plus `~/.agents/DESIGN.md` or customer branding.
1. **Cut and verify**: run the [checklist](references/checklist.md) and check rendered output ([playwright](../playwright/SKILL.md)). For fact-checks, run the checklist's Trust section and report dated findings without rewriting unless asked.

## Gotchas

- **Completeness is not quality**: a teammate email with an executive summary, Key terms, and risk matrix is a report nobody asked for.
- **Shorthand taxes the reader**: replace arrows, slash chains, stacked parentheses, coined labels, and metaphors with plain sentences.
- **Figures need a model**: give conservative rounded ranges against a named baseline ("30% cheaper" than what, at what volume), with formulas, inputs, and price dates in an annex.
- **Plausible details are still invented**: unstated titles, policies, baselines, owners, deadlines, or ungrounded risk/confidence ratings become labeled proposals, placeholders, or questions; state a position only when the user asks to sign it.

## Documentation

- [Plain language guidelines](https://digital.gov/guides/plain-language) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companions: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans).
