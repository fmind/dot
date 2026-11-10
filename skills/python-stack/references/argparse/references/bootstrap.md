# argparse CLI Bootstrap

For a new packaged CLI, create the minimal foundation through [python-stack](../../foundation/GUIDE.md), then apply this profile before its final qualification. Existing CLIs keep their layout and framework.

1. **Agree the contract**: agree command behavior through [cli-contracts](../../cli-contracts.md). The starter adds no dependency: `argparse` ships with Python.
1. **Install the CLI starter**: replace the foundation's example with [init-cli.py](../templates/init-cli.py) at `src/<package>/__init__.py`; add [main.py](../templates/main.py) as `src/<package>/__main__.py`. Replace `<slug>`, `<package>`, and `<description>` throughout. The starter is an explicit group: `<slug> greet --name Ada`, root `--version`, and root/subcommand `-h` / `--help`; a bare `<slug>` is a usage error. For a focused single-command tool, drop the subparsers and add the arguments to the root parser; update the invocation tests accordingly. The displayed version reads the installed package metadata, so it follows `pyproject.toml`.
1. **Add the installed command to `pyproject.toml`**:
   ```toml
   [project.scripts]
   <slug> = "<package>:main"
   ```
1. **Adopt the CLI test templates**: use [test_smoke.py](../templates/test_smoke.py) and [test_cli.py](../templates/test_cli.py) in `tests/`, replacing the library's version-only example. They exercise help, version, usage errors, and streams in-process, and the module entry point in a subprocess. Set `mise`'s `watch` command to `uv run <slug> greet` when useful; otherwise retain the shared test watcher.
1. **Document and qualify the installed CLI**: update project `AGENTS.md` with the command and module entry points. Run the shared quality gate, then install the wheel in a fresh environment and exercise the command and `python -m <package>` outside the source tree. Check help aliases, version, a successful invocation, and invalid arguments with exit 2 from the installed command.
