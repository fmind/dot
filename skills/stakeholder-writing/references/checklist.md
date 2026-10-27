# Reader Check

Review the draft as its reader would. Fix what fails, or keep the exception when it serves this reader better and tell the user why. The items marked **firm** never bend.

## Skim

- **Summary first**: does a reader who stops after the title and the executive summary know the conclusion, why it matters to them, and what to decide or do, by when?
- **Navigation**: does the title name the subject, are headings short names, and does each section open with a bold conclusion sentence?
- **Bold skim**: does the bold text alone tell the argument, without bolding everything?
- **Length**: is the body as short as the decision allows, measured rather than estimated, with methods, calculations, and raw data in annexes the text points to? Do long sections close with a take-home box?

## Clarity

- **Key terms**: is every unfamiliar term, acronym, unit, and metric explained, each metric with its unit, direction, and baseline, and the reader's daily vocabulary left alone?
- **Literal sentences**: are arrows, slash chains, stacked parentheses, coined labels, metaphors, and unexplained internal names gone?
- **Concrete support**: does each abstract claim have an example, each comparison a table with numbered options and worded statuses, and each figure a caption that states its conclusion and a text alternative?
- **Reader's language**: do the language, number format, and date format match the reader?

## Trust

- **No invented facts (firm)**: does every fact about the client and the author come from the user or a cited source, with the rest labeled as an assumption, a proposal, or a placeholder?
- **Sourced, consistent figures (firm)**: does every number in the summary, tables, and headings trace to a source or a labeled assumption, match everywhere it appears, and add up? Recompute with a script when there are more than a few, and show each estimate's method and range in an annex.
- **Neutral and limited**: are options compared on the same criteria and conditions, opinions shared only as context absent, and assumptions, residual risks, and what would change the recommendation visible?
- **Reused figures**: does each third-party image or redrawn figure carry a source line with a link and date, with captures only in private documents?
- **Links**: do key claims link to sources, do the links resolve, can this reader open them, and do their URLs reveal nothing the reader should not see? Are missing internal links visible placeholders?

## Ready to share

- **No secrets or private data (firm)**: does the final file pass `gitleaks stdin --redact < <file>`, and does it hold only what this reader may see, with no "as discussed", agent or tool names, local paths, or internal labels?
- **Beautiful and native**: does it look designed, in `~/.agents/DESIGN.md` (Fmind Theme) or customer branding if available, with color in headings, summary, figures, and statuses, comfortable type and spacing, and the destination's native features rather than imitations?
- **Renders at the destination**: do HTML screenshots look right at desktop and phone widths, in print, and with fonts loaded? Does a Google Docs native `.md` deliverable pass `compile_markdown_doc.py --check-only` with all Mermaid and SVG figures compiled to `@2x` Base64 PNG references and editable sources exported to `--assets-dir` for the Drive `assets/` folder ([draft-doc](../../draft-doc/SKILL.md))? Does the target renderer show Markdown tables, callouts, and diagrams correctly?
- **Identified**: do the type, status, audience, author, and date appear at the top, one field per line?
