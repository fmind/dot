# Humanize Pre-Send Checklist

Review as a busy reader before sharing. Items marked **firm** never bend.

## 1. Respect Human Time (Signal vs Noise)

- Opening line or callout states the core signal, impact, and ask in <10 seconds.
- Implementation plumbing, raw tool logs, and repetitive background are removed or collapsed into `<details>` / annexes.
- Length matches [default length](../SKILL.md#default-length); slides stay ≤30 words with 1 visual focal point.

## 2. Clean Prose & Rich Visuals

- **Clean backtick discipline**: backticks appear strictly on literal code, CLI commands, paths, or rare disambiguating identifiers — never on product names, statuses, regions, or metrics.
- **Zero terminal jargon**: no arrow chains (`->`), slash-stacked nouns, or agent session headers (`Verification`, `Decisions`, `Suggestions`, tool names, bare IDs).
- **Visual hierarchy applied**: the draft uses the medium's highlights (`<mark>`, alerts/callouts), dividers, KPI/status blocks, tables, or Typst/Mermaid visuals — never a flat grey wall of text.

## 3. Trust & Privacy (**firm**)

- **No invented facts**: every claim, date, URL, and figure comes from verified sources; unknowns are explicitly labeled.
- **Sourced, rounded figures**: ranges name their baseline, unit, period, and date.
- **Leak-free**: `betterleaks stdin --redact < <file>` exits 0; zero secrets, signed URLs, local paths, or customer identifiers cross system boundaries.
- **Rendered live**: visual output checked (PNG frames for Typst/Slides, live DOM for HTML, read-back check for Docs/Mail).
