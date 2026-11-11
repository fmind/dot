---
name: stakeholder-writing
description: "Write concise stakeholder emails, messages, docs, reports, and proposals; fact-check drafts."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-11-11"
---

# Stakeholder Writing

Write text busy people can read in seconds and send without rewriting, from a chat message to a decision memo. This skill owns content, length, and reader checks; delivery belongs to [draft-mail](../draft-mail/SKILL.md), [draft-doc](../draft-doc/SKILL.md), [pull-request](../gh/references/pull-request.md), [issues](../gh/references/issues/GUIDE.md), [documentation-site](../documentation-site/SKILL.md), and [repository-docs](../repository-docs/SKILL.md).

**Short beats complete.** Put the message first and move depth to annexes or links. Keep only what changes what the reader understands, decides, or does; adapt any guideline that hurts this reader and tell the user why. Three rules never bend: invent no facts, disclose no secrets or private data, and never let a figure mislead.

## Default length

Count main text with `wc -w` (excluding annexes). Exceed these defaults only when task complexity, multiple options, or real risk requires it:

- **Chat message**: ~50 words.
- **Email**: ~150 words (~100 for a reply).
- **Status update, PR, or issue text**: ~200 words.
- **Document for teammates**: 2–3 sentence summary + ~400 words.
- **Decision memo or proposal**: ~100-word summary + ~500 words.
- **Report or analysis**: ~100-word summary + ~800 words.

## Workflow

1. **Frame the reader and the ask**: identify who reads, what they know, their first questions ([reader lenses](references/outlines.md#reader-lenses)), and the action needed by when. Choose the type, destination, and reader's language, then start from the matching [outline](references/outlines.md). Ask when an unknown reader or goal changes the content.
1. **Put the message first**: open with the one sentence the reader must remember—the answer or ask in mail and chat.
1. **Ground every fact**: use only facts from the user and primary sources, recording each figure's source, date, and scope. Link claims inline where this reader can open them ([links](references/style.md#links-and-sensitivity)); turn unknowns into labeled assumptions or placeholders.
1. **Write plainly and show visually**: apply the [style guide](references/style.md) (plain words, active sentences, concrete examples, minimal code formatting) and add conclusion-captioned SVG, Mermaid, or matplotlib visuals when faster than prose ([visuals](references/style.md#examples-tables-and-visuals)).
1. **Match structure and design to formality**: follow [headings](references/style.md#titles-headings-and-section-summaries) and [platform features](references/style.md#destination-and-platform-features). Formal reports, proposals, and memos open with conclusion, decision, and deadline; compare options (including doing nothing) on shared criteria; state recommendation, risks, and next steps once; move methods and evidence to annexes; and style with [HTML](templates/report.html) / [Markdown](templates/report.md) templates plus `~/.agents/DESIGN.md` or customer branding. Emails and chat skip headings.
1. **Cut and verify**: delete background, non-decisive caveats, and repeats; check `wc -w`, run the [checklist](references/checklist.md), and verify rendered output ([playwright](../playwright/SKILL.md)). For fact-check requests, run the checklist's Trust section and report dated findings without rewriting unless asked.

## Gotchas

- **Completeness is not quality**: a teammate email with an executive summary, Key terms, and risk matrix is a report nobody asked for.
- **Shorthand taxes the reader**: arrows, slash chains, stacked parentheses, coined labels, and metaphors save writer effort and cost reader time.
- **Session habits leak**: strip "as discussed", agent or tool names, local paths, internal labels, session sections (verification notes, Decisions, Suggestions), and private data.
- **Figures need a model**: give estimates as conservative rounded ranges against a named baseline ("30% cheaper" than what, at what volume), with formulas, inputs, and price dates in an annex.
- **Plausible details are still invented**: unstated titles, client policies, baselines, owners, deadlines, ungrounded risk/confidence ratings, or assumed user reactions become proposals ("proposed owner"), placeholders, or questions.
- **Context is not content**: keep background opinions and hunches out; state a position only when the user asks to sign it.

## Documentation

- [Plain language guidelines](https://digital.gov/guides/plain-language) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companions: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans before sharing).
