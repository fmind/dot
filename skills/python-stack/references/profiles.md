# Python Project Profiles

Choose the smallest profile that fits the project. This file selects owners; their skills supply application procedures and examples.

| Profile | Foundation and owner |
| --- | --- |
| Library | Use the shared package foundation, no runtime dependencies by default, and no console entry point. |
| CLI | Extend the foundation through [typer](../../typer/SKILL.md); [cli-contracts](../../cli-contracts/SKILL.md) owns flags, streams, and exit codes. |
| Web | Extend the foundation through [litestar](../../litestar/SKILL.md); use [django](../../django/SKILL.md) or [fastapi](../../fastapi/SKILL.md) for an existing or explicitly selected stack. |
| Agent | Start with [agents-cli](../../agents-cli/SKILL.md) and use [google-adk](../../google-adk/SKILL.md) for SDK code; retain the generator's layout and supported Python range. |
| Data, ML, notebooks | Extend the library foundation with only the required workload dependencies; use [duckdb](../../duckdb/SKILL.md) for queries and [marimo](../../marimo/SKILL.md) for reactive notebooks. Put imported runtime dependencies in the package dependencies and development-only tools in dependency groups. |
| Single-file utility | Use [python-script](../../python-script/SKILL.md) for PEP 723 metadata and execution. |
