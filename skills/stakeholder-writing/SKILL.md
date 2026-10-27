---
name: stakeholder-writing
description: "Write reports, proposals, status updates, and executive summaries for busy readers, in HTML or Markdown."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-10-27"
---

# Stakeholder Writing

Write documents that busy professionals with no context on our work can understand, trust, and act on, and that the user can share without rewriting: reports, proposals, decision memos, cost estimates, status updates, emails, and PR or issue text. This skill owns the reader, the content, the structure, the look, and the final check. Delivery stays with its owners: [draft-doc](../draft-doc/SKILL.md) for Google Docs (native Drive `.md` by default), [draft-mail](../draft-mail/SKILL.md) for Gmail, [github-pull-request](../github-pull-request/SKILL.md) and [github-issues](../github-issues/SKILL.md) for GitHub, [documentation-site](../documentation-site/SKILL.md) for Zensical sites, [gws](../gws/SKILL.md) for Workspace APIs, [fmind-visuals](../fmind-visuals/SKILL.md) for decks, [diagrams-as-code](../diagrams-as-code/SKILL.md) for diagrams, and [repository-docs](../repository-docs/SKILL.md) for README and AGENTS.md files.

**These are guidelines, not a form.** Each one exists to help a busy reader; when one does not help this reader or this document, adapt or drop it, and tell the user what you changed and why. Three never bend: invent no facts, disclose no secrets or private data, and never let a figure mislead.

## Workflow

1. **Frame the reader and the ask**: note who reads, what they already know, the questions they ask first ([reader lenses](references/outlines.md#reader-lenses)), and the one decision or action you want from them, by when. Choose the document type, the destination, and the reader's language, then start from the matching [outline](references/outlines.md) and reshape it to the request. Ask the user when an unknown reader or goal would change the content; otherwise state your assumptions.
1. **Gather verified facts and their links**: use primary sources and current data, and record each figure's source, date, and scope. Link claims inline to the pages that support them, internal or external, and choose each link for this reader's access and need to know ([links](references/style.md#links-and-sensitivity)). Turn each unknown into a labeled assumption with a plausible range, and show how the conclusion moves across it.
1. **Lead with the message**: write the one sentence the reader should remember, then an executive summary of about 120 words with the conclusion, why it matters to them, the decision and its deadline, and one or two supporting figures. Follow it with a short Key terms block when the reader meets unfamiliar terms, units, or metrics.
1. **Structure by importance**: name the subject in the title and give sections short names; open each section with a bold sentence that states its conclusion and close a long one with a short take-home box ([headings](references/style.md#titles-headings-and-section-summaries)). Keep the body as short as the decision allows, about one page for a simple one, and move methods, calculations, evidence, and raw data to annexes that the text points to.
1. **Write plainly and show it**: follow the [style guide](references/style.md): plain words, short active sentences, a concrete example per abstract point, and bold that tells the argument to a skimmer. Use a chart or diagram wherever it explains faster than text, with a caption that states its conclusion ([visuals](references/style.md#examples-tables-and-visuals)).
1. **Make the decision easy and honest**: number the options and compare them on the same criteria and conditions (benefit, cost, risk, effort, time to value), include doing nothing, recommend one, and say why. State assumptions, limits, residual risks, and what would change the recommendation, and end with next steps that each have an owner and a date.
1. **Make it beautiful, natively**: a document that looks designed earns attention and trust, so give the look as much care as the words. Use the destination's own features rather than imitating them ([platform features](references/style.md#destination-and-platform-features)), start from the [HTML](templates/report.html) or [Markdown](templates/report.md) report template, and style with `~/.agents/DESIGN.md` (Fmind Theme) or customer branding if available, asking for its guide when you lack it.
1. **Run the reader check**: review the draft against the [checklist](references/checklist.md), fix what fails, and render it where it will be read, such as HTML at desktop and phone widths with [playwright](../playwright/SKILL.md). Tell the user what you could not verify and which guidelines you set aside.

## Gotchas

- **Dense prose costs the reader**: arrows, slash chains, stacked parentheses, coined labels, and metaphors save the writer words and cost the reader minutes.
- **Estimates look like facts**: a cost, effort, or risk figure is a model; give a range, round to what the inputs support, and show the formula, inputs, price date, and region in an annex.
- **Numbers need a baseline**: "30% cheaper" means nothing until it says than what, at which volume, over which period.
- **Plausible client details are still invented**: the author's title, the client's policies, baselines, or requirements, and owners or deadlines the user did not give become proposals ("proposed owner") or placeholders.
- **Context is not content**: opinions and hunches the user shares to brief you stay out; state a position only when the user asks to sign it.
- **Session details leak**: "as discussed", agent or tool names, local paths, internal labels, and private data mean nothing to the reader or must not leave the session.
- **Links disclose**: a URL can reveal hostnames, project or client names, folder structure, or grant access through a share or signed link.
- **One document serves one reader**: write for the decision maker and move other audiences' details to annexes or a separate document.
- **Formatting can fragment reasoning**: use prose for arguments, bullets for parallel items, and tables for comparisons; a wall of short bullets hides how the points connect.

## Documentation

- [Plain language guidelines](https://www.plainlanguage.gov/guidelines/) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companion skills: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans before sharing).
