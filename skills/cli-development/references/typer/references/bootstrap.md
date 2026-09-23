# Typer CLI Bootstrap

For a new packaged CLI, create the minimal foundation through [python-stack](../../../../python-stack/references/foundation/GUIDE.md), then apply this profile before its final qualification. Existing CLIs keep their layout.

1. Add `typer` through [uv](../../../../python-stack/references/uv.md); agree command behavior through [cli-contracts](../../cli-contracts.md).
1. Replace the foundation's example with [init-cli.py](../templates/init-cli.py) at `src/<package>/__init__.py`; add [main.py](../templates/main.py) as `src/<package>/__main__.py`. Replace `<slug>`, `<package>`, and `<description>` throughout. The starter is an explicit group: `<slug> greet --name Ada`, root `--version`, and root/subcommand `-h` / `--help`. For a focused single-command tool, omit the group callback, move its eager version option onto the command, and set `no_args_is_help` on the command only when inputs are required; update the invocation tests accordingly. Keep package metadata and displayed version aligned when releasing.
1. Add the installed command to `pyproject.toml`:
   ```toml
   [project.scripts]
   <slug> = "<package>:main"
   ```
1. Use [test_smoke.py](../templates/test_smoke.py) and [test_cli.py](../templates/test_cli.py) in `tests/`, replacing the library's version-only example. They exercise help, version, usage errors, streams, and Bash/Zsh/Fish completion generation. Set `mise`'s `watch` command to `uv run <slug> greet` when useful; otherwise retain the shared test watcher.
1. Update project `AGENTS.md` with the command and module entry points. Run the shared quality gate, then install the wheel in a fresh environment and exercise the command and `python -m <package>` outside the source tree. Check help aliases, version, a successful invocation, invalid arguments with exit 2, and completion generation from the installed command. Generation tests do not replace native shell checks when shell integration changes.
