---
name: draft-typst-deck
description: "Create 16:9 Typst slides, branded visual cards, PDF decks, and private Google Slides via gws."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-typst-deck
  created: "2026-11-13"
  updated: "2026-11-14"
---

# Draft Typst Slide Deck

Build crisp **16:9 (`960pt x 540pt`) Typst slide decks** and **standalone branded visual cards** with editable `.typ` sources, compiled PDF/PNG/PPTX outputs, speaker notes, and optional Google Drive / Google Slides publishing via [gws](../gws/SKILL.md). Default to the Fmind Theme (`~/.agents/DESIGN.md`: `#FFFFFF` canvas, `#174EA6` accent, `Google Sans`), or substitute a client's brand tokens and fonts (never mix brands).

## Format Choice (Typst Deck vs Editable Slides vs Visual Card)

Apply [humanize](../humanize/SKILL.md) ([outlines](../humanize/references/outlines.md), [primitives](../humanize/references/primitives.md)) on every deck:

1. **Typst PDF / Retina PPTX -> Private Google Slides (default)**: adapt [fmind-slides.typ](templates/fmind-slides.typ) + [deck.typ](templates/deck.typ), add `#speaker-note("...")`, compile with `check --pptx`, and publish via `upload --google-slides --source-dir .`. Drive converts the `.pptx` privately (Retina images + editable speaker notes) without public URLs.
1. **Editable-shape Google Slides**: when stakeholders must edit text boxes directly in Slides, adapt [editable_deck.py](templates/editable_deck.py) (`Google Sans` native shapes + 2x Typst PNG cards via `uv run --script`), or patch an existing template via `gws slides presentations batchUpdate` (`replaceAllText`), and upload with `--google-slides --source-dir .`.
1. **Standalone branded PNG/SVG card**: adapt [figure-card.typ](templates/figure-card.typ) (`#show: brand-card.with(width: 640pt)`) or compile `figures/*.typ` with `render` (or `check --render-figures`) for Docs ([draft-doc](../draft-doc/SKILL.md)), reports, email, or web.

## Slide Restraint Rules (Zero Slide Dumps)

- **One idea, one focal centerpiece**: pair an action-led headline with **one** visual (`kpi-card` strip, `bar-panel`, `split-cards`, or `step-card` flow). Never stack two heavy visuals on one slide.
- **Max 30 visible words, zero prose backticks**: use `#hl[...]` or `#pill(...)` instead of code styling on non-code words, enforce `--max-words 30` in `check`, and move caveats and formulas to `#speaker-note("...")`.
- **Readable minimums & escaping**: titles 26 pt, cards 15–16 pt, chart labels 12+ pt; follow [charts-and-diagrams.md](references/charts-and-diagrams.md#typst-escaping-rules) (`$`, `~`, `*` differ between `"..."` and `[...]`).

## Workflow (`check`, `render`, inspect, `upload`)

Run [build_typst_deck.py](scripts/build_typst_deck.py) with isolated stdlib Python (`python3 -I`):

1. **Validate deck, enforce word ceiling, export PNG/PDF/PPTX**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py check deck.typ \
     --expected-slides 4 --max-words 30 --pptx --json
   ```

   Pass `--render-figures --figure-format png` to also compile `figures/*.typ`, or compile one standalone card directly:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py render figure-card.typ --json
   ```

   Fails closed on bad Typst escapes, empty `*bold*` stars, missing fonts, word-limit overruns, or slide overflow.

1. **Inspect every PNG** (`_preview/<stem>-*.png` or card output) for spacing, contrast, and calm per [verification-and-drive.md](references/verification-and-drive.md).

1. **Dry-run and publish to Drive / Google Slides (after explicit approval)**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py upload deck.pptx \
     --drive-folder "<FOLDER_ID>" --google-slides --source-dir . --dry-run --json
   ```

   Rerun without `--dry-run` (or pass `--file-id "<ID>"` to update in place); `--source-dir .` syncs `.typ` and root `.py` sources into Drive `assets/<slug>/`. Verify remote integrity before finishing.
