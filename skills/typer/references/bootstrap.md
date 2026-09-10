# Typer CLI Bootstrap

For a new packaged CLI, create the minimal foundation through [python-stack](../../python-stack/SKILL.md), then apply this profile before its final qualification. Existing CLIs keep their layout.

1. Add `typer` through [uv](../../uv/SKILL.md); agree command behavior through [cli-contracts](../../cli-contracts/SKILL.md).
1. Replace the foundation's example with [init-cli.py](init-cli.py) at `src/<package>/__init__.py`; add [main.py](main.py) as `src/<package>/__main__.py`. Replace `<slug>`, `<package>`, and `<description>` throughout.
1. Add the installed command to `pyproject.toml`:
   ```toml
   [project.scripts]
   <slug> = "<package>:main"
   ```
1. Use [test_smoke.py](test_smoke.py) and [test_cli.py](test_cli.py) in `tests/`, replacing the library's version-only example. Set `mise`'s `watch` command to `uv run <slug>` when useful; otherwise retain the shared test watcher.
1. Update project `AGENTS.md` with the command and module entry points. Run the shared quality gate, then install the wheel in a fresh environment and exercise the command and `python -m <package>` outside the source tree. Check help, a successful invocation, and invalid arguments with a nonzero exit code.
