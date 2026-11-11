# Reader Check

Review the draft as its reader. Fix failures, or tell the user why an exception serves this reader better. Items marked **firm** never bend.

## Skim

- **Message first**: opening sentence or executive summary states conclusion, impact, and ask with deadline.
- **Navigation & bold skim**: short literal headings, bold section-opening conclusions, bold text carrying the argument alone, and main text near [default length](../SKILL.md#default-length) (`wc -w`, annexes separate, long sections closed by a take-home box, zero repeats).

## Clarity

- **Plain prose & terms**: everyday sentences without shorthand/metaphors, backticks only on copyable literals, unfamiliar terms/metrics defined (unit, direction, baseline), and locale-matched language/numbers/dates.
- **Concrete support**: examples for abstract claims, worded status tables, and conclusion-captioned figures with text alternatives where visuals beat prose.

## Trust

- **No invented facts (firm)**: every claim comes from the user or a cited primary source (never an invented URL), unknowns are labeled assumptions/proposals/placeholders, and solo freelancer drafts use `"I"`, not `"we"`.
- **Sourced, consistent figures (firm)**: every number traces to a source or assumption, matches across sections, and adds up (recomputed via script past a few numbers, with method/range in an annex).
- **Current facts (firm)**: time-sensitive facts (versions, governance, prices, availability) are verified today against authoritative live pages with check date recorded and no negative inferred from silence.
- **Neutral & cold-read**: equal criteria across options, flip conditions and gaps stated, third-party figures properly cited/redrawn, accessible leak-free links checked via [lychee](../../repository-docs/SKILL.md#workflow), and high-stakes docs tested on a fresh cold-reader subagent with 5–10 reader questions.

## Ready to share

- **No secrets or session leaks (firm)**: `betterleaks stdin --redact < <file>` passes, with zero session sections, tool/agent names, local paths, or unauthorized data.
- **Rendered cleanly**: matches `~/.agents/DESIGN.md` or customer branding across desktop/phone/print, and Google Docs `.md` passes `--check-only` and read-back ([draft-doc](../../draft-doc/SKILL.md#workflow)).
