# Slide Decks and Presentations

Build executive briefings, architecture reviews, talk decks, and client workshops people grasp at a glance. Apply `~/.agents/DESIGN.md` (Fmind Theme) by default, or the customer's brand guide and slide master when working for a client (never mix brands).

## Format and Tooling Choice

1. **Self-contained HTML/CSS deck (default for standalone shares, PDF export, and talks)**: single `.html` (`16:9` `1280x720`, `@page { size: 1280px 720px; margin: 0; }`, keyboard arrow navigation, embedded WOFF2 Google Sans + Google Sans Code, and Typst/D2/SVG/Mermaid diagrams via [diagrams-as-code](../../diagrams-as-code/SKILL.md)). Exports pixel-exact PDFs via headless Chrome (`--print-to-pdf`).
1. **Google Slides (`gws slides`) for collaborative Workspace decks**: inspect IDs and master layouts first with `gws slides presentations get --params '{"presentationId":"<ID>"}'`, validate atomic `presentations.batchUpdate` payloads (`createSlide`, `insertText`, `replaceAllText`, `createImage`) with `--dry-run`, apply under user authority, and read back to verify ([gws services](../../gws/references/services.md#calendar-and-slides)). Never send Markdown to Slides API; store editable Typst/D2/SVG/Mermaid sources in Drive `assets/` ([diagrams-as-code](../../diagrams-as-code/SKILL.md)).
1. **Typst (`fmind.typ` / `touying` / `polylux`) or Marp**: use when a course or talk repository standardizes on `.typ` or Marp Markdown; commit editable `.typ`/`.md` sources beside exported `.pdf`.

## Slide Structure and Pacing

Unlike prose headings ([style.md](style.md#titles-headings-and-section-summaries)), slides are scanned one screen at a time—**every slide title states the takeaway**:

- **Assertion-evidence layout**: write a 1-line action title stating the conclusion (`"Spot VMs cut nightly batch spend by 60% with <5 min retry delay"`), backed by **one** focal proof element (diagram, chart, 3-column comparison table, or ≤4 short bullets).
- **Strict density ceiling**: `25–40` words on-slide (`≤60` on comparison tables), ≥`32–36 px` (`24–28 pt`) titles, ≥`20–24 px` (`16–18 pt`) body text, ≥`16 px` (`12 pt`) diagram/axis labels, and ≥`4.5:1` text contrast on a `#FFFFFF` canvas (no dark backgrounds, gradients, drop shadows, or decorative stock/AI art).
- **Default 8–12 slide decision/architecture arc**:
  1. **Title**: literal topic, audience, author, date.
  1. **Executive takeaway**: recommendation, key metric, decision needed, and deadline.
  1. **Context & baseline**: current pain, volume, and measured baseline.
  1. **Options compared**: shared criteria table (including doing nothing), recommended row highlighted.
  1. **Target architecture**: one clean flow/component diagram ([diagrams-as-code](../../diagrams-as-code/SKILL.md)).
  1. **Security & controls**: trust boundaries, data residency, auth, and failure handling.
  1. **Cost & timeline**: conservative ranges against baseline, drivers, and milestones.
  1. **Risks & flip conditions**: top 2–3 risks, mitigations, and what would change the choice.
  1. **Next steps**: action, owner, and date.
  1. **Backup / Annex**: formulas, methodology, benchmarks, and primary source links for Q&A.

## Visual Verification (Mandatory)

Render every slide at `1280x720` in headless Chrome / [playwright](../../playwright/SKILL.md) (or export PDF via `gws drive files export --params '{"fileId":"<ID>","mimeType":"application/pdf"}' --output deck.pdf` for Google Slides) and inspect every frame for clipped text, overflowing cards, overlapping connectors, or unreadable labels before delivery.
