# Reader Check

Review the draft as its reader would. Fix what fails, or keep the exception when it serves this reader better and tell the user why. The items marked **firm** never bend.

## Skim

- **Message first**: does a reader who stops after the first sentence, or the summary of a formal document, know the conclusion, why it matters to them, and what to decide or do, by when?
- **Navigation (documents)**: are the title and section names simple and short, with each section of a formal document opening with a bold conclusion sentence?
- **Bold skim**: does the bold text alone tell the argument, without bolding everything?
- **Length**: is the main text, counted with `wc -w`, near the [default length](../SKILL.md#default-length) for its type, with methods, calculations, and raw data in annexes the text points to? Is any extra length earned by the task's complexity and explained to the user? Do long sections close with a take-home box?
- **Nothing to cut**: would the reader miss each sentence, caveat, and section, and is nothing said twice?

## Clarity

- **Key terms**: is every unfamiliar term, acronym, unit, and metric explained, each metric with its unit, direction, and baseline, and the reader's daily vocabulary left alone?
- **Literal sentences**: are arrows, slash chains, stacked parentheses, coined labels, metaphors, and unexplained internal names gone?
- **Plain prose**: is code formatting limited to commands, paths, or values the reader must copy, with none for non-technical readers?
- **Concrete support**: does each abstract claim have an example, each comparison a table with labeled options and worded statuses, and do figures (SVG, Mermaid, matplotlib) appear where a chart or diagram communicates faster than text, each with a caption that states its conclusion and a text alternative?
- **Reader's language**: do the language, number format, and date format match the reader?

## Trust

- **No invented facts (firm)**: does every fact about the client and the author come from the user or a cited source (never an invented URL: name the missing source instead), with the rest labeled as an assumption, a proposal, or a placeholder? Does every "we" name a team that exists, since a freelancer's own work is "I"?
- **Sourced, consistent figures (firm)**: does every number in the summary, tables, and headings trace to a source or a labeled assumption, match everywhere it appears, and add up? Recompute with a script when there are more than a few, and show each estimate's method and range in an annex.
- **Cold reader (for decisions and long documents)**: list the 5–10 questions the reader will ask, give only the document to a fresh subagent without our context, and fix every question it answers wrongly or finds ambiguous.
- **Neutral and limited**: are options compared on the same criteria and conditions, opinions shared only as context absent, and assumptions, residual risks, and what would change the recommendation visible?
- **Current facts (firm)**: are time-sensitive claims (versions, pins, governance, membership, ownership, prices, availability) checked today against the authoritative live page rather than a point-in-time announcement or draft date, with the check date stated and no negative claim inferred from silence?
- **Reused figures**: does each third-party image or redrawn figure carry a source line with a link and date, with captures only in private documents?
- **Links**: do key claims link to sources, do the links resolve ([lychee flags](../../repository-docs/SKILL.md#workflow)), and does each cited page, opened, support its claim? A lychee 403 or 429 can be bot blocking and a 200 can be a soft 404, so confirm in a browser and report login walls as unverifiable. Can this reader open them, and do their URLs reveal nothing the reader should not see? Are missing internal links visible placeholders?

## Ready to share

- **No secrets or private data (firm)**: does the final file pass `betterleaks stdin --redact < <file>`, and does it hold only what this reader may see, with no "as discussed", agent or tool names, local paths, internal labels, or session reply sections (verification notes, Decisions, Suggestions)?
- **Beautiful and native (formal documents)**: does it look designed, in `~/.agents/DESIGN.md` (Fmind Theme) or customer branding if available, with color in headings, summary, figures, and statuses, comfortable type and spacing, and the destination's native features rather than imitations?
- **Renders at the destination**: do HTML screenshots look right at desktop and phone widths, in print, and with fonts loaded? Does a Google Docs native `.md` deliverable pass `--check-only` and the read-back in [draft-doc](../../draft-doc/SKILL.md#workflow)? Does the target renderer show Markdown tables, callouts, and diagrams correctly?
