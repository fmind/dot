---
name: pydantic
description: Validate and serialize Python data with Pydantic and its official skills. Use when designing models, constraints, validators, or settings boundaries.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/pydantic
  created: "2026-09-06"
  updated: "2026-09-11"
---

# Pydantic

Use Pydantic for typed input boundaries and serialization; use [python-stack](../python-stack/SKILL.md) for shared project defaults and the selected application skill for scaffolding.

## Workflow

1. Inspect the locked Pydantic version and existing model configuration; add `pydantic` with `uv add pydantic` only when missing.
1. Select the upstream `pydantic` skill. Use `BaseModel` for structured objects and `TypeAdapter` for other annotated types; express constraints in types before writing custom validators.
1. Choose coercion versus strict validation and the policy for unknown fields explicitly. Use `model_validate` or `model_validate_json` at ingestion and `model_dump` or `model_dump_json` for output; Python and JSON representations can differ.
1. Test accepted values, rejected input, nested errors, aliases, defaults, and serialization with [Python testing](../test-driven-development/SKILL.md). Check validators' ordering and error behavior against the locked API.
1. For environment configuration, inspect `pydantic-settings` separately; install it only when needed and keep secrets out of validation output.

## Gotchas

- Pydantic AI and Logfire are separate products in the same bundle. Choose their skills only for agent or telemetry work; [observability](../observability/SKILL.md) owns the latter.
- Read the installed version before copying upstream examples; a skill fetched from the default branch can target newer APIs.

## Official Skills

Upstream: [pydantic/skills](https://github.com/pydantic/skills), selection `pydantic`. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md); this shares a name with the local skill, so compare ownership before installation or replacement.

## Documentation

- [Pydantic documentation](https://docs.pydantic.dev/latest/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Pydantic](https://github.com/pydantic/pydantic/releases) · [history](https://github.com/pydantic/pydantic/blob/main/HISTORY.md)
