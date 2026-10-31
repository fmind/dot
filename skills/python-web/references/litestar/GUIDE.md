---
name: litestar
description: "Litestar ASGI applications, request boundaries, and scaffolding."
---

# Litestar

Use Litestar for Python web applications, with [python-stack](../../../python-stack/references/foundation/GUIDE.md) supplying the project and quality defaults.

## Workflow

1. **Bootstrap after the Python foundation**: for a new service, follow [bootstrap](references/bootstrap.md) after the shared Python foundation; choose database integration only when needed.
1. **Use the Litestar CLI and source**: inspect the application with `uv run litestar --app <package>:app info`, `routes`, and `schema openapi`; these need no server and no extra, and autodiscovery does not find `src/<package>/__init__.py`. Read the source for the application factory, dependencies, and test client setup.
1. **Follow the upstream feature references**: when the project installed them, consult the upstream `litestar` references for the actual feature (routing, dependency injection, DTO/OpenAPI, authentication, middleware), `litestar-htmx` for templates and HTMX, and `litestar-testing` for tests; otherwise read the installed package source and current docs.
1. **Keep the existing template asset pipeline** for template styles; [web-frontend's standalone Tailwind workflow](../../../web-frontend/references/tailwind.md) covers Python templates, class discovery, and production CSS builds.

## Application resources

- [init.py](templates/init.py) and [env.example](templates/env.example) provide the database-backed application and example settings.
- [test_web.py](templates/test_web.py) covers offline health, readiness failures, CORS, and server wiring; [test_integration.py](templates/test_integration.py) and [conftest.py](templates/conftest.py) provide opt-in Postgres qualification.

## Gotchas

- **Keep Pydantic; declare only used packages**: the upstream bundle also documents Advanced Alchemy, SQLSpec, msgspec, and Polyfactory. Litestar already depends on msgspec and Polyfactory; declare either as a direct dependency only when application code imports it. Keep Pydantic for request, response, and settings models, which Litestar supports directly, and reach for msgspec `Struct` only in a measured hot path.
- **Declare handler inputs explicitly**: Litestar 2.22–2.25 deprecate inferred path and query parameters, implicit dependencies, and reserved arguments without their marker type; each emits `LitestarDeprecationWarning` when the app is built, which `filterwarnings = ["error"]` turns into a test failure, and 3.0 removes them. Use `FromPath[T]`, `FromQuery[T]`, `FromHeader[T]`, and `FromCookie[T]` from `litestar.params`, `NamedDependency[T]` from `litestar.di`, a body marker for `data` that matches the request encoding (a bare `data: Model` still warns): `JSONBody[T]` for JSON, `URLEncodedBody[T]` for HTML and HTMX forms, `MultipartBody[T]` for uploads (an `UploadFile` field), or `RawBody` for bytes, and `request: Request`, `headers: Headers`, `QueryParams`, or `RequestCookies` for the other reserved arguments. A form that fails validation returns a JSON 400 by default; to re-render an HTML form with its errors, validate inside the handler or register an HTML exception handler on that route or controller.
- **Render HTMX partials from files**: put each swappable fragment in `templates/partials/<feature>-<part>.html`; the page `{% include %}`s it and the handler returns it with `HTMXTemplate` from `litestar.plugins.htmx`. For out-of-band updates, return one partial that includes the main fragment and each `hx-swap-oob="true"` fragment. Use macros only for small repeated markup, from a macros-only file imported `with context`: without it `url_for`, `csrf_token()`, and `csrf_input` fail, and importing from a page template runs that page. Skip `jinja2-fragments`: rendering one block drops top-level `{% set %}` and imports, loop blocks need `scoped`, and `super()` breaks.
- **Make templates strict and forms safe**: build the engine with `TemplateConfig(instance=JinjaTemplateEngine.from_environment(Environment(loader=..., autoescape=True, undefined=StrictUndefined)))`. Write `{{ csrf_input | safe }}`: it is a plain string, so autoescaping otherwise prints the tag as text and the form posts no token. Link assets with `url_for("static", file_path=...)`; `url_for_static_asset` is deprecated.

## Official Skills

Upstream: [litestar-org/litestar-skills](https://github.com/litestar-org/litestar-skills). Follow the shared [vendor-skill policy](../../../agent-project/references/vendor-skills.md#workflow), including what a skills-only install omits, and select `litestar` (core framework, consolidated with references) and only the ecosystem skills the app uses.

## Documentation

- [Litestar documentation](https://docs.litestar.dev/latest/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Litestar release notes](https://docs.litestar.dev/latest/release-notes/) · [GitHub releases](https://github.com/litestar-org/litestar/releases)
