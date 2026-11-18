---
name: python-stack
description: "Develop and publish Python packages and PEP 723 scripts: uv, PyPI, Ruff, ty, Pydantic, pytest, async, HTTPX, CLIs, and hyperfine."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-stack
  created: "2026-06-23"
  updated: "2026-11-17"
---

# Python Stack

Maintain a lean, strictly typed Python foundation built on proven, well-maintained packages, minimal dependencies, and existing project conventions preserved in place.

## Workflow

Load the matching guide(s) for every active concern (e.g., domain guide + [pydantic](references/pydantic.md) + [python-testing](references/python-testing/GUIDE.md)), and audit non-trivial Python, CLI, or test changes with `fmind-review-python`, `fmind-review-cli`, and `fmind-review-test` ([subagent](../subagent/SKILL.md)). Dataframe code defaults to [Polars](../python-mlops/references/polars.md); [argparse](references/argparse/GUIDE.md#defaults-for-new-clis) owns CLI contracts in any language. Requests to diagnose, debug, or profile authorize read-only observation and isolated reproduction — modify product code only when asked for a fix.

## Task guides

<!-- guides:start -->

- [api-client](references/api-client/GUIDE.md): Build typed Python HTTPX API clients with bounded pagination and retries.
- [argparse](references/argparse/GUIDE.md): Design CLI contracts (commands, flags, streams, exit codes, JSON) and build Python argparse or Cyclopts CLIs.
- [foundation](references/foundation/GUIDE.md): Python package layout, PyPI distribution metadata, dependency choices, uv/Ruff/ty tooling, and project scaffolding.
- [observability](references/observability.md): Instrument Python services and agents: structlog logs, OpenTelemetry traces and metrics.
- [performance](references/performance.md): Profile Python CPU and memory, and benchmark commands and HTTP load with hyperfine, oha, or Locust.
- [pydantic](references/pydantic.md): Typed validation, serialization, and settings boundaries.
- [python-async](references/python-async/GUIDE.md): Async design, cancellation, timeouts, and shutdown.
- [python-script](references/python-script/GUIDE.md): Standalone single-file utilities with PEP 723 inline metadata run by uv run --script.
- [python-testing](references/python-testing/GUIDE.md): Write Python tests with pytest, fixtures, property and mutation tests.

<!-- guides:end -->

## Documentation

- [Python 3](https://docs.python.org/3/) · [uv](https://docs.astral.sh/uv/) · [Ruff](https://docs.astral.sh/ruff/) · [ty](https://docs.astral.sh/ty/) · [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) · [pytest](https://docs.pytest.org/en/stable/) · [Cyclopts](https://cyclopts.readthedocs.io/en/stable/) · [HTTPX2](https://pydantic.dev/docs/httpx2/get-started/) · [stamina](https://stamina.hynek.me/) · [structlog](https://www.structlog.org/en/stable/) · [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- Companions: [python-web](../python-web/SKILL.md), [python-mlops](../python-mlops/SKILL.md), [agent-frameworks](../agent-frameworks/SKILL.md), [mise](../mise/SKILL.md), [project-scaffolding](../project-scaffolding/SKILL.md).
