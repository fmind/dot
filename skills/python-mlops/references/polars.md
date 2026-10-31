---
name: polars
description: "Transform tabular data with Polars lazy queries and expressions; hand frames to Pandera, scikit-learn, and DuckDB."
---

# Polars Dataframes

Use Polars for new dataframe code in Python; [duckdb](../../duckdb/SKILL.md) owns SQL over files and ad hoc exploration, and pandas stays where an existing project or a required library depends on it. Do not migrate working pandas code without a measured need.

## Workflow

1. **Scan lazily, collect once**: start from `pl.scan_parquet`, `pl.scan_csv`, or `.lazy()`, chain `filter`, `select`, `with_columns`, `group_by`, and `join`, then `.collect()` at the boundary. Inspect the optimized plan with `.explain()` when projection or predicate pushdown matters. Polars 2.0 spills to disk once a query passes 80% of available memory, with a 64 GB default disk budget, so check disk headroom before large collects.
1. **Fix schemas at the edge**: pass `schema` or `schema_overrides` when reading untyped sources, cast deliberately, and validate with Pandera's Polars backend (`uv add 'pandera[polars]'`, `import pandera.polars as pa`) before training or writing outputs. Bin with `bin_intervals` or `bin_quantiles` instead of the deprecated `cut`/`qcut`; they are left-closed unless `right_closed=True`.
1. **Hand frames over directly**: scikit-learn estimators accept Polars frames and `set_output(transform="polars")` keeps transformer outputs in Polars; DuckDB queries an in-scope frame by name (`duckdb.sql("select ... from df").pl()`) with `pyarrow` installed. `to_pandas()` requires pandas and pyarrow; convert only where a library demands pandas.
1. **Test with small literal frames**: build expected frames inline and compare with `polars.testing.assert_frame_equal`, which checks dtypes and order unless told otherwise. Polars 2.0 collects lazy queries on the streaming engine, which does not preserve row order for `group_by`, joins, or `unpivot`: sort explicitly or pass `maintain_order` (`maintain_order="left"` for joins) before comparing.

## Documentation

- [Polars user guide](https://docs.pola.rs/user-guide/) · [lazy API](https://docs.pola.rs/user-guide/lazy/) · [Pandera Polars](https://pandera.readthedocs.io/en/stable/polars.html)
- Releases: [Polars](https://github.com/pola-rs/polars/releases) · [Polars 2 upgrade guide](https://docs.pola.rs/releases/upgrade/2/)
