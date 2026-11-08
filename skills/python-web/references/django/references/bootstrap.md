# Django Bootstrap

## Decide Before Scaffolding

- **Target a supported stable release**: select the latest stable Django series from the official download page, or the current LTS when the upgrade cadence is constrained, and a supported stable Python version; let `uv.lock` pin the patch release and exclude development, alpha, beta, and release-candidate builds.
- **Match recipes to the selected series**: built-in CSP, template partials, and tasks require Django 6.0+; `MAILERS`, fetch modes, and the cited mail/CSP checks require 6.1+. On an older supported LTS, use that version's documented equivalents rather than importing newer APIs.
- **Match the database to production**: SQLite is the smallest local or prototype default; use PostgreSQL in development and CI too when PostgreSQL semantics, concurrency, or extensions matter.
- **Settle the user model before migrating**: decide whether authentication will remain Django's built-in shape. If user identity is likely to evolve, create a minimal `AbstractUser` subclass and set `AUTH_USER_MODEL` before the first migration.
- **Default to Django templates, forms, and admin**: add an API, background-task backend, cache, object storage, or frontend toolchain only when a concrete use case needs it.
- **Reject third-party packages Django 6 replaced**: core ships `SECURE_CSP` over `django-csp`, `{% partialdef %}` over `django-template-partials`, and `django.tasks` over `django-tasks`. The built-in task backends are development-only, so select a real backend such as `django-tasks-db` before shipping queued work.
- **Prefer these packages once earned**: when a package earns its place, default to `whitenoise` for `collectstatic` output with its middleware directly after `SecurityMiddleware`, `model-bakery` once fixtures repeat, and `django-debug-toolbar` in development settings only. Packages used only as commands or settings strings (`granian`, `whitenoise`) go in deptry's `[tool.deptry.per_rule_ignores]` `DEP002` list.

## Create the Baseline

Start from Django itself rather than a third-party project template.

```bash
uv init --app --no-package --vcs none --python <supported-python-major.minor> --description "<description>" <slug>
cd <slug>
UV_MALWARE_CHECK=1 uv add --preview-features malware-check "Django~=<stable-major.minor>.0" granian
UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev deptry pytest pytest-cov pytest-django pytest-socket pytest-timeout django-stubs ruff "ty>=<latest>,<0.1" validate-pyproject
uv run django-admin startproject config .
uv run python manage.py startapp <domain>
```

Remove uv's placeholder `main.py` after Django creates `manage.py`; replace each generated `<domain>/tests.py` with a `tests/` package containing `test_*.py` modules because pytest does not collect `tests.py` by default. Remove the generated placeholder comments and unused imports, run `uv run ruff check --fix .` followed by `uv run ruff format .`, and review the fixes.

Keep `config/` limited to settings, root URLs, and WSGI/ASGI entry points. Put behavior in cohesive domain apps, not a generic `core` or `utils`.

Adapt the shared [Python manifest](../../../../python-stack/references/foundation/templates/pyproject.toml.template) and [mise tasks](../../../../python-stack/references/foundation/templates/mise.toml): set `[tool.uv] package = false`, keep only Django application dependencies and remove package build metadata, add Ruff's `DJ` rules, set `DJANGO_SETTINGS_MODULE = "config.settings"` for pytest, and keep warnings as errors. Add `pytest-django` database markers only to tests that access the database. The template assumes a `src/` package with top-level tests, so point `testpaths` and `[tool.coverage.run] source` at the app packages, widen the per-file-ignores key to `"**/tests/**"`, and add `[tool.deptry] extend_exclude = [".*/tests/"]` because deptry skips only a top-level `tests/`; otherwise `filterwarnings = ["error"]` turns pytest's empty-`testpaths` warning into a failure, coverage collects nothing against `fail_under`, and `S101` fires on every test assertion.

## Harden the Generated Project

- **Apply the deployment checklist**: harden `DEBUG` (default off), `SECRET_KEY`, `ALLOWED_HOSTS`, static files, and media per Django's [deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/), keeping local values in an ignored `.env` documented by `.env.example`.
- **Derive security settings from deployment topology**: configure HTTPS, secure cookies, trusted origins, forwarding headers, `MAILERS`, and proxy trust from the actual deployment topology; the generated console mail backend fails `check --deploy` with `mail.E001`, and the legacy `EMAIL_*` settings are deprecated. Never copy proxy settings between providers without verifying the trust boundary.
- **Take Django's own fail-closed defaults first**: before any third party, add `LoginRequiredMiddleware` and mark public views `@login_not_required`; set `SECURE_CSP` from `django.utils.csp.CSP` with `ContentSecurityPolicyMiddleware`, and add `django.template.context_processors.csp` to a template backend whenever the policy uses `CSP.NONCE`, or `check` raises `security.W027`.
- **Fetch relations explicitly**: name the relations you traverse in `select_related()` or `prefetch_related()` or batch them with `QuerySet.fetch_mode(models.FETCH_PEERS)` because the no-argument `select_related()` is deprecated. In regression tests use `models.FETCH_RAISE` so an unintended query raises `FieldFetchBlocked` at its call site instead of a query count you must maintain.

## Canonical Tasks

Reuse the shared format, leak, lint, type, vulnerability, and test tasks. Add these Django checks as a `check:local` dependency, so the pre-commit hook runs them too, and pass production-like environment values to the deployment check without storing real secrets:

```bash
uv run --locked python manage.py check --fail-level WARNING
uv run --locked python manage.py makemigrations --check --dry-run
uv run --locked python manage.py check --deploy --fail-level WARNING
```

Use `uv run python manage.py runserver` only for the `watch` development task. Make `build` produce the real deployment artifact—usually collected static files and an OCI image—rather than a wheel for a non-package application.
