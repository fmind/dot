---
name: python-stack
description: "Develop Python projects and PEP 723 scripts: uv, Ruff, ty, Pydantic, pytest, async, HTTPX, Typer and CLI contracts, observability, LangExtract, debugging, profiling, benchmarks."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-11-07"
---

# Python Stack

Maintain a small typed Python foundation and choose libraries for demonstrated requirements. Preserve the existing environment and conventions rather than restarting a scaffold for every feature.

## Workflow

Read only the matching guide and its required resources. Dataframe code in any profile, scripts included, defaults to [Polars](../python-mlops/references/polars.md). The [cli-contracts](references/cli-contracts.md) guide applies to any CLI, whatever its language. A request to diagnose, debug, or profile authorizes investigation, not fixes: observe read-only, reproduce in an isolated temporary directory, and change product code only when the user also asks for a fix.

## Task guides

<!-- guides:start -->

- [api-client](references/api-client/GUIDE.md): Build typed Python HTTPX API clients with bounded pagination and retries.
- [cli-contracts](references/cli-contracts.md): Design any CLI's commands, flags, streams, exit codes, and JSON output, in any language.
- [foundation](references/foundation/GUIDE.md): Python package layout, dependency choices, defaults, and project scaffolding.
- [langextract](references/langextract.md): Extract structured facts from text with LangExtract and source-grounded evidence.
- [observability](references/observability.md): Instrument Python services and agents: structlog logs, OpenTelemetry traces and metrics.
- [performance](references/performance.md): Profile Python CPU and memory, and benchmark commands and HTTP load with hyperfine, oha, or Locust.
- [pydantic](references/pydantic.md): Typed validation, serialization, and settings boundaries.
- [python-async](references/python-async/GUIDE.md): Async design, cancellation, timeouts, and shutdown.
- [python-script](references/python-script/GUIDE.md): Standalone single-file utilities with PEP 723 inline metadata run by uv run --script.
- [python-testing](references/python-testing/GUIDE.md): Write Python tests with pytest, fixtures, property and mutation tests.
- [ruff](references/ruff.md): Python linting, formatting, imports, and safe fixes.
- [ty](references/ty.md): Type diagnostics and environment resolution.
- [typer](references/typer/GUIDE.md): Typer application code, help, completion, and command tests.
- [uv](references/uv.md): Dependency resolution, environments, packaging, and lockfiles.

<!-- guides:end -->
