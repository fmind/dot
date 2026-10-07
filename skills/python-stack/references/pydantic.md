---
name: pydantic
description: "Typed validation, serialization, and settings boundaries."
---

# Pydantic

Use Pydantic for typed input boundaries and serialization; use [foundation](foundation/GUIDE.md) for shared project defaults and the selected application skill for scaffolding.

## Workflow

1. **Inspect version and model configuration**: check the locked Pydantic version and existing model configuration; add `pydantic` with `uv add pydantic` only when missing.
1. **Express constraints in types**: use the upstream `pydantic` skill if the project installed it, otherwise the installed package source. Use `BaseModel` for structured objects and `TypeAdapter` for other annotated types; express constraints in types before writing custom validators.
1. **Handle settings separately**: for environment configuration, inspect `pydantic-settings` separately; install it only when needed and keep secrets out of validation output.

## Gotchas

- **Pydantic AI and Logfire are separate products**: both ship in the same bundle. Choose their skills only for agent or telemetry work; [observability](../../observability/SKILL.md) owns the latter.

## Official Skills

Upstream: [pydantic/skills](https://github.com/pydantic/skills), selection `pydantic`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md); this shares a name with the local skill, so compare ownership before installation or replacement.

## Documentation

- [Pydantic documentation](https://pydantic.dev/docs/validation/latest/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Pydantic](https://github.com/pydantic/pydantic/releases) · [history](https://github.com/pydantic/pydantic/blob/main/HISTORY.md)
