---
name: django
description: "Django applications, ORM, admin, authentication, and native testing."
---

# Django

Choose Django when integrated ORM, migrations, forms, templates, auth, and admin shrink the total system; [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns general packages, [argparse](../../../python-stack/references/argparse/GUIDE.md) owns CLIs, and [Litestar](../litestar/GUIDE.md) owns async services.

## Workflow

1. **Inspect the contract**: check installed Django version, settings, URLs, apps, migrations, database, and deploy target before editing; read [bootstrap](references/bootstrap.md) for new apps.
1. **Build styles deliberately**: keep existing asset pipelines; for standalone Tailwind follow [tailwind](../../../web-frontend/references/tailwind.md) and compile CSS before `collectstatic` (no CDN).
1. **Keep Django plain and sync**: thin views and functions; add signals, custom middleware, managers, service layers, or async views only with measured need.
1. **Serve with Granian**: run `granian --interface wsgi --host 0.0.0.0 --port "${PORT:-8080}" config.wsgi:application` (never gunicorn). Granian defaults to `127.0.0.1:8000` and ignores Cloud Run's `PORT` unless passed or set via `GRANIAN_HOST`/`GRANIAN_PORT`; it drains in-flight requests on `SIGTERM` (verified on Granian 2.8.7 + Django 6).
1. **Verify**:

```bash
uv run python manage.py check --fail-level WARNING
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q <focused-test-path>
mise run check && mise run test
```

## Gotchas

- **Async transactions**: ORM transactions remain sync-only — wrap transactional work in `sync_to_async()`, disable `CONN_MAX_AGE` under ASGI in favor of DB backend pooling, and never set `DJANGO_ALLOW_ASYNC_UNSAFE`.
- **`django-stubs` + `ty`**: add `django-stubs` (`dev`) so `Model.objects` resolves; declare reverse relations under `if TYPE_CHECKING:` (`from django.db.models.fields.related_descriptors import RelatedManager` -> `comments: RelatedManager[Comment]`) instead of suppressing diagnostics.

## Documentation

- [Django docs](https://docs.djangoproject.com/en/stable/) · [releases](https://docs.djangoproject.com/en/stable/releases/) · Companions: [project-scaffolding](../../../project-scaffolding/references/bootstrap.md), [python-stack](../../../python-stack/references/foundation/GUIDE.md), [containerize](../../../docker/references/containerize/GUIDE.md), [cloud-run](../../../cloud-run/SKILL.md), [code-security](../../../code-security/references/code-review/GUIDE.md).
