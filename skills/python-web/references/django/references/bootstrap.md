# Django Bootstrap

Use this only for a new Django application. Preserve an existing project's layout and dependency choices unless the user requested a migration.

## Decide Before Scaffolding

- **Name the project and its boundaries**: define the repository slug, description, first cohesive domain app, and deployment boundary.
- **Target a supported stable release**: select the latest stable Django series from the official download page, or the current LTS when the upgrade cadence is constrained, and a supported stable Python version; let `uv.lock` pin the patch release and exclude development, alpha, beta, and release-candidate builds.
- **Match recipes to the selected series**: built-in CSP, template partials, and tasks require Django 6.0+; `MAILERS`, fetch modes, and the cited mail/CSP checks require 6.1+. On an older supported LTS, use that version's documented equivalents rather than importing newer APIs.
- **Match the database to production**: choose the database from expected production behavior. SQLite is the smallest local or prototype default; use PostgreSQL in development and CI too when PostgreSQL semantics, concurrency, or extensions matter.
- **Settle the user model before migrating**: decide whether authentication will remain Django's built-in shape. If user identity is likely to evolve, create a minimal `AbstractUser` subclass and set `AUTH_USER_MODEL` before the first migration.
- **Default to Django templates, forms, and admin**: add an API, background-task backend, cache, object storage, or frontend toolchain only when a concrete use case needs it.
- **Reject third-party packages Django 6 replaced**: core ships `SECURE_CSP` over `django-csp`, `{% partialdef %}` over `django-template-partials`, and `django.tasks` over `django-tasks`. The built-in task backends are development-only, so select a real backend such as `django-tasks-db` before shipping queued work.
- **Prefer these packages once earned**: when a package earns its place, default to `whitenoise` for `collectstatic` output with its middleware directly after `SecurityMiddleware`, `granian --interface wsgi` in production, `model-bakery` once fixtures repeat, and `django-debug-toolbar` in development settings only. Compile CSS with the mise-pinned standalone `tailwindcss` binary; no Node.js toolchain, no CDN. Packages used only as commands or settings strings (`granian`, `whitenoise`) go in deptry's `[tool.deptry.per_rule_ignores]` `DEP002` list.

## Create the Baseline

Start from Django itself rather than a third-party project template. Replace the version placeholders with the supported series verified in this session.

```bash
uv init --app --no-package --vcs none --python <supported-python-major.minor> --description "<description>" <slug>
cd <slug>
uv add "Django~=<stable-major.minor>.0"
uv add --dev pytest pytest-cov pytest-django django-stubs ruff ty validate-pyproject
uv run django-admin startproject config .
uv run python manage.py startapp <domain>
```

Remove uv's placeholder `main.py` after Django creates `manage.py`; replace each generated `<domain>/tests.py` with a `tests/` package containing `test_*.py` modules because pytest does not collect `tests.py` by default. Remove the generated placeholder comments and unused imports, run `uv run ruff check --fix .` followed by `uv run ruff format .`, and review the fixes.

Keep `config/` limited to settings, root URLs, and WSGI/ASGI entry points. Put behavior in cohesive domain apps, not a generic `core`, `utils`, or premature service hierarchy.

Adapt the shared [Python manifest](../../../../python-stack/references/foundation/templates/pyproject.toml.template) and [mise tasks](../../../../python-stack/references/foundation/templates/mise.toml): set `[tool.uv] package = false`, keep only Django application dependencies and remove package build metadata, add Ruff's `DJ` rules, set `DJANGO_SETTINGS_MODULE = "config.settings"` for pytest, and keep warnings as errors. Add `pytest-django` database markers only to tests that access the database. The template assumes a `src/` package with top-level tests, so point `testpaths` and `[tool.coverage.run] source` at the app packages, widen the per-file-ignores key to `"**/tests/**"`, and add `[tool.deptry] extend_exclude = [".*/tests/"]` because deptry skips only a top-level `tests/`; otherwise `filterwarnings = ["error"]` turns pytest's empty-`testpaths` warning into a failure, coverage collects nothing against `fail_under`, and `S101` fires on every test assertion.

## Harden the Generated Project

- **Keep settings minimal**: keep one settings module until environments genuinely differ. Read a few settings with the standard library; add a settings dependency only when validation or URL parsing earns it.
- **Harden secrets and debug defaults**: default `DEBUG` to false, require the production `SECRET_KEY`, parse `ALLOWED_HOSTS` explicitly, and keep local values in an ignored `.env` with names documented in `.env.example`.
- **Separate static files from untrusted media**: configure `STATIC_ROOT` for `collectstatic`; treat uploaded media as untrusted and keep it outside the application image and static-file path.
- **Derive security settings from deployment topology**: configure HTTPS, secure cookies, trusted origins, forwarding headers, `MAILERS`, and proxy trust from the actual deployment topology; the generated console mail backend fails `check --deploy` with `mail.E001`, and the legacy `EMAIL_*` settings are deprecated. Never copy proxy settings between providers without verifying the trust boundary.
- **Take Django's own fail-closed defaults first**: before any third party, add `LoginRequiredMiddleware` and mark public views `@login_not_required`; set `SECURE_CSP` from `django.utils.csp.CSP` with `ContentSecurityPolicyMiddleware`, and add `django.template.context_processors.csp` to a template backend whenever the policy uses `CSP.NONCE`, or `check` raises `security.W027`.
- **Enforce invariants and explicit fetching**: keep database constraints close to models, wrap multi-write invariants in `transaction.atomic()`, and name the relations you traverse in `select_related()` or `prefetch_related()` or batch them with `QuerySet.fetch_mode(models.FETCH_PEERS)` because the no-argument `select_related()` is deprecated. In regression tests use `models.FETCH_RAISE` so an unintended query raises `FieldFetchBlocked` at its call site instead of a query count you must maintain.
- **Avoid signals for business workflows**: prefer explicit calls. Use signals only when the sender must not know the receiver and test registration, transaction timing, and idempotency.

## Canonical Tasks

Reuse the shared format, leak, lint, type, vulnerability, and test tasks. Add these Django checks to `mise run check` and pass production-like environment values to the deployment check without storing real secrets:

```bash
uv run python manage.py check --fail-level WARNING
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py check --deploy --fail-level WARNING
```

Use `uv run python manage.py runserver` only for the `watch` development task. Make `build` produce the real deployment artifact—usually collected static files and an OCI image—rather than a wheel for a non-package application.

## Acceptance

- **A clean checkout works end to end**: a clean checkout can install, migrate, run, test, and build using documented mise tasks.
- **Tests run and cover key paths**: tests are actually collected and cover one useful request path, validation failure, authorization boundary, model constraint, and custom-user behavior when selected.
- **Gates pass without warnings**: `mise run format`, `mise run check`, and `mise run test` pass without warnings; `makemigrations --check --dry-run` is empty and `check --deploy` is evaluated with production-like settings.
- **Keep docs secret-free and deploys authorized**: `.env.example`, README, and AGENTS.md describe names and commands without secrets; deployment, publication, and live migrations remain separately authorized actions.
