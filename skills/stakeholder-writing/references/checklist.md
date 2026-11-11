# Reader Check

Review the draft as its reader. Fix failures, or tell the user why an exception serves this reader better. Items marked **firm** never bend.

## Skim

- **Message first**: does the opening sentence (or executive summary) state the conclusion, why it matters, and what to decide or do by when?
- **Navigation (documents)**: are title and headings short and literal, with formal sections opening on a bold conclusion sentence?
- **Bold skim**: does the bold text alone trace the argument without over-bolding?
- **Length**: is `wc -w` on the main text near the [default length](../SKILL.md#default-length), with methods, math, and raw data in linked annexes, any overrun justified to the user, and long sections closed by a take-home box?
- **Nothing to cut**: would the reader miss every remaining sentence, caveat, and section, with nothing repeated?

## Clarity

- **Key terms**: are unfamiliar terms, acronyms, units, and metrics defined (with unit, direction, and baseline) while daily vocabulary is left alone?
- **Literal sentences**: are arrows, slash chains, stacked parentheses, coined labels, metaphors, and unexplained internal names gone?
- **Plain prose**: is code formatting restricted to copyable commands, paths, and values—and omitted for non-technical readers?
- **Concrete support**: do abstract claims have examples, comparisons use tables with worded statuses, and figures (SVG, Mermaid, matplotlib) appear with conclusion captions and text alternatives where visuals beat prose?
- **Reader's language**: do language, number formatting, and date formatting match the reader?

## Trust

- **No invented facts (firm)**: does every client or author fact come from the user or a cited source (never an invented URL; name missing sources), with unknowns marked as assumptions, proposals, or placeholders—and `"I"` used for solo freelancer work instead of `"we"`?
- **Sourced, consistent figures (firm)**: does every number trace to a source or labeled assumption, match across sections, and add up (recomputed via script past a few numbers, with method and range in an annex)?
- **Cold reader (decisions and long docs)**: hand only the draft and 5–10 expected reader questions to a fresh subagent without session context; fix every wrong or ambiguous answer.
- **Neutral and limited**: are options compared on equal terms, background-only user opinions excluded, and assumptions, residual risks, and flip conditions stated?
- **Current facts (firm)**: are time-sensitive facts (versions, pins, governance, membership, ownership, prices, availability) verified today against authoritative live pages with the check date recorded and no negative claim inferred from silence?
- **Reused figures**: do third-party or redrawn figures cite source, link, and date, with cropped captures limited to private documents?
- **Links**: do key claims link to primary sources, pass [lychee](../../repository-docs/SKILL.md#workflow) (confirming 403/429 bot blocks and soft-404 200s in a browser, flagging login walls), stay accessible without leaking sensitive URL parts, and use visible placeholders when missing?

## Ready to share

- **No secrets or private data (firm)**: does `betterleaks stdin --redact < <file>` pass, with no "as discussed", agent/tool names, local paths, internal labels, session sections (verification notes, Decisions, Suggestions), or unauthorized data?
- **Beautiful and native (formal documents)**: does it apply `~/.agents/DESIGN.md` (Fmind Theme) or customer branding with colored hierarchy, readable spacing, and native destination features?
- **Renders at the destination**: do desktop, phone, and print renders load fonts cleanly; does Google Docs `.md` pass `--check-only` and read-back ([draft-doc](../../draft-doc/SKILL.md#workflow)); and do tables, callouts, and diagrams render properly?
