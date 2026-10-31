---
name: python-stack
description: "Develop Python projects and PEP 723 scripts: uv, Ruff, ty, Pydantic, pytest, async, HTTPX, structlog, OpenTelemetry, LangExtract."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-10-31"
---

# Python Stack

Maintain a small typed Python foundation and choose libraries for demonstrated requirements. Preserve the existing environment and conventions rather than restarting a scaffold for every feature.

## Workflow

Read only the matching guide and its required resources. Dataframe code in any profile, scripts included, defaults to [Polars](../python-mlops/references/polars.md).

## Task guides

<!-- guides:start -->

- [api-client](references/api-client/GUIDE.md): Build typed Python HTTPX API clients with bounded pagination and retries.
- [foundation](references/foundation/GUIDE.md): Python package layout, dependency choices, defaults, and project scaffolding.
- [langextract](references/langextract.md): Extract structured facts from text with LangExtract and source-grounded evidence.
- [observability](references/observability.md): Instrument Python services and agents: structlog logs, OpenTelemetry traces and metrics.
- [pydantic](references/pydantic.md): Typed validation, serialization, and settings boundaries.
- [python-async](references/python-async/GUIDE.md): Async design, cancellation, timeouts, and shutdown.
- [python-script](references/python-script/GUIDE.md): Standalone single-file utilities with PEP 723 inline metadata run by uv run --script.
- [python-testing](references/python-testing/GUIDE.md): Write Python tests with pytest, fixtures, property and mutation tests, and TDD.
- [ruff](references/ruff.md): Python linting, formatting, imports, and safe fixes.
- [ty](references/ty.md): Type diagnostics and environment resolution.
- [uv](references/uv.md): Dependency resolution, environments, packaging, and lockfiles.

<!-- guides:end -->
