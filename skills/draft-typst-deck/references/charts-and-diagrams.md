# Charts, Diagrams, and Typst Escaping

Pure-Typst graphics compile crisply in vector or Retina resolution with zero `@preview/...` packages or external browser runtime dependencies. Limit each deck to **at most 3 comparative visuals** so slides stay breathable.

## Reusable Chart Helpers ([fmind-slides.typ](../templates/fmind-slides.typ))

1. **`bar-panel(title, subtitle, rows, width: 100%, height: auto)`**: `#F1F3F4` container (defaults to hugging row content cleanly; pass an explicit `height` when matching asymmetric panels). Put unit definitions and sample scope directly in `subtitle`.
1. **`stacked-bar-row(label, segments, val-text, ...)`**: compares parts summing to a total (`segments` is an array of `(pct, color)` tuples rendered left-to-right). Follow the `DESIGN.md` `chart-series` hue order (blue `#174EA6`, teal `#00636D`, amber `#934900`, purple `#681DA8`) before green (`#0D652D`) and red (`#A50E0E`). Keep totals `<= 100`.
1. **`broken-bar-row(label, pct, fill-col, val-text, broken: false, ...)`**: adds crisp white break notches near the right edge when an extreme baseline outlier would crush readable bars (`broken: true`, accompanied by `"out of scale"` in `val-text`).
1. **`step-card(num, title, desc, ...)` + `flow-arrow(label)`**: renders clean 3-step horizontal flows (`1 -> 2 -> 3`) using numbered badges, `#F1F3F4` / `#D2E3FC` / `#CEEAD6` semantic states, and vector `polygon(...)` arrowheads.

## Layout & Label Budgets

1. **Minimum font size**: never drop chart labels or footnotes below `12pt` (`11.5pt` absolute floor for compact multi-legend subtitles).
1. **Reserve metric column width**: when `val-text` combines counts and sub-metrics (for example `"187 (120 code + 67 edge)"`), size `right-width` to at least `230pt` on full-width (`876pt`) panels or `112pt–136pt` on half-width (`429pt`) panels so numbers never wrap mid-digit.
1. **Standalone `figures/*.typ` vs inline**: author standalone figures in `figures/*.typ` (with `#set page(width: auto, height: auto, margin: 4pt, fill: colors.canvas)`) when stakeholders also need standalone SVG/PNG exports for docs ([diagrams-as-code Typst guide](../../diagrams-as-code/references/typst.md)); run [build_typst_deck.py](../scripts/build_typst_deck.py) `check --render-figures` before compiling the main deck.

## Typst Escaping Rules

Typst distinguishes **content blocks (`[...]`)**, **string literals (`"..."`)**, and **raw inline spans (`` `...` ``)**. Mixing escapes leaves literal backslashes in rendered PDFs:

| Context               | Syntax                | Rule                                                                    | Example                 |
| :-------------------- | :-------------------- | :---------------------------------------------------------------------- | :---------------------- |
| Inline raw code       | `` `$100 ~5%` ``      | **Never escape**; backticks render characters verbatim                  | `` `EUR 0.42/run` ``    |
| String literal        | `"~5.81 $"`           | **Never escape** `$`, `~`, `*`; only escape `\"` or `\\`                | `val-text: "~5.81 $"`   |
| Content block         | `[Cost: ~5 \$]`       | Escape markup specials `\$`, `\*`, `\~`; use single `*bold*` (not `**`) | `[Budget cap: *\$200*]` |
| Flow arrows in labels | `"->"` vs arrow glyph | Avoid ASCII `->` in prose; use `flow-arrow(...)` or clean sentences     | `"Step 1 feeds Step 2"` |

Run [build_typst_deck.py](../scripts/build_typst_deck.py) `check` before inspecting PNGs — it fails immediately on unexpected `\$`, `\~`, or `\*` inside string literals or inline raw spans, and rejects `**...**` star warnings.
