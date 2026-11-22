---
name: polars
description: "Polars lazy tabular pipelines; hand off to Pandera, scikit-learn, DuckDB."
---

# Polars Dataframes

Default for new Python dataframe code; [duckdb](../../duckdb/SKILL.md) owns SQL over files/exploration, and pandas stays where existing code or libraries require it (do not migrate working pandas without measured need).

## Workflow

1. **Scan lazily, collect once (`2.1+`)**: chain `pl.scan_parquet` / `pl.scan_csv` / `.lazy()` (`filter`, `select`, `with_columns`, `group_by`, `join`, or `join_asof(..., strategy="backward")` for leakage-free point-in-time feature joins) and `.collect()` at boundaries; check pushdown with `.explain()`. Polars 2.x spills to disk past 80% available RAM (64 GB default disk budget) — verify disk headroom first.
1. **Enforce schemas at the edge**: pass `schema` / `schema_overrides`, cast explicitly, and validate with `pandera.polars` (`uv add 'pandera[polars]>=0.36.0'`, using `pandera.typing.polars.Series` for strict `ty` checking). Prefer `bin_intervals` / `bin_quantiles` (left-closed unless `right_closed=True`) over deprecated `cut` / `qcut`.
1. **Pass frames zero-copy**: scikit-learn accepts Polars (`set_output(transform="polars")` preserves Polars outputs); DuckDB queries in-scope frames directly (`duckdb.sql("select ... from df").pl()`, needs `pyarrow`). Call `to_pandas()` only when required.
1. **Test deterministically**: assert small literal frames via `polars.testing.assert_frame_equal`. Polars 2.0's default streaming engine does not preserve row order on `group_by`, joins, or `unpivot` — sort explicitly or set `maintain_order` (`maintain_order="left"` on joins).
1. **Stream cloud artifacts via `obstore`**: prefer `obstore` over `fsspec` for zero-copy Arrow and Parquet I/O across GCS, S3, and R2 ([object storage](../../python/references/database-and-jobs.md#object-storage-io)).

## Documentation

- [Polars user guide](https://docs.pola.rs/user-guide/) · [lazy API](https://docs.pola.rs/user-guide/lazy/) · [Pandera Polars](https://pandera.readthedocs.io/en/stable/polars.html)
- Releases: [Polars](https://github.com/pola-rs/polars/releases) · [2.0.0 notes](https://github.com/pola-rs/polars/releases/tag/py-2.0.0) · [Polars 2 upgrade](https://docs.pola.rs/releases/upgrade/2/)
