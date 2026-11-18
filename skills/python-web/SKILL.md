---
name: python-web
description: "Build Python web apps/APIs with Django, Litestar, FastAPI, Gradio, or NiceGUI."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-web
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Python Web Applications

Keep an existing project's framework. Default to Litestar for new APIs/services, Django for integrated ORM/admin/auth, or `python-ui` (Gradio/NiceGUI) for Python UIs. Browser UIs follow [web-frontend](../web-frontend/SKILL.md) and live Chrome verification across desktop/mobile viewports and empty/loading/error/populated states ([chrome-devtools](../chrome-devtools/SKILL.md)). Load the matching framework, [security-and-auth](references/security-and-auth.md), and [database-and-jobs](references/database-and-jobs.md) guides as needed, and audit non-trivial changes with `fmind-review-api`, `fmind-review-web`, `fmind-review-design`, and `fmind-review-security` ([subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [database-and-jobs](references/database-and-jobs.md): Configure async Postgres/SQLite pools, Alembic migrations, object storage, pgqueuer, and Cloud Tasks workers.
- [django](references/django/GUIDE.md): Django applications, ORM, admin, authentication, and native testing.
- [fastapi](references/fastapi.md): Existing or explicitly chosen FastAPI services and generated agent scaffolds.
- [litestar](references/litestar/GUIDE.md): Litestar ASGI applications, request boundaries, and scaffolding.
- [python-ui](references/python-ui.md): Build Gradio model demos and NiceGUI dashboards or browser utilities.
- [security-and-auth](references/security-and-auth.md): Implement OIDC/OAuth2 login, JWT validation, Argon2id hashing, webhook HMAC checks, CSRF cookies, and security headers.

<!-- guides:end -->

## Documentation

- [Litestar](https://docs.litestar.dev/latest/) · [Django](https://docs.djangoproject.com/en/stable/) · [FastAPI](https://fastapi.tiangolo.com/) · [Granian](https://github.com/emmett-framework/granian) · [Gradio](https://gradio.app/docs) · [NiceGUI](https://nicegui.io/documentation) · [SQLAlchemy](https://docs.sqlalchemy.org/en/20/) · [Psycopg 3](https://www.psycopg.org/psycopg3/docs/) · [pgqueuer](https://janbjorge.github.io/pgqueuer/) · [obstore](https://developmentseed.org/obstore/latest/)
- Companions: [python-stack](../python-stack/SKILL.md), [web-frontend](../web-frontend/SKILL.md), [chrome-devtools](../chrome-devtools/SKILL.md), [playwright](../playwright/SKILL.md), [cloud-run](../cloud-run/SKILL.md), [code-security](../code-security/SKILL.md).
