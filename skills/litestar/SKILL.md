---
name: litestar
description: Build Python ASGI services with Litestar and its official ecosystem skills. Use for Litestar scaffolding, routing, dependency injection, authentication, or request tests.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/litestar
  created: "2026-09-06"
  updated: "2026-09-11"
---

# Litestar

Use Litestar for Python web applications, with [python-stack](../python-stack/SKILL.md) supplying the project and quality defaults.

## Workflow

1. For a new service, follow [bootstrap](references/bootstrap.md) after the shared Python foundation; choose database integration only when needed.
1. Inspect the application with `uv run litestar --app <package>:app info`, `routes`, and `schema openapi`; these need no server and no extra, and autodiscovery does not find `src/<package>/__init__.py`. Read the source for the application factory, dependencies, and test client setup.
1. Select the upstream skill for the actual feature: routing, dependency injection, DTO/OpenAPI, authentication, middleware, templates and HTMX, or testing.
1. Keep the existing server and database choices. Run local request tests for success, invalid input, authorization, and lifespan behavior.

## Application resources

- [init.py](references/init.py) and [env.example](references/env.example) provide the database-backed application and example settings.
- [test_web.py](references/test_web.py) covers offline health, readiness failures, CORS, and server wiring; [test_integration.py](references/test_integration.py) and [conftest.py](references/conftest.py) provide opt-in Postgres qualification.

## Gotchas

- The upstream bundle also documents Advanced Alchemy, SQLSpec, msgspec, and Polyfactory. msgspec and Polyfactory ship inside Litestar, so never `uv add` them; keep Pydantic for request, response, and settings models, which Litestar registers automatically, and reach for msgspec `Struct` only in a measured hot path.
- A skills-only install does not install plugin hooks, reviewer agents, slash commands, or MCP servers; those are separate host integrations.

## Official Skills

Upstream: [litestar-org/litestar-skills](https://github.com/litestar-org/litestar-skills). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the Litestar application guidance.

## Documentation

- [Litestar documentation](https://docs.litestar.dev/latest/) · [Skills CLI](https://skills.sh/docs/cli)
