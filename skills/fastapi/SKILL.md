---
name: fastapi
description: Maintain FastAPI Python services using its official skill. Use for FastAPI routes, dependencies, request models, streaming, or generated agents-cli services.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/fastapi
  created: "2026-09-06"
  updated: "2026-09-06"
---

# FastAPI

Use this for an existing or explicitly chosen FastAPI service, including an [agents-cli](../agents-cli/SKILL.md) scaffold; [litestar](../litestar/SKILL.md) remains the default for new ordinary web apps.

## Workflow

1. Inspect the installed FastAPI version and generated project contract before changing the app or dependencies.
1. Choose the official framework guidance, then adapt routes, validation, dependency lifetimes, or streaming to the existing application.
1. Run local request and lifespan tests and inspect the OpenAPI output when the public schema changes.

## Gotchas

- The skill is shipped within the framework source package and is discovered by the skills CLI. Installing the Python package alone does not establish host discovery.
- Do not convert an agents-cli FastAPI scaffold to Litestar while implementing an agent feature.

## Official Skills

Upstream: [fastapi/fastapi](https://github.com/fastapi/fastapi). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the FastAPI application guidance.

## Documentation

- [FastAPI documentation](https://fastapi.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
