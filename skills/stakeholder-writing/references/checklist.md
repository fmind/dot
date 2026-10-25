# Reader Check

Run every item before delivering. Fix each failure, and tell the user about anything you could not verify.

## Two-minute test

- **Summary first**: a reader who reads only the title and the executive summary, about 120 words, knows the conclusion, why it matters to them, and what to decide or do, by when.
- **Headings tell the story**: every heading states a conclusion.
- **Short main body**: about 500 words of prose before the annexes, counted, not estimated; methods, calculations, and raw data sit in annexes.

## Clarity

- **Defined terms**: every term, acronym, and metric this reader may not know is defined at first use, terms they use daily are not, and each metric has its unit, direction, and baseline.
- **Literal sentences**: no arrows, slash chains, stacked parentheses, coined labels, metaphors, or unexplained internal names.
- **Concrete support**: each abstract claim has an example, each comparison has a table, and each visual has a caption that states its conclusion.
- **Reader's language**: the language, number format, and date format match the reader.

## Trust

- **Sourced figures**: trace every number in the summary, tables, and headings to a cited source or a labeled assumption, and delete or label the rest; each estimate shows its method and range in an annex.
- **No invented facts**: facts about the client and the author come from the user or a cited source; everything else is a labeled assumption, a proposal, or a placeholder.
- **Consistent numbers**: each figure matches everywhere it appears, and totals add up; recompute them with a script when there are more than a few.
- **Stated limits**: assumptions, residual risks, and what would change the recommendation are visible.
- **Working links**: links resolve and point to primary sources where possible.

## Ready to share

- **No session details**: no "as discussed", agent or tool names, local paths, or internal labels.
- **No secrets or private data**: the final file passes `gitleaks stdin --redact < <file>`, and it contains only what this reader may see.
- **Renders at the destination**: for HTML, desktop and phone screenshots look right and printing keeps tables readable; for Markdown, the target renderer shows tables correctly.
- **Identified**: the author, date, audience, and status (draft or final) appear at the top.
