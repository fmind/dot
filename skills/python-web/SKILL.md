---
name: python-web
description: "Build Python web apps/APIs with Django, Litestar, FastAPI, Gradio, or NiceGUI."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-web
  created: "2026-09-16"
  updated: "2026-11-16"
---

# Python Web Applications

Keep an existing project's framework. Default to Litestar for new APIs/services, Django for integrated ORM/admin/auth, or `python-ui` (Gradio/NiceGUI) for Python UIs. Browser UIs follow [web-frontend](../web-frontend/SKILL.md) and live Chrome verification ([chrome-devtools](../chrome-devtools/SKILL.md)). Read only the matching guide and its required resources.

## Task guides

<!-- guides:start -->

- [database-and-jobs](references/database-and-jobs.md): Configure async Alembic migrations, connection pools, SQLite WAL, pgqueuer, and Cloud Tasks workers.
- [django](references/django/GUIDE.md): Django applications, ORM, admin, authentication, and native testing.
- [fastapi](references/fastapi.md): Existing or explicitly chosen FastAPI services and generated agent scaffolds.
- [litestar](references/litestar/GUIDE.md): Litestar ASGI applications, request boundaries, and scaffolding.
- [python-ui](references/python-ui.md): Build Gradio model demos and NiceGUI dashboards or browser utilities.
- [security-and-auth](references/security-and-auth.md): Implement OIDC/JWT validation, webhook HMAC checks, Litestar CSRF/session cookies, and HTTP security headers.

<!-- guides:end -->
