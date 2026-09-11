# Python Project Profiles

Choose the smallest profile that fits the project. This file selects owners; their skills supply application procedures and examples.

| Profile | Foundation and owner |
| --- | --- |
| Library | Use the shared package foundation, no runtime dependencies by default, and no console entry point. |
| CLI | Extend the foundation through [typer](../../typer/SKILL.md); [cli-contracts](../../cli-contracts/SKILL.md) owns flags, streams, and exit codes. |
| Web | [litestar](../../litestar/SKILL.md) extends the foundation for typed ASGI APIs and services; [django](../../django/SKILL.md) owns ORM, admin, auth, and server-rendered pages through its own bootstrap; [fastapi](../../fastapi/SKILL.md) covers an existing or generated scaffold. Use [nicegui](../../nicegui/SKILL.md) or [gradio](../../gradio/SKILL.md) for a single-user tool or model demo instead of a service. |
| Agent | Start with [agents-cli](../../agents-cli/SKILL.md) and use [google-adk](../../google-adk/SKILL.md) for SDK code; retain the generator's layout and supported Python range. |
| Data, ML, notebooks | Extend the library foundation with workload dependencies already selected by the project. Use [duckdb](../../duckdb/SKILL.md) for local queries and [marimo](../../marimo/SKILL.md) for reactive notebooks; consult installed source and official docs for dataframe, schema, and chart APIs. Keep runtime dependencies separate from development tools. |
| Single-file utility | Use [python-script](../../python-script/SKILL.md) for PEP 723 metadata and execution. |

Default to synchronous code. Choose async only for I/O-bound concurrency — many simultaneous network calls, streaming responses, or long-lived connections — and keep CPU-bound work, blocking drivers, and scripts synchronous; [python-async](../../python-async/SKILL.md) owns task lifetime once async is chosen.
