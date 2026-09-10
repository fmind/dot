# Django Bootstrap

Use this only for a new Django application. Preserve an existing project's layout and dependency choices unless the user requested a migration.

## Decide Before Scaffolding

- Define the repository slug, description, first cohesive domain app, and deployment boundary.
- Select the latest stable Django series from the official download page and a supported stable Python version; let `uv.lock` pin the patch release and exclude development, alpha, beta, and release-candidate builds.
- Choose the database from expected production behavior. SQLite is the smallest local or prototype default; use PostgreSQL in development and CI too when PostgreSQL semantics, concurrency, or extensions matter.
- Decide whether authentication will remain Django's built-in shape. If user identity is likely to evolve, create a minimal `AbstractUser` subclass and set `AUTH_USER_MODEL` before the first migration.
- Default to Django templates, forms, and admin. Add an API, background-task backend, cache, object storage, or frontend toolchain only when a concrete use case needs it.

## Create the Baseline

Start from Django itself rather than a third-party project template. Replace the version placeholders with the supported series verified in this session.

```bash
uv init --app --no-package --vcs none --python <supported-python-major.minor> --description "<description>" <slug>
cd <slug>
uv add "Django>=<stable-major.minor>,<next-major.minor>"
uv add --dev pytest pytest-cov pytest-django ruff ty validate-pyproject
uv run django-admin startproject config .
uv run python manage.py startapp <domain>
```

Remove uv's placeholder `main.py` after Django creates `manage.py`; replace each generated `<domain>/tests.py` with a `tests/` package containing `test_*.py` modules because pytest does not collect `tests.py` by default. Remove the generated placeholder comments and unused imports, run `uv run ruff check --fix .` followed by `uv run ruff format .`, and review the fixes.

Keep `config/` limited to settings, root URLs, and WSGI/ASGI entry points. Put behavior in cohesive domain apps, not a generic `core`, `utils`, or premature service hierarchy.

Adapt the shared [Python manifest](../../python-stack/references/pyproject.toml.template) and [mise tasks](../../python-stack/references/mise.toml): set `[tool.uv] package = false`, keep only Django application dependencies and remove package build metadata, add Ruff's `DJ` rules, set `DJANGO_SETTINGS_MODULE = "config.settings"` for pytest, and keep warnings as errors. Add `pytest-django` database markers only to tests that access the database.

## Harden the Generated Project

- Keep one settings module until environments genuinely differ. Read a few settings with the standard library; add a settings dependency only when validation or URL parsing earns it.
- Default `DEBUG` to false, require the production `SECRET_KEY`, parse `ALLOWED_HOSTS` explicitly, and keep local values in an ignored `.env` with names documented in `.env.example`.
- Configure `STATIC_ROOT` for `collectstatic`; treat uploaded media as untrusted and keep it outside the application image and static-file path.
- Configure HTTPS, secure cookies, trusted origins, forwarding headers, email, and proxy trust from the actual deployment topology. Never copy proxy settings between providers without verifying the trust boundary.
- Keep database constraints close to models, wrap multi-write invariants in `transaction.atomic()`, use `select_related()` or `prefetch_related()` for proven query fan-out, and inspect query counts in regression tests.
- Prefer explicit calls over signals for business workflows. Use signals only when the sender must not know the receiver and test registration, transaction timing, and idempotency.

## Canonical Tasks

Reuse the shared format, leak, lint, type, vulnerability, and test tasks. Add these Django checks to `mise run check` and pass production-like environment values to the deployment check without storing real secrets:

```bash
uv run python manage.py check --fail-level WARNING
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check --deploy --fail-level WARNING
```

Use `uv run python manage.py runserver` only for the `watch` development task. Make `build` produce the real deployment artifact—usually collected static files and an OCI image—rather than a wheel for a non-package application.

## Acceptance

- A clean checkout can install, migrate, run, test, and build using documented mise tasks.
- Tests are actually collected and cover one useful request path, validation failure, authorization boundary, model constraint, and custom-user behavior when selected.
- `mise run format`, `mise run check`, and `mise run test` pass without warnings; `makemigrations --check --dry-run` is empty and `check --deploy` is evaluated with production-like settings.
- `.env.example`, README, and AGENTS.md describe names and commands without secrets; deployment, publication, and live migrations remain separately authorized actions.
