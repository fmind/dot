---
name: django
description: Bootstrap and maintain production-minded Django applications with a small typed Python stack. Use for Django projects, apps, models, views, admin, settings, migrations, or tests.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/django
  created: "2026-09-07"
  updated: "2026-09-11"
---

# Django

Use Django when its integrated ORM, migrations, forms, templates, authentication, and admin reduce the total system; [python-stack](../python-stack/SKILL.md) owns non-Django Python packages, CLIs, and Litestar services.

## Workflow

1. **Establish the framework contract**: inspect the installed Django version, settings, URL configuration, apps, migrations, database, and deployment target before editing; for a new application, read [bootstrap](references/bootstrap.md).
1. **Model the domain first**: keep apps cohesive, encode invariants with fields, constraints, forms, and transactions, and decide whether a custom user model is needed before the first migration.
1. **Prefer Django's integrated path**: start with server-rendered templates, forms, authentication, and admin; add an API framework, task backend, cache, or JavaScript layer only for a demonstrated requirement.
1. **Keep control flow visible**: use thin views and explicit functions for multi-step use cases; avoid signals, custom middleware, managers, or repository/service layers when ordinary Django code is clearer.
1. **Choose sync deliberately**: default to synchronous request and transaction code; use async only for measured concurrent I/O and verify the ASGI, middleware, ORM, connection-pooling, and transaction boundaries end to end.
1. **Treat schema changes as code**: review generated migrations, preserve applied migration history, test data migrations in both directions when reversible, and never infer production schema state from models alone.
1. **Verify the behavior**: run focused model, form, permission, view, and template tests, then the project gate; include Django system, deployment, and migration-drift checks.

```bash
uv run python manage.py check --fail-level WARNING
uv run python manage.py makemigrations --check --dry-run
uv run pytest
mise run check
mise run test
```

## Gotchas

- **Generated settings are development-only**: move secrets and environment-specific values to validated inputs, default `DEBUG` off, and run `check --deploy` against production-like settings.
- **User models are an early boundary**: changing `AUTH_USER_MODEL` after tables exist is complex; make the decision before the first `migrate` and reference users through `settings.AUTH_USER_MODEL` or `get_user_model()`.
- **Async is not a blanket optimization**: transactions still do not work in async mode, so keep transactional work in a synchronous function called through `sync_to_async()`; disable `CONN_MAX_AGE` under ASGI in favor of the database backend's own pooling, and never set `DJANGO_ALLOW_ASYNC_UNSAFE` to bypass the safety check.
- **Django needs stubs to type-check**: add `django-stubs` as a dev dependency or `ty` reports `unresolved-attribute` on `Model.objects`; it reads PEP 561 stubs only, so declare reverse accessors under `if TYPE_CHECKING:` as `comments: RelatedManager[Comment]` rather than suppressing the diagnostic.
- **`runserver` is not production**: choose and test a production WSGI or ASGI server only after the deployment target and concurrency model are known.

## Documentation

- [Django documentation](https://docs.djangoproject.com/en/stable/) · [supported releases](https://www.djangoproject.com/download/) · [deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/) · [security](https://docs.djangoproject.com/en/stable/topics/security/) · [async support](https://docs.djangoproject.com/en/stable/topics/async/)
- Companion skills: [new-project](../new-project/SKILL.md) (repository-wide scaffold), [python-stack](../python-stack/SKILL.md) (uv and quality defaults), [containerize](../containerize/SKILL.md) (OCI image), [cloud-run](../cloud-run/SKILL.md) (deployment), and [secure](../secure/SKILL.md) (security pass).
