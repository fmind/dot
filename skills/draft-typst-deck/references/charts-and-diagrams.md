# Charts, Diagrams, Branded Images, and Typst Escaping

Pure-Typst graphics compile in crisp vector SVG or 2× Retina PNG (`--ppi 192`) without `@preview/...` packages or a headless browser. Keep each deck to **1 focal visual per slide** (`<=3` comparative charts per deck).

## Reusable Slide & Brand Card Helpers ([fmind-slides.typ](../templates/fmind-slides.typ))

- **`hl(body, role: "warning-surface")`**: rounded inline highlight pill (`#FEEFC3` warm amber default, or `"selection"`, `"success-surface"`) to draw eyes to the single number or decision ask.
- **`speaker-note(note)`**: attaches per-slide speaker notes (`str`) compiled invisibly and extracted via `typst query` when generating `.pptx` / Google Slides.
- **`split-cards(left-title, left-body, right-title, right-body, ...)`**: clean two-column comparison (neutral baseline panel vs `#D2E3FC` highlighted recommendation).
- **`bar-panel(title, subtitle, rows)`**, **`stacked-bar-row`**, **`broken-bar-row`**: comparative horizontal charts respecting `DESIGN.md` `chart-series` order (`#174EA6`, `#00636D`, `#934900`, `#681DA8` before `#0D652D` green and `#A50E0E` red). Pass `right-width >= 112pt` (half-width) or `230pt` (full-width) so numbers never wrap; use `broken: true` for outliers.
- **`step-card(num, title, desc)` + `flow-arrow(label)`**: clean 3-step horizontal flows with semantic fill states.

## Standalone Branded Images (`figures/*.typ`)

Author standalone diagrams, architecture cards, or social/doc visuals in `figures/*.typ` using `#set page(width: auto, height: auto, margin: 12pt, fill: colors.canvas)` and importing `../fmind-slides.typ` (or `~/.agents/themes/typst/fmind.typ` per [Typst guide](../../diagrams-as-code/references/typst.md)):

```bash
python3 -I ~/.agents/skills/draft-typst-deck/scripts/build_typst_deck.py check deck.typ \
  --render-figures --figure-format png --ppi 192 --json
```

Use `--figure-format svg` for web/HTML reports and `png --ppi 192` for Google Docs, email, or `python-pptx` Google Slides.

## Typst Escaping Rules {#typst-escaping-rules}

Typst treats **content blocks (`[...]`)**, **string literals (`"..."`)**, and **inline code (`` `...` ``)** differently:

| Context         | Syntax           | Rule                                                  | Example                |
| :-------------- | :--------------- | :---------------------------------------------------- | :--------------------- |
| Inline raw code | `` `$100 ~5%` `` | Never escape `$`, `~`, `*`; use only for literal code | `` `mise run check` `` |
| String literal  | `"~5.81 $"`      | Never escape `$`, `~`, `*`; escape only `\"` or `\\`  | `val-text: "~5.81 $"`  |
| Content block   | `[Cost: ~5 \$]`  | Escape markup specials `\$`, `\*`, `\~`; single `*b*` | `[Cap: *\$200*]`       |

`build_typst_deck.py check` fails automatically on bad escapes and empty `*bold*` star warnings.
