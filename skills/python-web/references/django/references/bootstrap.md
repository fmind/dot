# Django Bootstrap

## Decide Before Scaffolding

- **Target stable releases**: pick the latest stable Django series (or current LTS when constrained) and stable Python; let `uv.lock` pin patches and exclude pre-releases.
- **Match recipes to series**: built-in CSP, template partials, and `django.tasks` require Django `6.0+`; `MAILERS`, fetch modes, and mail/CSP checks require `6.1+` (use LTS equivalents on older series).
- **Match DB to production**: SQLite for small/local prototypes; PostgreSQL in dev and CI when Postgres semantics, concurrency, or extensions matter.
- **Settle `AUTH_USER_MODEL` before first migration**: subclass `AbstractUser` upfront if user identity may evolve.
- **Start with core Django**: templates, forms, and admin first; add APIs, task workers, caches, object storage, or frontend toolchains only when needed.
- **Drop packages Django 6 replaced**: use `SECURE_CSP` (over `django-csp`), `{% partialdef %}` (over `django-template-partials`), and `django.tasks` (over `django-tasks`; pair with a real backend like `django-tasks-db` in production since built-in backends are dev-only).
- **Preferred add-ons once earned**: `whitenoise` (directly after `SecurityMiddleware`), `model-bakery` (repeated fixtures), `django-debug-toolbar` (dev only). Ignore CLI/settings-only packages (`granian`, `whitenoise`) under `[tool.deptry.per_rule_ignores]` `DEP002`.

## Create the Baseline

```bash
uv init --app --no-package --vcs none --python <supported-python-major.minor> --description "<description>" <slug>
cd <slug>
UV_MALWARE_CHECK=1 uv add --preview-features malware-check "Django~=<stable-major.minor>.0" granian
UV_MALWARE_CHECK=1 uv add --preview-features malware-check --dev deptry pytest pytest-cov pytest-django pytest-socket pytest-timeout django-stubs ruff "ty>=<latest>,<0.1" validate-pyproject
uv run django-admin startproject config .
uv run python manage.py startapp <domain>
```

Delete `main.py`, replace `<domain>/tests.py` with `<domain>/tests/test_*.py` (pytest skips `tests.py`), strip generated boilerplate/unused imports, and run `uv run ruff check --fix . && uv run ruff format .`. Keep `config/` to settings, root URLs, and WSGI/ASGI; put logic in domain apps (not `core`/`utils`).

Adapt [pyproject.toml.template](../../../../python-stack/references/foundation/templates/pyproject.toml.template) and [mise.toml](../../../../python-stack/references/foundation/templates/mise.toml): set `[tool.uv] package = false` (drop build metadata), add Ruff `DJ` rules, set `DJANGO_SETTINGS_MODULE = "config.settings"`, mark only DB tests with `pytest-django`, point `testpaths` and `[tool.coverage.run] source` at app packages, widen Ruff test ignores to `"**/tests/**"`, and set `[tool.deptry] extend_exclude = [".*/tests/"]` (avoids empty-`testpaths` error under `filterwarnings = ["error"]`, zero-coverage failure, and `S101` on nested tests).

## Harden the Generated Project

- **Deployment checklist**: default `DEBUG` off and configure `SECRET_KEY`, `ALLOWED_HOSTS`, static, and media per the [deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/), using an ignored `.env` + `.env.example`.
- **Topology-matched security & mail**: set HTTPS, secure cookies, trusted origins, forwarding headers, proxy trust, and `MAILERS` (`EMAIL_*` is deprecated and the console backend fails `check --deploy` with `mail.E001`).
- **Fail-closed defaults**: enable `LoginRequiredMiddleware` (marking public views `@login_not_required`) and `ContentSecurityPolicyMiddleware` with `SECURE_CSP` (`django.utils.csp.CSP`; include `django.template.context_processors.csp` when using `CSP.NONCE` to avoid `security.W027`).
- **Explicit relation fetching**: pass explicit fields to `select_related()` / `prefetch_related()` or `QuerySet.fetch_mode(models.FETCH_PEERS)` (bare `select_related()` is deprecated); use `models.FETCH_RAISE` in regression tests to fail unintended queries with `FieldFetchBlocked`.

## Canonical Tasks

Wire into `check:local` (passing non-secret prod-like env vars to `--deploy`):

```bash
uv run --locked python manage.py check --fail-level WARNING
uv run --locked python manage.py makemigrations --check --dry-run
uv run --locked python manage.py check --deploy --fail-level WARNING
```

Use `manage.py runserver` only for `watch`; make `build` emit collected static assets + OCI image rather than a wheel.
