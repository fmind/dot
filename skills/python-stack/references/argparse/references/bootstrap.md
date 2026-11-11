# argparse CLI Bootstrap

Layer onto [python-stack](../../foundation/GUIDE.md) for new packaged CLIs; existing CLIs keep their layout and framework.

1. **Contract**: define behavior per [cli-contracts](../../cli-contracts.md) (zero runtime dependencies).
1. **Starter code**: copy [init-cli.py](../templates/init-cli.py) to `src/<package>/__init__.py` and [main.py](../templates/main.py) to `src/<package>/__main__.py`, replacing `<slug>`, `<package>`, and `<description>`. Default shape is `<slug> greet --name Ada`, root `--version` (via `importlib.metadata`), `-h`/`--help`, and exit `2` on bare `<slug>` (drop subparsers for single-command tools).
1. **Entry point**: add `[project.scripts]` `<slug> = "<package>:main"` in `pyproject.toml`.
1. **Tests & watch**: replace library tests with [test_smoke.py](../templates/test_smoke.py) and [test_cli.py](../templates/test_cli.py) (optional `watch`: `uv run <slug> greet`).
1. **Qualify**: document CLI/module entry points in `AGENTS.md`, pass the project gate, install the wheel in a fresh venv, and verify `<slug>`, `python -m <package>`, `--help`, `--version`, and exit `2` on invalid args outside the source tree.
