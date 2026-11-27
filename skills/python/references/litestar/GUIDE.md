---
name: litestar
description: "Build Litestar ASGI applications, request/header boundaries, HTMX/SSE streaming, and scaffolding."
---

# Litestar

Default framework for Python web apps and APIs, paired with [foundation](../foundation/GUIDE.md) quality defaults.

## Workflow

1. **Bootstrap**: follow [bootstrap](references/bootstrap.md) (templates, settings, tests) on top of the Python foundation, adding DB integration only when needed.
1. **Inspect via CLI & lock OpenAPI contract (opt-in)**: run `uv run --locked litestar --app <package>:create_default_app info|routes|schema openapi` (needs no server or extra; pass `--app` explicitly with `.env` / `DATABASE_URL` present since `src/<package>/__init__.py` is not autodiscovered). For APIs where external clients or human reviewers track surface changes, check in `openapi.json` (exported from `app.openapi_schema.to_schema()`) and assert exact equality in an offline pytest test so every route, DTO, and status-code change surfaces in PR diffs.
1. **Use installed references**: consult `litestar` (routing, DI, DTO/OpenAPI, auth, middleware), `litestar-htmx`, and `litestar-testing` when installed, else read `.venv/` source and docs.
1. **Styles**: preserve existing pipelines or compile standalone Tailwind per [tailwind](../../../web-frontend/references/tailwind.md).

## Gotchas

- **Keep Pydantic; avoid redundant direct deps**: Litestar ships `msgspec` and `polyfactory` transitively — declare them only if imported directly, and use `msgspec.Struct` only on measured hot paths.
- **Explicit handler markers (`2.22–2.25`, required in `3.0`)**: inferred params/DI/bodies emit `LitestarDeprecationWarning` (failing `filterwarnings = ["error"]`). Annotate `FromPath[T]`, `FromQuery[T]`, `FromHeader[T]`, `FromCookie[T]` (`litestar.params`), `NamedDependency[T]` (`litestar.di`), explicit body markers (`JSONBody[T]`, `URLEncodedBody[T]`, `MultipartBody[T]`, `RawBody`), and reserved args (`Request`, `Headers`, `QueryParams`, `RequestCookies`). Form validation returns JSON `400` by default; re-render HTML errors inside the handler or via a route/controller HTML exception handler.
- **HTMX partials**: store fragments in `templates/partials/<feature>-<part>.html`, `{% include %}` in pages, and return via `HTMXTemplate` (`litestar.plugins.htmx`; wrap main + `hx-swap-oob="true"` fragments in one partial). Import macros `with context` from macros-only files (else `url_for`/`csrf_token()`/`csrf_input` fail or page bodies execute); avoid `jinja2-fragments` (breaks top-level `{% set %}`, imports, `scoped` loops, and `super()`).
- **SSE & LLM streaming**: return `ServerSentEvent` yielding `ServerSentEventMessage` (`litestar.response.sse`), propagate `asyncio.CancelledError` in the async generator's `finally` block to cancel upstream model streams on client disconnect, and enforce hard token/time bounds.
- **Wire boundaries & headers**: emit RFC 9457 `application/problem+json` on errors ([api-design](../api-design.md)), attach baseline security headers via `ASGIMiddleware` (not `after_request` closures, which Litestar caches on module-level route handlers across `create_app()` calls), bound payloads via `request_max_body_size`, and enforce `RateLimitConfig` or gateway rate limits ([security-and-auth](../security-and-auth.md)).
- **Static & SSR**: serve content-hashed assets via `create_static_files_router(..., cache_control=CacheControlHeader(max_age=31_536_000, immutable=True, public=True))` + standalone [tailwind](../../../web-frontend/references/tailwind.md) with vendored assets (no CDN). Import `HTMXPlugin`/`HTMXRequest` (`litestar.plugins.htmx`) and `JinjaTemplateEngine` (`litestar.plugins.jinja`; `litestar.contrib.jinja` is removed in `3.0`); skip Node-bound `litestar-vite`/`litestar-inertia`. Configure `TemplateConfig(instance=JinjaTemplateEngine.from_environment(Environment(loader=..., autoescape=True, undefined=StrictUndefined)))`, render `{{ csrf_input | safe }}` (plain string), and link assets via `url_for("static", file_path=...)` (`url_for_static_asset` is deprecated).

## Official Skills & Docs

Upstream: [litestar-org/litestar-skills](https://github.com/litestar-org/litestar-skills) (install `litestar` + needed extras per [vendor-skills](../../../agent-harnesses/references/vendor-skills.md#workflow)). Docs: [Litestar](https://docs.litestar.dev/latest/) · [release notes](https://docs.litestar.dev/latest/release-notes/) · [GitHub releases](https://github.com/litestar-org/litestar/releases).
