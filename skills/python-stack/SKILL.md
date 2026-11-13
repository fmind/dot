---
name: python-stack
description: "Develop Python projects and PEP 723 scripts: uv, Ruff, ty, Pydantic, pytest, async, HTTPX, CLIs, and profiling with hyperfine."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-11-13"
---

# Python Stack

Maintain a lean, strictly typed Python foundation built on proven, well-maintained packages, minimal dependencies, and existing project conventions preserved in place.

## Workflow

Read only the matching guide and its required resources. Dataframe code defaults to [Polars](../python-mlops/references/polars.md); [argparse](references/argparse/GUIDE.md#defaults-for-new-clis) owns CLI contracts in any language. Requests to diagnose, debug, or profile authorize read-only observation and isolated reproduction — modify product code only when asked for a fix.

## Task guides

<!-- guides:start -->

- [api-client](references/api-client/GUIDE.md): Build typed Python HTTPX API clients with bounded pagination and retries.
- [argparse](references/argparse/GUIDE.md): Design CLI contracts (commands, flags, streams, exit codes, JSON) and build Python argparse or Typer CLIs.
- [foundation](references/foundation/GUIDE.md): Python package layout, dependency choices, uv/Ruff/ty tooling, and project scaffolding.
- [langextract](references/langextract.md): Extract structured facts from text with LangExtract and source-grounded evidence.
- [observability](references/observability.md): Instrument Python services and agents: structlog logs, OpenTelemetry traces and metrics.
- [performance](references/performance.md): Profile Python CPU and memory, and benchmark commands and HTTP load with hyperfine, oha, or Locust.
- [pydantic](references/pydantic.md): Typed validation, serialization, and settings boundaries.
- [python-async](references/python-async/GUIDE.md): Async design, cancellation, timeouts, and shutdown.
- [python-script](references/python-script/GUIDE.md): Standalone single-file utilities with PEP 723 inline metadata run by uv run --script.
- [python-testing](references/python-testing/GUIDE.md): Write Python tests with pytest, fixtures, property and mutation tests.

<!-- guides:end -->
