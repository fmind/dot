---
name: stakeholder-writing
description: "Write short emails, messages, docs, reports, and proposals for other people: message first, plain words, details in annexes; fact-check drafts and posts."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/stakeholder-writing
  created: "2026-10-25"
  updated: "2026-11-08"
---

# Stakeholder Writing

Write text that busy people read in seconds and act on, from a chat message to a decision memo. The user should be able to send it without rewriting. This skill owns the content, the length, and the final check. Delivery stays with [draft-mail](../draft-mail/SKILL.md) (Gmail), [draft-doc](../draft-doc/SKILL.md) (Google Docs), [github-pull-request](../github-pull-request/SKILL.md) and [github-issues](../github-issues/SKILL.md) (GitHub), [documentation-site](../documentation-site/SKILL.md) (Zensical), and [repository-docs](../repository-docs/SKILL.md) (README and AGENTS.md).

**Short beats complete.** Readers want the message first and open annexes or links when they want depth. Every sentence, caveat, and section costs them time, so keep only what changes what they understand, decide, or do. Adapt any guideline that does not help this reader and tell the user why. Three rules never bend: invent no facts, disclose no secrets or private data, and never let a figure mislead.

## Default length

Start from the default for the type and count the main text with `wc -w`; annexes do not count. These are defaults, not limits: go longer when the task is complex, such as several options, real risk, or a reader who must act on detail.

- **Chat message**: about 50 words.
- **Email**: about 150 words; a reply about 100.
- **Status update, PR, or issue text**: about 200 words.
- **Document for teammates**: a summary of two or three sentences, then about one page (400 words).
- **Decision memo or proposal**: a summary of about 100 words, then about one page (500 words).
- **Report or analysis**: a summary of about 100 words, then about two pages (800 words).

## Workflow

1. **Frame the reader and the ask**: note who reads, what they already know, the questions they ask first ([reader lenses](references/outlines.md#reader-lenses)), and the one thing you want from them, by when. Pick the type, the destination, and the reader's language, then start from the matching [outline](references/outlines.md). Ask the user when an unknown reader or goal would change the content.
1. **Put the message first**: write the one sentence the reader should remember and open with it. In an email or chat message, that sentence is the answer or the ask.
1. **Use only the facts the message needs**: take them from the user and from primary sources, and record each figure's source, date, and scope. Link claims inline where this reader can open them ([links](references/style.md#links-and-sensitivity)). Turn each unknown into a labeled assumption or a placeholder.
1. **Write plainly and show with figures when relevant**: follow the [style guide](references/style.md): everyday words, short active sentences, one idea per paragraph, and a concrete example for an abstract point. Use prose for reasoning, a short list for parallel items, and a table for comparisons. Create figures such as SVG, Mermaid, or matplotlib charts and diagrams when a visual communicates a flow, architecture, timeline, or trend faster than text, each with a caption that states its conclusion ([visuals](references/style.md#examples-tables-and-visuals)). Bold at most one phrase per paragraph, the one that carries the message. Use code formatting only for a command, path, or value the reader must copy, and none for non-technical readers.
1. **Use simple titles and section names, and keep formal structure for formal documents**: give documents a simple title that names the subject and simple, short section names, putting the conclusion in the section's bold first sentence ([headings](references/style.md#titles-headings-and-section-summaries)). Reports, proposals, and decision memos open with a summary of the conclusion, the decision, and its deadline, compare the options on the same criteria (including doing nothing, and keeping the user's labels), argue the recommendation once with its risks, and end with next steps. Key terms, supporting figures, methods, and evidence go to annexes; add ratings or a metadata block only when this reader needs them. Give them a designed look with the destination's [native features](references/style.md#destination-and-platform-features), the [HTML](templates/report.html) or [Markdown](templates/report.md) template, and `~/.agents/DESIGN.md` or the customer's brand guide, asking for it if missing. Emails and chat messages use no headings; status updates and teammate documents keep only simple sections unless the reader needs more.
1. **Cut**: reread as the reader. Delete every sentence they would not miss, known background, caveats that do not change their decision, and repeats. Move detail to an annex or a link, then compare the length with the default.
1. **Run the reader check**: review the draft against the [checklist](references/checklist.md), fix what fails, and render it where it will be read, such as HTML at desktop and phone widths with [playwright](../playwright/SKILL.md). Tell the user what you could not verify and where you went past the default length. To fact-check an existing draft, article, post, or talk, run the checklist's Trust section and report findings with the date checked; rewrite only when asked.

## Gotchas

- **Completeness is not quality**: a teammate email with a summary, Key terms, and a risk section is a report nobody asked for.
- **Dense prose costs the reader**: arrows, slash chains, stacked parentheses, coined labels, and metaphors save the writer words and cost the reader minutes.
- **Session habits leak**: "as discussed", agent or tool names, local paths, internal labels, and session reply sections (verification notes, Decisions, Suggestions) mean nothing to the reader, and private data must not leave the session.
- **Figures need context**: a cost, effort, or risk estimate is a model; give a range rounded to what the inputs support, a baseline ("30% cheaper" than what, at which volume), and the formula, inputs, and price date in an annex.
- **Plausible details are still invented**: the author's title, the client's policies, baselines, or requirements, owners or deadlines the user did not give, risk ratings or confidence levels with no stated basis, and claims added to strengthen the case, such as what users will notice, become proposals ("proposed owner"), placeholders, or questions for the user.
- **Context is not content**: opinions and hunches the user shares to brief you stay out; state a position only when the user asks to sign it.

## Documentation

- [Plain language guidelines](https://digital.gov/guides/plain-language) · [Google developer documentation style guide](https://developers.google.com/style) · [Bottom line up front](https://en.wikipedia.org/wiki/BLUF_(communication))
- Companion skills: [playwright](../playwright/SKILL.md) (render checks), [diagrams-as-code](../diagrams-as-code/SKILL.md) (diagrams), [code-security](../code-security/SKILL.md) (secret scans before sharing).
