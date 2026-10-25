---
name: stakeholder-writing
description: "Write reports, proposals, status updates, and executive summaries for busy readers, in HTML or Markdown."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-10-25"
---

# Stakeholder Writing

Write documents that busy professionals with no context on our work can understand, trust, and act on within two minutes, and that the user can share without rewriting: reports, proposals, decision memos, cost estimates, status updates, emails, and PR or issue text. This skill owns the reader, the content, the structure, and the final check. Delivery stays with its owners: [draft-mail](../draft-mail/SKILL.md) for Gmail drafts, [github-pull-request](../github-pull-request/SKILL.md) and [github-issues](../github-issues/SKILL.md) for GitHub text, [fmind-visuals](../fmind-visuals/SKILL.md) for slide decks, [diagrams-as-code](../diagrams-as-code/SKILL.md) for diagrams, and [repository-docs](../repository-docs/SKILL.md) for README and AGENTS.md files.

## Workflow

1. **Frame the reader and the ask**: write down who reads, what they already know, the questions they ask first ([reader lenses](references/outlines.md#reader-lenses)), and the one decision or action you want from them, by when. Choose the document type and its outline in [outlines](references/outlines.md), the destination format, and the reader's language. When an unknown reader or goal would change the content, ask the user before drafting; otherwise state your assumptions to the user.
1. **Gather verified facts**: use primary sources and current data, and record each figure's source, date, and scope. Never invent facts about the client, its systems, its volumes, or its people. Turn each unknown into a labeled assumption with a plausible range, and show how the conclusion changes across that range.
1. **Write the take-home message first**: one sentence the reader should remember and repeat. Then write the executive summary in about 120 words: the conclusion, why it matters to this reader, the decision or action with its deadline, and the one or two figures that support it. A reader who stops there must have what they need.
1. **Structure by importance**: headings state conclusions, sections answer the reader's questions in order of importance, and each paragraph carries one idea. Keep the main body to about one page, roughly 500 words of prose plus its tables, and move methods, calculations, evidence, and raw data to annexes. Measure it before delivering and cut until it fits.
1. **Make it easy to read**: follow the [style rules](references/style.md): plain words, short sentences, and active voice; every term, acronym, and metric this reader may not know defined at first use, while terms they use daily stay undefined; a concrete example for each abstract point; a table for each comparison, a chart for a trend, a diagram for a flow; and bold only for the key messages.
1. **Make the decision easy and honest**: compare options on the same criteria (benefit, cost, risk, effort, time to value), include doing nothing, recommend one, and say why. State the assumptions, limits, residual risks, and what would change the recommendation. End with next steps that each have an owner and a date.
1. **Format for the destination**: start standalone HTML reports from the [report template](templates/report.html); use Markdown for documents, PRs, and issues, and plain text for email and chat. Client or employer work uses their design system when the user provides it, and Fmind work follows `~/.agents/DESIGN.md`; otherwise keep the template's neutral style.
1. **Run the reader check**: apply every item of the [checklist](references/checklist.md) and fix each failure. For HTML, render it at desktop and phone widths with the [playwright](../playwright/SKILL.md) skill and look at the screenshots. Tell the user what you could not verify.

## Gotchas

- **Dense prose costs the reader**: arrows, slash chains, stacked parentheses, coined labels, and metaphors save the writer words and cost the reader minutes; write complete sentences instead.
- **Estimates look like facts**: a cost, effort, or risk figure is a model; show its formula, inputs, price date, and region in an annex, give a range, and round to the precision the inputs support.
- **Numbers need a baseline**: "30% cheaper" means nothing until it says than what, for which volume, and over which period.
- **Plausible client details are still invented**: the author's title, the client's policies, baselines, or requirements, and owners and deadlines the user did not give are guesses; write them as proposals ("proposed owner", "suggested date") or placeholders for the user to fill.
- **Session details leak**: "as discussed", agent or tool names, local paths, internal labels, and private data either mean nothing to the reader or must not leave the session.
- **One document serves one reader**: a security leader, an executive, and an engineer ask different first questions; write for the decision maker and move other audiences' details to annexes or a separate document.
- **Formatting can fragment reasoning**: use prose for arguments, bullets for parallel items, and tables for comparisons; a wall of short bullets hides how the points connect.

## Documentation

- [Plain language guidelines](https://www.plainlanguage.gov/guidelines/) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companion skills: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans before sharing).
