# Python Project Profiles

Choose the smallest profile that fits the project. This file selects owners; their skills supply application procedures and examples.

| Profile | Foundation and owner |
| --- | --- |
| Library | Use the shared package foundation, no runtime dependencies by default, and no console entry point. |
| CLI | Extend the foundation through [typer](../../../../cli-development/references/typer/GUIDE.md); [cli-contracts](../../../../cli-development/references/cli-contracts.md) owns flags, streams, and exit codes. |
| Web | [litestar](../../../../python-web/references/litestar/GUIDE.md) extends the foundation for typed ASGI APIs and services; [django](../../../../python-web/references/django/GUIDE.md) owns ORM, admin, auth, and server-rendered pages through its own bootstrap; [fastapi](../../../../python-web/references/fastapi.md) covers an existing or generated scaffold. Use [nicegui](../../../../python-web/references/nicegui.md) or [gradio](../../../../python-web/references/gradio.md) for a single-user tool or model demo instead of a service. |
| Agent | Start with [agents-cli](../../../../agent-frameworks/references/agents-cli/GUIDE.md) and use [google-adk](../../../../agent-frameworks/references/google-adk.md) for SDK code; retain the generator's layout and supported Python range. |
| Data, ML, notebooks | Use [python-mlops](../../../../python-mlops/SKILL.md) for training, experiments, model delivery, and monitoring; retain project-selected workload dependencies. Use [duckdb](../../../../duckdb/SKILL.md) for local queries and [marimo](../../../../python-mlops/references/marimo.md) for reactive notebooks; consult installed source and official docs for dataframe, schema, and chart APIs. Keep runtime dependencies separate from development tools. |
| Single-file utility | Use [python-script](../../../../python-script/SKILL.md) for PEP 723 metadata and execution. |

Default to synchronous code. Choose async only for I/O-bound concurrency — many simultaneous network calls, streaming responses, or long-lived connections — and keep CPU-bound work, blocking drivers, and scripts synchronous; [python-async](../../python-async/GUIDE.md) owns task lifetime once async is chosen.
