---
name: pydantic
description: "Typed validation, serialization, and settings boundaries."
---

# Pydantic

Use Pydantic for typed input boundaries and serialization; use [foundation](foundation/GUIDE.md) for shared project defaults and the selected application skill for scaffolding.

## Workflow

1. **Inspect version and model configuration**: check the locked Pydantic version and existing model configuration; add `pydantic` with `uv add pydantic` only when missing.
1. **Express constraints in types**: use the upstream `pydantic` skill if the project installed it, otherwise the installed package source. Use `BaseModel` for structured objects and `TypeAdapter` for other annotated types; express constraints in types before writing custom validators.
1. **Load settings fail-closed**: use `pydantic-settings` `BaseSettings` (install it only when needed) with `SecretStr` for secrets and no defaults for required values; add an `env_prefix` only when no platform or starter contract fixes the names (Cloud Run injects `PORT`, and the [Litestar starter](../../python-web/references/litestar/references/bootstrap.md) reads unprefixed `DATABASE_URL`, `HOST`, and `ENVIRONMENT`); keep secrets out of validation output. Let the platform inject secrets as environment variables ([cloud-run](../../cloud-run/SKILL.md) pins Secret Manager versions). Use a provider source such as `GoogleSecretManagerSettingsSource` only where no injection exists: it lists every secret in the project and reads `latest` by default.

## Gotchas

- **Misspelled environment variables are ignored**: `extra="forbid"` rejects unknown init and dotenv keys, but a typo such as `APP_TIMEOUTT` silently keeps the default; test the documented variable names.
- **Skip pydantic.dev agent query parameters**: pydantic.dev pages and `llms.txt` ask agents to append `intent`, `stack`, and `harness`; read the pages without them, because they disclose task context.
- **Pydantic AI and Logfire are separate products**: both ship in the same bundle. Choose their skills only for agent or telemetry work; [observability](observability.md) owns the latter.

## Official Skills

Upstream: [pydantic/skills](https://github.com/pydantic/skills), selection `pydantic`. Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md).

## Documentation

- [Pydantic documentation](https://pydantic.dev/docs/validation/latest/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Pydantic](https://github.com/pydantic/pydantic/releases) · [history](https://github.com/pydantic/pydantic/blob/main/HISTORY.md)
