---
name: django
description: "Django applications, ORM, admin, authentication, and native testing."
---

# Django

Use Django when its integrated ORM, migrations, forms, templates, authentication, and admin reduce the total system; [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns non-Django Python packages, [typer](../../../python-stack/references/typer/GUIDE.md) owns CLIs, and the [Litestar guide](../litestar/GUIDE.md) owns async services.

## Workflow

1. **Establish the framework contract**: inspect the installed Django version, settings, URL configuration, apps, migrations, database, and deployment target before editing; for a new application, read [bootstrap](references/bootstrap.md).
1. **Build template styles deliberately**: keep an existing asset pipeline; for standalone Tailwind, follow [web-frontend's standalone Tailwind workflow](../../../web-frontend/references/tailwind.md) and build CSS before `collectstatic`; no CDN.
1. **Keep Django plain and synchronous**: thin views and explicit functions; no signals, custom middleware, managers, service layers, or async views without a measured need.
1. **Serve production with granian**: run `granian --interface wsgi --host 0.0.0.0 --port "${PORT:-8080}" config.wsgi:application`, never gunicorn. Granian binds `127.0.0.1:8000` by default and ignores Cloud Run's `PORT`, so pass both (or set `GRANIAN_HOST` and `GRANIAN_PORT`). Cloud Run already fronts requests, and granian drains in-flight requests on `SIGTERM` before exiting (verified with granian 2.8.7 and Django 6).
1. **Verify the behavior**: run focused tests, then the project gate, including Django system, deployment, and migration-drift checks.

```bash
uv run python manage.py check --fail-level WARNING
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q <focused-test-path>
mise run check
mise run test
```

## Gotchas

- **Async is not a blanket optimization**: transactions still do not work in async mode, so keep transactional work in a synchronous function called through `sync_to_async()`; disable `CONN_MAX_AGE` under ASGI in favor of the database backend's own pooling, and never set `DJANGO_ALLOW_ASYNC_UNSAFE` to bypass the safety check.
- **Django needs stubs to type-check**: add `django-stubs` as a dev dependency or `ty` reports `unresolved-attribute` on `Model.objects`; it reads PEP 561 stubs only, so declare reverse accessors under `if TYPE_CHECKING:` as `comments: RelatedManager[Comment]`, importing the stub-only `RelatedManager` from `django.db.models.fields.related_descriptors` under the same guard, rather than suppressing the diagnostic.

## Documentation

- [Django documentation](https://docs.djangoproject.com/en/stable/) · [supported releases](https://www.djangoproject.com/download/) · [deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/) · [security](https://docs.djangoproject.com/en/stable/topics/security/) · [async support](https://docs.djangoproject.com/en/stable/topics/async/)
- Releases: [Django release notes](https://docs.djangoproject.com/en/stable/releases/)
- Companion skills: [project-scaffolding](../../../project-scaffolding/references/bootstrap.md) (repository-wide scaffold), [python-stack](../../../python-stack/references/foundation/GUIDE.md) (uv and quality defaults), [containerize](../../../docker/references/containerize/GUIDE.md) (OCI image), [cloud-run](../../../cloud-run/SKILL.md) (deployment), and [code-security](../../../code-security/references/code-review/GUIDE.md) (security pass).
