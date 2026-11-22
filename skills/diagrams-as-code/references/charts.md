---
name: charts
description: "Quantitative data charts with Altair/vl-convert and Matplotlib: honest scales, CVD palettes, direct labels, PNG/SVG export."
---

# Quantitative Data Charts

Render reproducible evaluation, benchmark, FinOps, and analytical charts directly from code (`Altair` or `Matplotlib`) with honest scales, colorblind-safe contrast, and zero browser dependencies. [Diagrams as code](../SKILL.md) owns format selection (use [typst-deck](../../draft/references/typst-deck/references/charts-and-diagrams.md) `bar-panel` for simple 3–6 bar deck comparisons).

## Tool Selection

- **Default (`Altair` + `vl-convert-python`)**: add `altair>=6.3.0` and `vl-convert-python` (or run via ephemeral `uv run --no-project --with altair --with vl-convert-python`) for bar/line/dot comparisons, threshold sweeps, and faceted small multiples exported statically to PNG/SVG without a headless browser.
- **Dense diagnostics (`Matplotlib`)**: add `matplotlib>=3.11.2` for ROC/PR/calibration curves, residual/error distributions, custom annotations, or publication typography (`matplotlib.use("Agg")` headless).
- **Keep code beside exports**: commit the generating `.py` script (and pinned inputs or seed) next to static `.png`/`.svg` outputs so numbers stay reproducible and auditable.

## Visual & Statistical Rules

1. **Honest scales & uncertainty**: start bar and area axes at `0` (annotate any explicit break); avoid dual Y-axes and pie charts (`> 3` slices—use sorted horizontal bars). Include explicit axis units, direction (*"lower is better"*), reference baseline, sample size (`n=...`), and error bars/CI/IQR rather than bare means.
1. **Brand & CVD-safe palettes**: apply the client palette when provided (never mix brands), else follow `~/.agents/DESIGN.md` categorical order: primary `#174EA6`, info `#00636D`, warning `#934900`, type `#681DA8`. Reserve `#0D652D` (gain) and `#A50E0E` (loss) for semantic deltas only, pair color with dash/marker/direct labels, and use perceptually uniform sequential scales (`viridis`, `cividis`)—never `jet`/rainbow.
1. **High data-ink ratio & small multiples**: cap single panels at `<= 6` series (split dense series into faceted small multiples with shared axes). Prefer direct end-of-series labels over detached legends, mute gridlines (`#F1F3F4` / `#9AA0A6`), and remove top/right spines.
1. **Readable exports on every theme**: set an explicit `#FFFFFF` figure/canvas background (transparent dark text vanishes in dark viewers), keep plot text `>= 8pt` (`>= 10–12pt` for decks/docs) with `>= 4.5:1` contrast, and export Retina PNG (`ppi=192`–`300`) or vector SVG (`plt.rcParams["svg.fonttype"] = "none"`):

   ```python
   # Altair static export without a browser
   chart.properties(background="#FFFFFF").save("out.png", ppi=192)
   chart.properties(background="#FFFFFF").save("out.svg")
   ```

1. **Verify visually & numerically**: inspect every rendered PNG/SVG directly for clipped titles, overlapping tick/end labels, and exact numeric parity with surrounding prose/tables; audit substantive figures with `fmind-review-visuals` ([subagent](../../subagent/SKILL.md)).

## Gotchas

- **Default `Altair` 5,000-row cap**: pre-aggregate in [polars](../../mlops/references/polars.md) or [sql](../../sql/SKILL.md) before plotting instead of embedding raw tables into Vega-Lite JSON.
- **Unquoted / colliding long category labels**: switch to horizontal bars rather than rotated 45° X-axis labels, and reserve explicit padding (`bbox_inches="tight"`, `pad_inches=0.15` in Matplotlib).
- **Misleading log scales**: annotate log ticks clearly and explain why multiplicative spread warrants log scaling.

## Documentation

- [Altair docs](https://altair-viz.github.io/) · [vl-convert](https://github.com/vega/vl-convert) · [Matplotlib](https://matplotlib.org/stable/) · [fmind/theme DESIGN.md](https://github.com/fmind/theme/blob/main/DESIGN.md)
- Companions: [mlops/training](../../mlops/references/training.md), [draft/typst-deck](../../draft/references/typst-deck/GUIDE.md), [humanize](../../humanize/SKILL.md), [finops](../../finops/SKILL.md).
