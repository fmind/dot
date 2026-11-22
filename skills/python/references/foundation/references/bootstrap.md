# Python Package Foundation

For new packages only ([bootstrap](../../../../github/references/bootstrap.md) owns repo creation/CI; existing projects keep their layout).

1. **Select identifiers**: distribution `<slug>`, GitHub `<owner>` (`<owner>/<slug>`), `<description>`, `<holder>`, supported Python range (`3.14` default; `3.15` for pure-Python packages), underscored `<package>`, and exact Python pin from the [mise baseline](../../../../mise/references/tool-versions.md).
1. **Initialize**:
   ```bash
   uv init --lib --build-backend uv --vcs none --python <exact-python-version> --description "<description>" <slug>
   cd <slug>
   ```
1. **Write `pyproject.toml`** from [pyproject.toml.template](../templates/pyproject.toml.template), substituting placeholders (including `<owner>` in `[project.urls]`, or dropping `[project.urls]` for non-GitHub internal packages; keep `github.com/<owner>/<slug>`, `<owner>.github.io/<slug>/`, and email-less `authors` for PyPI verification). Keep `dependencies = []`, omit `[project.scripts]`, and keep `license = "LicenseRef-Proprietary"` for private/internal repos (switch to `MIT` only for public OSS per [project-license](../../../../github/references/project-license/GUIDE.md); [uv](../GUIDE.md#uv)).
1. **Copy foundation files**: [mise.toml](../templates/mise.toml), [lefthook.yml](../templates/lefthook.yml), [gitignore](../templates/gitignore) (`.gitignore`), [ignore](../templates/ignore) (`.ignore`, non-Python noise only — Ruff and `ty` also skip `.ignore` paths), [AGENTS.md.template](../templates/AGENTS.md.template) (`AGENTS.md`), plus [dprint.json](../../../../mise/templates/dprint.json) ([dprint](../../../../mise/references/dprint.md)) and [betterleaks.toml](../../../../code-security/templates/betterleaks.toml) (`.betterleaks.toml`). Pin exact Python + tool versions in `mise.toml` (strip selector comments), align `.python-version`, write `README.md` ([docs/repository](../../../../docs/references/repository/GUIDE.md)) and `LICENSE` ([project-license](../../../../github/references/project-license/GUIDE.md)), then run `mise lock && uv lock` (`mise run install` requires `uv.lock`).
1. **Add library starter**: copy [init-library.py](../templates/init-library.py) to `src/<package>/__init__.py` (keep `py.typed`) and [test_library.py](../templates/test_library.py) to `tests/test_library.py`.
1. **Layer profile & opt-in extensions** from [foundation](../GUIDE.md#workflow):
   - Add CLI/web/ML/agent dependencies and templates per specialist guide.
   - **Docs site (libraries/OSS)**: add `"zensical>=0.1.1,<0.2"` and `"mkdocstrings-python>=2.0.11"` to `dev`, copy [zensical.toml](../templates/zensical.toml) and [docs-index.md](../templates/docs-index.md) (`docs/index.md`), and add `build:docs` / `serve:docs` tasks per [docs/site](../../../../docs/references/site/GUIDE.md).
   - **Docker integration tests**: add `[tasks."test:integration"]` (`uv run --locked pytest -q -m integration --force-enable-socket --timeout=600`) only once `integration`-marked tests exist (`pytest` exits `5` on empty selection).
1. **Qualify offline**: run `mise run install && mise run all`, then install the built wheel in a fresh `uv` venv and verify public imports (plus CLI and `python -m <package>` for apps).
