---
name: plotly
description: Create interactive Python charts with Plotly. Use for Express figures, graph objects, hover data, subplots, standalone HTML, and static image export.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/plotly
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Plotly

Use Plotly for interactive data figures; [pandas](../pandas/SKILL.md) and [polars](../polars/SKILL.md) own data preparation, while [manim](../manim/SKILL.md) owns animated mathematical scenes.

## Workflow

1. Establish the question, audience, data units, chart type, and delivery format. Add `plotly` with `uv add plotly`; start with Plotly Express and use graph objects for needed control.
1. Validate the underlying aggregation and ordering, then set explicit axis labels, units, category order, legend names, and hover fields. Show uncertainty where the data supports it.
1. Inspect the figure at its intended size for clipping, misleading scales, color accessibility, and dense traces; downsample or aggregate deliberately for large inputs.
1. Export a standalone local artifact with `fig.write_html("chart.html", include_plotlyjs=True, auto_open=False)` and open it to verify interaction offline.
1. For PNG/SVG/PDF, add `kaleido` only when needed and verify a compatible Chrome/Chromium installation. Use `fig.write_image(...)`, then inspect the exported artifact as well as figure data tests.

## Gotchas

- HTML embeds the figure data, including hover/custom data; remove sensitive columns before sharing.
- Current Kaleido needs a compatible browser; Python package installation alone does not prove static export works. Do not silently download a browser in a render path.
- WebGL traces can be rasterized inside vector exports. Lines connect points in input order, so sort deliberately.

## Official Skills

No consumer Agent Skill was found in the inspected [plotly/plotly.py](https://github.com/plotly/plotly.py) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Plotly Express](https://plotly.com/python/plotly-express/) · [HTML export](https://plotly.com/python/interactive-html-export/) · [Static export](https://plotly.com/python/static-image-export/)
