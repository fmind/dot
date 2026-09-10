---
name: wagtail
description: Build Django content sites with Wagtail. Use for page models, StreamField blocks, editor workflows, previews, and publishing permissions.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/wagtail
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Wagtail

Use Wagtail for an editor-managed CMS; [django](../django/SKILL.md) owns shared Django setup and deployment.

## Workflow

1. Inspect the project's Wagtail, Django, and Python compatibility before adding `wagtail` with `uv add wagtail`; keep an existing site's apps and migrations.
1. For a new site, run `uv run wagtail start <site-name>` into a new directory, then follow its generated dependency instructions. Run `uv run python manage.py migrate` against the development database and `uv run python manage.py check`.
1. Model content with `Page` subclasses, explicit editor panels, and reusable StreamField blocks. Set parent/child constraints and template paths before creating sample pages.
1. Create schema migrations with `uv run python manage.py makemigrations`; changing stored block shapes also needs a content migration and recovery rehearsal through [data-migration](../data-migration/SKILL.md).
1. Test draft preview, publish/unpublish, page routing, search, and editor permissions with Django tests and Wagtail's testing helpers. Check keyboard editing and a real rendered page before delivery.

## Gotchas

- A public page query must respect publication and permissions; use the appropriate live/public filters and test restricted descendants.
- Avoid N+1 queries for specific page types, related images, and renditions; measure the rendered page's query count.
- Rich text and media need Wagtail's rendering helpers; do not bypass sanitization or expose the development media server in production.

## Official Skills

No consumer Agent Skill was found in the inspected [wagtail/wagtail](https://github.com/wagtail/wagtail) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Tutorial](https://docs.wagtail.org/en/stable/getting_started/tutorial.html) · [Testing](https://docs.wagtail.org/en/stable/advanced_topics/testing.html) · [StreamField](https://docs.wagtail.org/en/stable/topics/streamfield.html)
