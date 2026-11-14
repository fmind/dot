# Charts, Diagrams, Branded Images, and Typst Escaping

Pure-Typst graphics compile to 2x Retina PNG (`--ppi 192`) or vector SVG without `@preview/...` packages or a headless browser. Keep each slide to **one focal visual** and each deck to three comparative charts or fewer.

## Reusable Slide & Brand Card Helpers ([fmind-slides.typ](../templates/fmind-slides.typ))

- **`brand-card(width: 640pt, margin: 16pt, fill: colors.canvas)`**: page show-rule wrapper for standalone visual cards and figures so `width: 100%` and `1fr` inside `kpi-card`, `bar-panel`, `split-cards`, and `card` never collapse to `0pt` on `width: auto` pages (start from [figure-card.typ](../templates/figure-card.typ); pass `width: 440pt` for Google Docs).
- **`hl(body, role: "warning-surface")`**: rounded highlight pill (`#FEEFC3` warm amber default, or `"selection"`, `"success-surface"`) replacing raw backticks on metrics and asks.
- **`speaker-note(note)`**: attaches per-slide speaker notes (`str`) compiled invisibly and extracted via `typst eval` for `.pptx` / Google Slides.
- **`split-cards(...)`**, **`card(...)`**, **`callout(...)`**, **`kpi-card(...)`**: semantic surfaces obeying `DESIGN.md` light contrast.
- **`bar-panel(title, subtitle, rows)`**, **`stacked-bar-row`**, **`broken-bar-row`**: comparative horizontal charts respecting `DESIGN.md` categorical order (`primary` `#174EA6`, `information` `#00636D`, `warning` `#934900`, `type` `#681DA8` before green/red). Size `right-width` wide enough (around 120–230 pt) so values stay single-line; use `broken: true` for outliers.
- **`step-card(num, title, desc)` + `flow-arrow(...)`**: accepts either positional `#flow-arrow("Signal")` or named `#flow-arrow(step: 1, caption: "clone", length: 34pt, dir: ltr)` (`dir: ttb` for vertical flows).

## Standalone Branded Images (`render` & `figures/*.typ`)

Start from [figure-card.typ](../templates/figure-card.typ) or place reusable visuals in `figures/*.typ` and render directly:

```bash
# Single standalone card (PNG at 192 PPI by default, or --format svg)
python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py render figure-card.typ --json

# Render all figures/*.typ alongside a deck check
python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py check deck.typ \
  --render-figures --figure-format png --ppi 192 --json
```

Choose `--format png` (192 PPI) for Google Docs, Gmail, social cards, and `editable_deck.py` embeds; choose `--format svg` for HTML reports ([diagrams-as-code](../../diagrams-as-code/references/typst.md)).

## Typst Escaping Rules

Typst treats **content blocks (`[...]`)**, **string literals (`"..."`)**, and **inline code (`` `...` ``)** differently:

| Context         | Syntax           | Rule                                                  | Example                |
| :-------------- | :--------------- | :---------------------------------------------------- | :--------------------- |
| Inline raw code | `` `$100 ~5%` `` | Never escape `$`, `~`, `*`; use only for literal code | `` `mise run check` `` |
| String literal  | `"~5.81 $"`      | Never escape `$`, `~`, `*`; escape only `\"` or `\\`  | `val-text: "~5.81 $"`  |
| Content block   | `[Cost: ~5 \$]`  | Escape markup specials `\$`, `\*`, `\~`; single `*b*` | `[Cap: *\$200*]`       |

`build_typst_deck.py check` and `render` fail automatically on bad escapes and empty `*bold*` star warnings.
