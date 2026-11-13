---
name: draft-typst-deck
description: "Create 16:9 Typst slides, branded visual cards, PDF decks, and private Google Slides via gws."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-typst-deck
  created: "2026-11-13"
  updated: "2026-11-13"
---

# Draft Typst Slide Deck

Build crisp **16:9 (`960pt x 540pt`) Typst slide decks** and **branded visual cards** with editable `.typ` sources, compiled PDF/PNG/PPTX outputs, speaker notes, and optional Google Drive / Google Slides publishing via [gws](../gws/SKILL.md). Default to the Fmind Theme (`~/.agents/DESIGN.md`: `#FFFFFF` canvas, `#174EA6` accent, `Google Sans`), or substitute a client's brand tokens and fonts (never mix brands).

## Format Choice (PDF vs Google Slides vs Editable Shapes)

Apply [humanize](../humanize/SKILL.md) and its [slides guide](../humanize/references/slides.md) on every deck:

1. **Typst PDF / Retina PPTX → Private Google Slides (default)**: author [fmind-slides.typ](templates/fmind-slides.typ) + [deck.typ](templates/deck.typ), include `#speaker-note("...")`, export `--pptx`, and upload with `--google-slides`. Drive converts the `.pptx` privately (`ppt/media/` + speaker notes) into a Google Slides URL without exposing public image links.
1. **Editable-shape Google Slides**: when stakeholders must edit on-slide text boxes directly in Slides, adapt [editable_deck.py](templates/editable_deck.py) (`Google Sans` native cards + 2× Typst `figures/*.typ` PNGs via `uv run --script`) and upload with `--google-slides --source-dir .`.
1. **Standalone branded images**: compile `figures/*.typ` (2× Retina PNG/SVG) via `--render-figures` for Google Docs ([draft-doc](../draft-doc/SKILL.md)), reports, or web/social cards ([diagrams-as-code](../diagrams-as-code/references/typst.md)).

## Slide Restraint Rules (Zero Slide Dumps)

- **One idea, one visual centerpiece per slide**: pair an action-led headline with **one** focal block (`kpi-card` strip, `bar-panel`, `split-cards`, or `step-card` flow).
- **≤30 words & no prose backticks**: emphasize key asks or metrics with `#hl[...]` or `#pill(...)` and reserve backticks strictly for literal code or CLI syntax; move explanations and formulas to `#speaker-note("...")`.
- **Readable minimums & escaping**: titles `26pt`, cards `15–16pt`, chart labels `>=12pt`; follow [charts-and-diagrams.md](references/charts-and-diagrams.md#typst-escaping-rules) (`$`, `~`, `*` differ between `"..."` and `[...]`).

## Workflow (`check`, inspect, `upload`)

Run [build_typst_deck.py](scripts/build_typst_deck.py) with isolated Python stdlib (`python3 -I`, zero external packages):

1. **Validate, compile PDF + PNGs (+ `.pptx` with speaker notes), and verify slide count**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py check deck.typ \
     --expected-slides 4 --pptx --json
   ```

   Pass `--render-figures --figure-format png` to export standalone `figures/*.typ` cards. Fails closed on bad Typst escapes, empty `*bold*` stars, missing fonts, or slide overflow.

1. **Inspect every PNG (`_preview/<stem>-*.png`)** for spacing, label fit, and visual calm per [verification-and-drive.md](references/verification-and-drive.md).

1. **Dry-run and publish to Drive / Google Slides (after explicit approval)**:

   ```bash
   python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py upload deck.pptx \
     --drive-folder "<FOLDER_ID>" --google-slides --source-dir . --dry-run --json
   ```

   Rerun without `--dry-run` (or upload `deck.pdf` / `--file-id "<ID>"`). Verify remote integrity (MD5+size for PDF/binary `.pptx`; Drive type + `gws slides` slide-count parity for `--google-slides`).
