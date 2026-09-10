---
name: polars
description: Transform tabular data with Polars expressions and lazy queries. Use for scans, joins, aggregations, streaming execution, and query-plan analysis.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/polars
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Polars

Use Polars for columnar transformations; [pandera](../pandera/SKILL.md) owns dataframe contracts and [pandas](../pandas/SKILL.md) owns pandas-specific behavior.

## Workflow

1. Inspect the locked version, input format/schema, data size, and required output order. Add `polars` with `uv add polars`; install optional IO dependencies only when needed.
1. Prefer `scan_csv` or `scan_parquet` for a lazy pipeline; select needed columns and filter early. Use expressions with `select`, `with_columns`, `filter`, `group_by`, and `join` rather than Python row loops.
1. Define casts, null/NaN handling, time zones, key uniqueness, and join cardinality explicitly. Do not assume pandas index alignment; Polars has no implicit row index.
1. Inspect `LazyFrame.explain()` and collect only at a materialization boundary. For large outputs, check current streaming and sink support before choosing `collect(engine="streaming")` or a sink.
1. Test exact schema and values with `polars.testing.assert_frame_equal`, including empty input, nulls, duplicate join keys, ordering, and invalid casts. Measure time and peak memory on representative input.

## Gotchas

- `read_*().lazy()` has already loaded the input; it cannot recover scan-level IO pushdown.
- Results without an ordering guarantee need an explicit sort when order is part of the output contract.
- Python UDFs inhibit optimization and can need explicit return dtypes. Use native expressions before `map_elements`. Streaming support depends on the operation and release.

## Official Skills

No consumer Agent Skill was found in the inspected [pola-rs/polars](https://github.com/pola-rs/polars) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Lazy execution](https://docs.pola.rs/user-guide/lazy/using/) · [Expressions](https://docs.pola.rs/user-guide/expressions/) · [Testing](https://docs.pola.rs/api/python/stable/reference/testing.html)
