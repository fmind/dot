---
name: python-web
description: "Build Python web apps/APIs with Django, Litestar, FastAPI, Gradio, or NiceGUI."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-web
  created: "2026-09-16"
  updated: "2026-10-31"
---

# Python Web Applications

Build the requested application in its existing framework. For new ordinary APIs use Litestar; choose Django for integrated ORM/admin/auth, or Gradio/NiceGUI for an appropriate Python interface. Keep browser UIs Google-simple and styled with `~/.agents/DESIGN.md` per [web-frontend](../web-frontend/SKILL.md) unless the project or customer defines its own design: one primary job per view, sensible defaults, progressive disclosure for secondary controls, and no unrequested chrome.

## Workflow

Read only the matching guide and its required resources.

## Task guides

<!-- guides:start -->

- [django](references/django/GUIDE.md): Django applications, ORM, admin, authentication, and native testing.
- [fastapi](references/fastapi.md): Existing or explicitly chosen FastAPI services and generated agent scaffolds.
- [gradio](references/gradio.md): Gradio model demos and interactive interfaces.
- [litestar](references/litestar/GUIDE.md): Litestar ASGI applications, request boundaries, and scaffolding.
- [nicegui](references/nicegui.md): NiceGUI dashboards and general browser interfaces.

<!-- guides:end -->
