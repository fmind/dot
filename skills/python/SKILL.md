---
name: python
description: "Build Python packages, CLIs, APIs, web apps, PEP 723 scripts: uv, Ruff, ty, pytest, Pydantic, Litestar, Django, FastAPI, OTel."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python
  created: "2026-11-21"
  updated: "2026-11-23"
---

# Python Engineering

Maintain lean, strictly typed Python packages, CLIs, web services, and PEP 723 scripts using proven libraries and existing repo conventions.

## Workflow

Load the matching domain guide(s) below plus `language` and `testing`. Defaults: [mlops](../mlops/SKILL.md) for dataframes/ML, [argparse](references/argparse/GUIDE.md#defaults-for-new-clis) for CLIs, and `litestar` for web services (`django` for ORM/admin, `ui` for Gradio/NiceGUI). Audit non-trivial changes with `fmind-review-code` and `fmind-review-python` plus matching `sre`, `simplicity`, `test`, `cli`, `api`, `frontend`, `data`, or `security` reviewers ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [api-client](references/api-client/GUIDE.md): Build typed Python HTTPX/httpx2 clients with bounded pagination/retries.
- [api-design](references/api-design.md): Design HTTP/RPC/SDK wire contracts: RFC 9457 errors, cursor pagination, idempotency, OpenAPI, and SemVer.
- [argparse](references/argparse/GUIDE.md): Design CLI contracts (streams, exits, JSON) and build argparse or Cyclopts CLIs.
- [async](references/async.md): Build asyncio/AnyIO concurrency with TaskGroup cancellation, loop_factory, bounded pools, and SIGTERM drain.
- [database-and-jobs](references/database-and-jobs.md): Configure async Postgres/SQLite pools, Alembic, obstore, pgqueuer, and Cloud Tasks.
- [django](references/django/GUIDE.md): Build Django applications with ORM, admin, authentication, Granian serving, and native testing.
- [fastapi](references/fastapi.md): Maintain existing FastAPI services and generated agent scaffolds.
- [foundation](references/foundation/GUIDE.md): Configure Python package layout, PyPI metadata, uv/Ruff/ty tooling, workspaces, and project scaffolding.
- [language](references/language.md): Apply Python 3.14+ idioms, strict ty typing, exception chaining, subprocess bounds, and atomic file I/O.
- [litestar](references/litestar/GUIDE.md): Build Litestar ASGI applications, request/header boundaries, HTMX/SSE streaming, and scaffolding.
- [observability](references/observability.md): Instrument Python services/agents with structlog and OpenTelemetry OTLP.
- [performance](references/performance.md): Profile Python CPU/memory and benchmark CLIs/HTTP with hyperfine, oha, Locust.
- [pydantic](references/pydantic.md): Typed validation, serialization, and settings boundaries.
- [script](references/script/GUIDE.md): Build standalone PEP 723 single-file Python scripts run via uv run.
- [security-and-auth](references/security-and-auth.md): Implement OIDC/OAuth2, JWT, Argon2id, webhook HMAC, CSRF, and HTTP security headers.
- [testing](references/testing/GUIDE.md): Write Python tests with pytest, fixtures, property, mutation, and opt-in BDD tests.
- [ui](references/ui.md): Build Gradio model demos and NiceGUI dashboards or browser utilities.

<!-- guides:end -->

## Documentation

- Companions: [mlops](../mlops/SKILL.md), [agent-frameworks](../agent-frameworks/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [mise](../mise/SKILL.md), [bootstrap](../github/references/bootstrap.md), [sql](../sql/SKILL.md).
