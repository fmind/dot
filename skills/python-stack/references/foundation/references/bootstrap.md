# Python Package Foundation

For new packages only ([project-scaffolding](../../../../project-scaffolding/references/bootstrap.md) owns repo creation/CI; existing projects keep their layout).

1. **Select identifiers**: distribution `<slug>`, `<description>`, `<holder>`, supported Python range, underscored `<package>`, and exact Python pin from the [mise baseline](../../../../mise/references/tool-versions.md).
1. **Initialize**:
   ```bash
   uv init --lib --build-backend uv --vcs none --python <exact-python-version> --description "<description>" <slug>
   cd <slug>
   ```
1. **Write `pyproject.toml`** from [pyproject.toml.template](../templates/pyproject.toml.template), substituting placeholders with `dependencies = []` and no `[project.scripts]` ([uv](../../uv.md)).
1. **Copy foundation files**: [mise.toml](../templates/mise.toml), [lefthook.yml](../templates/lefthook.yml), [gitignore](../templates/gitignore) (`.gitignore`), [ignore](../templates/ignore) (`.ignore`, non-Python noise only — Ruff and `ty` also skip `.ignore` paths), [AGENTS.md.template](../templates/AGENTS.md.template) (`AGENTS.md`), [zensical.toml](../templates/zensical.toml), [docs-index.md](../templates/docs-index.md) (`docs/index.md`), plus `dprint.json` ([dprint](../../../../mise/references/dprint.md)). Pin exact Python + tool versions in `mise.toml` (strip selector comments), align `.python-version`, write `README.md` ([repository-docs](../../../../repository-docs/SKILL.md)) and `LICENSE` ([project-license](../../../../project-scaffolding/references/project-license/GUIDE.md)), then run `mise lock && uv lock` (`mise run install` requires `uv.lock`).
1. **Add library starter**: copy [init-library.py](../templates/init-library.py) to `src/<package>/__init__.py` (keep `py.typed`) and [test_library.py](../templates/test_library.py) to `tests/test_library.py`.
1. **Layer profile** from [profiles](../GUIDE.md#profiles-and-owners) (argparse/Litestar replace starter code/tests; remove `test:integration` unless `integration`-marked tests exist, since pytest exits `5` on empty selection).
1. **Qualify offline**: run `mise run install && mise run all`, then install the built wheel in a fresh `uv` venv and verify public imports (plus CLI and `python -m <package>` for apps).
