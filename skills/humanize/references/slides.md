# Slide Decks and Presentations

Build high-signal visual decks busy audiences grasp in 5 seconds per slide. Apply `~/.agents/DESIGN.md` (Fmind Theme: `#FFFFFF` canvas, `#174EA6` accent, `Google Sans`) by default, or the customer's brand guide (never mix brands).

## Visual Rules (Zero AI Slide Dumps)

- **One idea, one visual centerpiece per slide**: pair a **takeaway headline** (`Caching cut p95 latency by 42%`, never `Architecture Overview`) with **one** focal visual (KPI strip, 2-card contrast, 3-step flow, or comparative bar chart).
- **Radical density cap**: target `4–10` slides, **≤30 on-slide words** (`≤50` for comparison tables), **zero backticks**, `≥35%` open whitespace, ≥15 pt body text, and dark-on-light contrast (`≥4.5:1`). Move backup tables and explanations to **speaker notes** or a linked memo.
- **Highlight selectively**: use one tinted pill (`#pill`), highlight span (`#hl`), or left-accent callout per slide so the eye knows where to land immediately.

## Format and Tooling Choice

1. **Typst (`draft-typst-deck`) — default for PDF decks, Google Slides publishing, and branded cards**: deterministic 16:9 styling, pure-Typst charts/cards, inline speaker notes, PDF output, and private **Google Slides** publishing (`build_typst_deck.py check --pptx` + `upload --pptx ... --google-slides`, which embeds high-DPI slide visuals and speaker notes privately in Drive without public image URLs).
1. **Editable-shape Google Slides (when stakeholders must edit text boxes directly in Slides)**: build a native `.pptx` with `Google Sans` text/card shapes plus 2× Retina Typst `figures/*.typ` PNG charts (`uv run --with python-pptx`), and upload with Drive `mimeType: application/vnd.google-apps.presentation`. Keep `.typ` figure sources in Drive `assets/`.
1. **Self-contained HTML/CSS deck**: browser `1280x720` presentation for interactive web sharing or Chrome `--print-to-pdf`.

> [!CAUTION]
> Never use Google Slides API `createImage` (`presentations.batchUpdate`) for confidential diagrams: `createImage.url` requires a world-readable public URL and records `source_url` inside the presentation. Upload `.pptx` to Drive with `mimeType: application/vnd.google-apps.presentation` instead.

## Default 6–10 Slide Decision Arc

1. **Cover**: clear title, audience, date.
1. **Executive takeaway**: 2–3 KPI highlights + decision asked by date.
1. **Current bottleneck**: measured baseline vs target.
1. **Options compared**: crisp comparison (baseline vs recommended, zero clutter).
1. **How it works**: one clean flow/architecture visual ([diagrams-as-code](../../diagrams-as-code/SKILL.md)).
1. **Risks & decision**: top 2 controls + 3-step rollout with owners.
1. **Backup** _(only when needed)_: assumptions, methodology, primary links.

## Verification

Inspect every compiled PNG frame (`_preview/<stem>-*.png`, or exported PDF via `gws drive files export` for edited Google Slides) to confirm zero text clipping, overlaps, or dense walls of text before sharing.
