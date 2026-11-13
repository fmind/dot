---
name: pydantic
description: "Typed validation, serialization, and settings boundaries."
---

# Pydantic

Typed validation, serialization, and settings boundaries; [foundation](foundation/GUIDE.md) owns project defaults.

## Workflow

1. **Check locked version & config**: add `pydantic` via `uv add pydantic` only when needed; consult installed `pydantic` skill or `.venv/` source.
1. **Encode constraints in types**: use `BaseModel` for objects and `TypeAdapter` for arbitrary annotated types, preferring type constraints (`Annotated`, `Field`) over custom validators.
1. **Fail-closed settings**: use `pydantic-settings` `BaseSettings` (`SecretStr` for secrets, no defaults on required secrets, and redacted validation output). Add `env_prefix` only when platform/starter contracts permit (Cloud Run sets `PORT`; [Litestar bootstrap](../../python-web/references/litestar/references/bootstrap.md) reads unprefixed `DATABASE_URL`, `HOST`, `ENVIRONMENT`). Prefer platform env injection ([cloud-run](../../cloud-run/SKILL.md) pins Secret Manager versions) over `GoogleSecretManagerSettingsSource` (which lists all project secrets and defaults to `latest`).

## Gotchas & Upstream Skill

- **Env var typos are silent**: `extra="forbid"` catches unknown init/dotenv keys, not misspelled OS env vars (`APP_TIMEOUTT` silently keeps the default) — test exact env names.
- **Omit `pydantic.dev` tracking query params**: never append `intent`/`stack`/`harness` from `llms.txt` (leaks task context).
- **Select only `pydantic`** from [pydantic/skills](https://github.com/pydantic/skills) per [vendor-skills](../../agent-project/references/vendor-skills.md) (skip Pydantic AI and Logfire — [observability](observability.md)).
- Docs: [Pydantic](https://pydantic.dev/docs/validation/latest/) · [Releases](https://github.com/pydantic/pydantic/releases) ([history](https://github.com/pydantic/pydantic/blob/main/HISTORY.md)).
