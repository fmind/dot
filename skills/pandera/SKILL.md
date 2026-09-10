---
name: pandera
description: Validate tabular data with Pandera. Use for dataframe schemas, column checks, coercion rules, lazy error collection, and pandas or Polars boundaries.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/pandera
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Pandera

Use Pandera for dataframe contracts; [pydantic](../pydantic/SKILL.md) owns object/API validation, while [pandas](../pandas/SKILL.md) and [polars](../polars/SKILL.md) own transformations.

## Workflow

1. Choose the actual dataframe backend and inspect compatible versions. Install `uv add "pandera[pandas]"` or `uv add "pandera[polars]"`; import `pandera.pandas` or `pandera.polars` explicitly.
1. Define `DataFrameSchema` or a `DataFrameModel` with declared columns, dtypes, nullability, uniqueness, and domain checks. Decide whether extra columns and coercion are allowed.
1. Validate ingestion and output boundaries, preserving the returned validated frame when coercion or filtering applies. Use `lazy=True` when the caller needs a combined report of schema failures.
1. Test valid input plus missing columns, wrong types, nulls, duplicate keys, out-of-range values, and empty frames. Assert the expected failure category without logging sensitive rows.
1. Measure validation on representative data; configure sampling only when partial validation meets the contract, and state what remains unchecked.

## Gotchas

- Backend APIs and supported checks differ; do not paste pandas decorators into a Polars pipeline.
- Lazy error collection is not Polars lazy execution. A LazyFrame schema check may not evaluate row-level data; test the chosen validation depth explicitly.
- An inferred schema describes the sample; it is not an approved business contract. Coercion can erase evidence of bad source values.

## Official Skills

No consumer Agent Skill was found in the inspected [unionai-oss/pandera](https://github.com/unionai-oss/pandera) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [DataFrame models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [Polars validation](https://pandera.readthedocs.io/en/stable/polars.html) · [Lazy validation](https://pandera.readthedocs.io/en/stable/lazy_validation.html)
