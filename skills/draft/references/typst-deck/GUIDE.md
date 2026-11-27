---
name: typst-deck
description: "Create 16:9 Typst decks, PDF/PPTX, and figure cards; upload via gws."
---

# Draft Typst Slide Deck

Build **16:9 (`960pt x 540pt`) Typst slide decks** (plus `figures/*.typ` cards) with PDF/PNG/PPTX outputs and speaker notes. For **native editable Google Slides** or client template fills, use [draft/slides](../slides/GUIDE.md). Delegate prose, narrative, and visual tokens to [humanize](../../../humanize/SKILL.md) and customer brand or `~/.agents/DESIGN.md`.

## Templates

1. **16:9 Deck**: adapt [fmind.typ](templates/fmind.typ) + [fmind-slides.typ](templates/fmind-slides.typ) + [deck.typ](templates/deck.typ) with `#speaker-note("...")`.
1. **Companion PNG/SVG card**: adapt [figure-card.typ](templates/figure-card.typ) (`#import "/fmind-slides.typ": *` + `#show: brand-card.with(width: 640pt)`) or place figures in `figures/*.typ` (root-relative import works in both `check --render-figures` and standalone `render figures/fig.typ`) for [draft/doc](../doc/GUIDE.md) or reports.

## Workflow (`check`, `render`, inspect, upload)

Run [build_typst_deck.py](scripts/build_typst_deck.py) ([pptx_builder.py](scripts/pptx_builder.py)) with `python3 -I` (escaping rules in [charts-and-diagrams.md](references/charts-and-diagrams.md#typst-escaping-rules)):

1. **Validate deck, word cap, and export** (zero prose paragraphs; `~40–90` visible words on visual/card live slides, `~60–110`w async; pass `appendix: true` on closing `Annex · Sources` slides so `--max-words` still guards main slides):

   ```bash
   python3 -I ~/.agents/skills/draft/references/typst-deck/scripts/build_typst_deck.py check deck.typ \
     --expected-slides 4 --max-words 90 --pptx --json
   ```

   Pass `--render-figures --figure-format png` for `figures/*.typ` (`--lang fr-FR --theme-name neutral` for French or customer decks), or `render figures/fig.typ --json` standalone. Fails closed on empty `*bold*` stars, missing fonts, word overruns, or overflow; lint narrative prose via [humanize](../../../humanize/SKILL.md#pre-send-gate).

1. **Inspect PNGs & review adversarially**: read every `_preview/<stem>-*.png` frame visually per [verification-and-drive.md](references/verification-and-drive.md), then fan out `fmind-review-visuals` + `fmind-review-human` (copy/insight per [humanize](../../../humanize/SKILL.md#pre-send-gate); add `fmind-review-frontend` / `fmind-review-factcheck` when needed; [subagent](../../../subagent/SKILL.md)).
1. **Upload to Drive / Google Slides (after explicit approval)** via shared [`drive_upload.py`](../../../gws/scripts/drive_upload.py) (`--dry-run` first):

   ```bash
   python3 -I ~/.agents/skills/gws/scripts/drive_upload.py deck.pptx \
     --drive-folder "<FOLDER_ID>" --name "<Title>" \
     --target-mime application/vnd.google-apps.presentation --dry-run --json
   ```

   Rerun without `--dry-run` (or `--file-id "<ID>"` to update in place); omit `--target-mime` to upload raw `.pdf` or `.pptx`.

## Documentation

- [Typst docs](https://typst.app/docs/) · [Google Slides API](https://developers.google.com/workspace/slides/api/guides/presentations) · [fmind/theme](https://github.com/fmind/theme) · [Typst releases](https://github.com/typst/typst/releases)
- Companions: [draft/slides](../slides/GUIDE.md), [diagrams-as-code](../../../diagrams-as-code/SKILL.md), [humanize](../../../humanize/SKILL.md), [gws](../../../gws/SKILL.md), [draft/doc](../doc/GUIDE.md).
