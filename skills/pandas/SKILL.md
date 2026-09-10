---
name: pandas
description: Analyze and transform data with pandas. Use for dataframe indexing, joins, groupby, nullable dtypes, time series, and reliable file round trips.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/pandas
  created: "2026-09-10"
  updated: "2026-09-10"
---

# pandas

Use pandas where its indexed dataframe semantics and ecosystem fit the project; [polars](../polars/SKILL.md) owns Polars and [pandera](../pandera/SKILL.md) owns schema validation.

## Workflow

1. Inspect the installed version and input schema, especially identifiers, timestamps, missing values, and index meaning. Add `pandas` with `uv add pandas` and only needed format engines.
1. Read with explicit columns, dtypes, and date parsing where inference can lose information. Preserve leading-zero identifiers and distinguish missing values from empty strings and zero.
1. Prefer vectorized operations and explicit `.loc` assignments. Declare merge keys and use `validate=` for intended join cardinality; inspect unmatched rows when completeness matters.
1. State grouping choices for missing keys and categorical levels, time-zone conversions, and required sorting. Treat Copy-on-Write behavior according to the pinned pandas release.
1. Test with `pandas.testing.assert_frame_equal`, retaining dtype/index checks. Include duplicate keys, missing data, empty frames, and a read/write round trip; measure memory before expanding to full data.

## Gotchas

- Chained assignment does not reliably update the original frame and fails under Copy-on-Write; assign to the owning frame in one operation.
- pandas joins can match null keys, unlike typical SQL expectations; test that case explicitly.
- Implicit index alignment can introduce missing values or reorder results. Avoid row-wise `apply` when vectorized operations express the same behavior.

## Official Skills

No consumer Agent Skill was found in the inspected [pandas-dev/pandas](https://github.com/pandas-dev/pandas) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [User guide](https://pandas.pydata.org/docs/user_guide/index.html) · [Copy-on-Write](https://pandas.pydata.org/docs/user_guide/copy_on_write.html) · [Merge](https://pandas.pydata.org/docs/reference/api/pandas.merge.html)
