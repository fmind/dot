---
name: litestar
description: Build Python ASGI services with Litestar and its official ecosystem skills. Use for routing, dependency injection, DTOs, authentication, or Litestar tests.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/litestar
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Litestar

Use Litestar for Python web applications, with [python-stack](../python-stack/SKILL.md) supplying the project and quality defaults.

## Workflow

1. Inspect the installed Litestar version, application factory, routes, dependencies, and test client setup before editing.
1. Select the upstream skill for the actual feature: routing, dependency injection, DTO/OpenAPI, authentication, middleware, or testing.
1. Keep the existing server and database choices. Run local request tests for success, invalid input, authorization, and lifespan behavior.

## Gotchas

- The bundle is opinionated and also covers optional libraries such as Advanced Alchemy, SQLSpec, msgspec, and Polyfactory. Install guidance only for dependencies the project uses.
- A skills-only install does not install plugin hooks, reviewer agents, slash commands, or MCP servers; those are separate host integrations.

## Official Skills

Upstream: [litestar-org/litestar-skills](https://github.com/litestar-org/litestar-skills). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the Litestar application guidance.

## Documentation

- [Litestar documentation](https://docs.litestar.dev/latest/) · [Skills CLI](https://skills.sh/docs/cli)
