---
name: pydantic
description: Validate and serialize Python data with Pydantic and its official skills. Use when designing models, constraints, validators, or settings boundaries.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/pydantic
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Pydantic

Use Pydantic for typed input boundaries and serialization; keep application scaffolding in [python-stack](../python-stack/SKILL.md).

## Workflow

1. Inspect the locked Pydantic version and existing model configuration; add `pydantic` with `uv add pydantic` only when missing.
1. Select the upstream data-validation guidance. Express field constraints in types and test coercion, rejected input, serialization, and error behavior at the boundary.
1. For environment configuration, inspect `pydantic-settings` separately; install it only when needed and keep secrets out of validation output.

## Gotchas

- Pydantic AI and Logfire are separate products in the same bundle. Choose their skills only for agent or telemetry work; [observability](../observability/SKILL.md) owns the latter.
- Read the installed version before copying upstream examples; a skill fetched from the default branch can target newer APIs.

## Official Skills

Upstream: [pydantic/skills](https://github.com/pydantic/skills). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the relevant validation or serialization guidance.

## Documentation

- [Pydantic documentation](https://docs.pydantic.dev/latest/) · [Skills CLI](https://skills.sh/docs/cli)
