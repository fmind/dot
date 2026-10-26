---
name: stakeholder-writing
description: "Write reports, proposals, status updates, and executive summaries for busy readers, in HTML or Markdown."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-10-26"
---

# Stakeholder Writing

Write documents that busy professionals with no context on our work can understand, trust, and act on, and that the user can share without rewriting: reports, proposals, decision memos, cost estimates, status updates, emails, and PR or issue text. This skill owns the reader, the content, the structure, and the final check. Delivery stays with its owners: [draft-mail](../draft-mail/SKILL.md) for Gmail drafts, [github-pull-request](../github-pull-request/SKILL.md) and [github-issues](../github-issues/SKILL.md) for GitHub text, [fmind-visuals](../fmind-visuals/SKILL.md) for slide decks, [diagrams-as-code](../diagrams-as-code/SKILL.md) for diagrams, and [repository-docs](../repository-docs/SKILL.md) for README and AGENTS.md files.

## Workflow

1. **Frame the reader and the ask**: write down who reads, what they already know, the questions they ask first ([reader lenses](references/outlines.md#reader-lenses)), and the one decision or action you want from them, by when. Choose the document type, the destination format, and the reader's language. The [outlines](references/outlines.md) and the [report template](templates/report.html) are a baseline: adapt their sections, order, and layout to the request, and add what the situation needs, such as a sensitivity table, a timeline, or a FAQ. When an unknown reader or goal would change the content, ask the user before drafting; otherwise state your assumptions to the user.
1. **Gather verified facts**: use primary sources and current data, and record each figure's source, date, and scope. Link each claim inline to its source, both the internal documents, tickets, and dashboards the user provides and the external primary documentation, so the reader can check it and follow up; write a missing internal link as a visible placeholder. Never invent facts about the client, its systems, its volumes, or its people. Turn each unknown into a labeled assumption with a plausible range, and show how the conclusion changes across that range.
1. **Write the take-home message first**: one sentence the reader should remember and repeat. Then write the executive summary in about 120 words: the conclusion, why it matters to this reader, the decision or action with its deadline, and the one or two figures that support it. A reader who stops there must have what they need. Right after it, add a short **Key terms** block that explains, in one line each, the terms, units, and metrics this reader may not know, such as "$ per million tokens"; skip it when there are none.
1. **Structure by importance**: give the document a title that names its subject, such as "Comparing the cost of A and B", and give sections short names, such as Context, Options, or Recommendation. Open each section with a bold sentence that states its conclusion, answer the reader's questions in order of importance, and keep one idea per paragraph. End a long section, one that runs past a few paragraphs or mixes several findings, with a short "Take-home messages" box of one to three sentences; short sections need none. Keep the main body as short as the decision allows: about one page for a simple decision, longer only when the task's complexity requires it. Move technical details, methods, calculations, evidence, and raw data to annexes, and point to each annex from the sentence it supports.
1. **Make it easy to read**: follow the [style rules](references/style.md): plain words, short sentences, and active voice; every term, acronym, and metric this reader may not know explained in the Key terms block, while terms they use daily stay unexplained; a concrete example for each abstract point; and the key phrase of each paragraph in bold, so a reader who skims only the bold text gets the argument.
1. **Show it, not only tell it**: add a figure wherever it explains faster than text: a chart for numbers and trends (inline SVG or matplotlib, following the host's data-visualization skill when it has one), and a diagram for a flow, an architecture, or a timeline ([diagrams-as-code](../diagrams-as-code/SKILL.md) for Mermaid, D2, and SVG). Give each figure a caption that states its conclusion and a table or text alternative. When citing third-party data such as a benchmark, show it as a figure rather than a paragraph of numbers: in a private document, read by a customer's internal team or a small circle, embed a cropped capture of the source's chart with a source line and link, as a person quoting it would; in a public document, redraw it from the published figures or get permission.
1. **Make the decision easy and honest**: number the options (Option 1, Option 2) and refer to them by number, compare them on the same criteria (benefit, cost, risk, effort, time to value), include doing nothing, recommend one, and say why. Compare under equal conditions, and say when the evidence does not, such as benchmarks run at different settings. State the assumptions, limits, residual risks, and what would change the recommendation. End with next steps that each have an owner and a date.
1. **Format for the destination**: start standalone HTML reports from the [report template](templates/report.html); use Markdown for documents, PRs, and issues, and plain text for email and chat. Make the document look designed, not black text on white: style it with `~/.agents/DESIGN.md` by default, as the template does, or with the customer's or employer's brand when the work is theirs, and ask for their brand guide when you do not have it. Use the design's colors for headings, summary card, key-figure tiles, status badges, and framed figures, and embed its fonts so the file renders the same everywhere.
1. **Run the reader check**: apply every item of the [checklist](references/checklist.md) and fix each failure. For HTML, render it at desktop and phone widths with the [playwright](../playwright/SKILL.md) skill and look at the screenshots. Tell the user what you could not verify.

## Gotchas

- **Dense prose and jargon cost the reader**: arrows, slash chains, stacked parentheses, coined labels, and metaphors save the writer words and cost the reader minutes; write complete sentences instead.
- **Estimates look like facts**: a cost, effort, or risk figure is a model; show its formula, inputs, price date, and region in an annex, give a range, and round to the precision the inputs support.
- **Numbers need a baseline**: "30% cheaper" means nothing until it says than what, for which volume, and over which period.
- **Plausible client details are still invented**: the author's title, the client's policies, baselines, or requirements, and owners and deadlines the user did not give are guesses; write them as proposals ("proposed owner", "suggested date") or placeholders for the user to fill.
- **Context is not content**: opinions, preferences, and hunches the user shares to brief you stay out of the document; state a position only when the user asks to sign it, and let the evidence carry the recommendation.
- **Session details leak**: "as discussed", agent or tool names, local paths, internal labels, and private data either mean nothing to the reader or must not leave the session.
- **One document serves one reader**: a security leader, an executive, and an engineer ask different first questions; write for the decision maker and move other audiences' details to annexes or a separate document.
- **Formatting can fragment reasoning**: use prose for arguments, bullets for parallel items, and tables for comparisons; a wall of short bullets hides how the points connect.

## Documentation

- [Plain language guidelines](https://www.plainlanguage.gov/guidelines/) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companion skills: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans before sharing).
