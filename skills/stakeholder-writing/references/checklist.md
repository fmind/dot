# Reader Check

Run every item before delivering. Fix each failure, and tell the user about anything you could not verify.

## Skim test

- **Summary first**: a reader who reads only the title and the executive summary, about 120 words, knows the conclusion, why it matters to them, and what to decide or do, by when.
- **Navigable structure**: the title names the subject, section headings are short names, and each section opens with a bold sentence that states its conclusion.
- **Bold skim**: the bold text alone tells the argument: the opening sentence of each section and about one phrase per other paragraph.
- **Section summaries**: each long section ends with a short "Take-home messages" box; short sections have none.
- **Short main body**: as short as the decision allows, with the word count measured, not estimated; technical details, methods, calculations, and raw data sit in annexes, and the main text points to each annex it relies on.

## Clarity

- **Key terms**: every term, acronym, unit, and metric this reader may not know is explained in the Key terms block after the summary, terms they use daily are not, and each metric has its unit, direction, and baseline.
- **Literal sentences**: no arrows, slash chains, stacked parentheses, coined labels, metaphors, or unexplained internal names.
- **Concrete support**: each abstract claim has an example, each comparison has a table with numbered options and a colored status with a word for ratings, numbers and flows that read faster as a figure have one, and each figure has a caption that states its conclusion and a table or text alternative.
- **Reader's language**: the language, number format, and date format match the reader.

## Trust

- **Sourced figures**: trace every number in the summary, tables, and headings to a cited source or a labeled assumption, and delete or label the rest; each estimate shows its method and range in an annex.
- **Neutral and private**: options are compared on the same criteria and conditions, and opinions the user shared only as context are absent.
- **No invented facts**: facts about the client and the author come from the user or a cited source; everything else is a labeled assumption, a proposal, or a placeholder.
- **Consistent numbers**: each figure matches everywhere it appears, and totals add up; recompute them with a script when there are more than a few.
- **Stated limits**: assumptions, residual risks, and what would change the recommendation are visible.
- **Reused figures**: each third-party image or redrawn figure has a source line with a link and date; captures appear only in private documents, and public ones use redrawn figures or permitted images.
- **Working links**: key claims link to internal or external sources, links resolve, external ones point to primary sources where possible, and missing internal links are visible placeholders.

## Ready to share

- **No session details**: no "as discussed", agent or tool names, local paths, or internal labels.
- **No secrets or private data**: the final file passes `gitleaks stdin --redact < <file>`, and it contains only what this reader may see.
- **Designed look**: the document uses the Fmind design or the customer's brand, with color in headings, summary, figures, and statuses, embedded fonts that load, and badges rather than emoji for statuses in HTML.
- **Readable layout**: body text is at least 16 px on screen and 10 pt in print, headings and spacing separate sections, paragraphs stay short, and no section is a wall of raw text or unformatted data.
- **Renders at the destination**: for HTML, desktop and phone screenshots look right, figures are legible in the document's color scheme, and printing keeps colors and tables readable; for Markdown, the target renderer shows tables correctly.
- **Identified**: the document type, status (draft or final), audience, author, and date appear at the top, one field per line.
