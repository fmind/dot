# Python Package Foundation

Use this for a new package. [new-project](../../new-project/SKILL.md) owns repository creation and shared setup; this procedure supplies the Python files. Existing projects retain their conventions.

1. **Identify** the distribution slug, description, holder, supported Python range, and import package (`<slug>` with underscores). Select and pin a supported stable interpreter through [uv](../../uv/SKILL.md).
1. **Initialize** the package:
   ```bash
   uv init --lib --build-backend uv --vcs none --description "<description>" <slug>
   cd <slug>
   uv python pin <major.minor>
   ```
1. **Configure** `pyproject.toml` from [the shared manifest](pyproject.toml.template), replacing placeholders and preserving the selected Python support range. Start with `dependencies = []` and no console entry point. [uv](../../uv/SKILL.md) owns dependency and build-backend operations.
1. **Add project files**: [mise.toml](mise.toml), [lefthook.yml](lefthook.yml), [gitignore](gitignore), and [AGENTS.md](AGENTS.md); configure dprint through [dprint](../../dprint/SKILL.md). Fill the README and license through [repository-docs](../../repository-docs/SKILL.md) and [project-license](../../project-license/SKILL.md) before building.
1. **Add the library example** as `src/<package>/__init__.py` from [init-library.py](init-library.py) and `tests/test_library.py` from [test_library.py](test_library.py). Replace generated placeholder sources and tests with the selected examples; a library needs no `__main__.py` or `[project.scripts]`.
1. **Apply the selected profile** from [profiles](profiles.md). Typer and Litestar own their application dependencies, source files, entry points, and tests; do not copy a web configuration into a library. Generated agents and Django applications use their owners' bootstrap procedures.
1. **Qualify the final package**: after repository initialization, run `mise run install` and `mise run all`. Install the built wheel in a fresh uv environment and exercise its public import outside the source tree. Applications also exercise the installed command and `python -m <package>`; [uv](../../uv/SKILL.md) owns environment and installation commands.

No publication or provider access is required to qualify the package locally.
