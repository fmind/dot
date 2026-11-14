"""Command tree and entry point for dot."""

import argparse
import contextlib
import os
import shlex
import signal
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

from fmind_dot import __version__, agent, auth, orphan, repository, secrets, system, trust, workstation
from fmind_dot.command import COMPLETE_VARIABLE, Parser, candidates
from fmind_dot.config import dump_config
from fmind_dot.errors import CancelledError, DotError, UsageError
from fmind_dot.state import State, validated_config

# The shared contract agents need before running any command; each command's --help adds its own.
_EPILOG = (
    "Exit codes: 0 success; 1 failure, declined prompt, or unhealthy result; 2 usage error; 130 interrupted. "
    "Reports go to stdout; prompts and errors go to stderr.\n\n"
    "Reports accept --json (-j) and print one JSON document with a versioned schema field; "
    "agent session show always prints JSON and config show prints YAML. "
    "cache, login, setup, prune, pull, trust, and agent session sync accept --dry-run; login also --check; "
    "prune --aggressive needs --yes without a terminal. "
    "Run dot COMMAND --help for examples."
)


def _config_show(state: State, _args: argparse.Namespace) -> None:
    state.stdout.write(dump_config(state.config))


def _config_path(state: State, _args: argparse.Namespace) -> None:
    print(state.config_path, file=state.stdout)


def _config_edit(state: State, _args: argparse.Namespace) -> None:
    try:
        editor = shlex.split(os.environ.get("EDITOR", "")) or ["vi"]
    except ValueError as error:
        raise DotError(f"invalid EDITOR value: {error}") from error
    if state.runner.which(editor[0]) is None:
        raise DotError(f"editor {editor[0]!r} not found in PATH")
    try:
        state.config_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError(f"failed to create config directory: {error}") from error
    code = state.runner.interactive(
        [*editor, str(state.config_path)], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    if code != 0:
        raise DotError(f"editor exited with status {code}")
    validated_config(state.config_argument)
    print("✓ Configuration is valid.", file=state.stdout)


def _register_config(commands: Parser) -> None:
    # Repair commands never validate dot.yaml first: they must work while it is broken.
    group = commands.group("config", "Inspect and edit the dot configuration file")
    group.command("edit", "Open the configuration file in $EDITOR, then validate it", _config_edit, config=False)
    group.command("path", "Print the resolved configuration file path", _config_path, config=False)
    group.command(
        "show", "Print the effective configuration (defaults merged with the file) as YAML", _config_show, config=False
    )


def build_parser() -> Parser:
    """Build the whole tree; help lists commands in this (alphabetical) registration order."""
    root = Parser(prog="dot", summary="Manage workstation tools, repositories, and agent archives", epilog=_EPILOG)
    root.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="<path>",
        # An empty variable counts as unset.
        default=os.environ.get("DOT_CONFIG_PATH") or None,
        help="Path to the configuration file [env: DOT_CONFIG_PATH]",
    )
    root.add_argument(
        "-V", "--version", action="version", version=f"dot version {__version__}", help="Print the version and exit"
    )
    root.set_defaults(handler=root.show_help, needs_config=False, parser=root)
    agent.register(root)
    workstation.register_cache(root)
    system.register_completion(root)
    _register_config(root)
    system.register_doctor(root)
    auth.register_login(root)
    orphan.register(root)
    workstation.register_prune(root)
    repository.register_pull(root)
    secrets.register(root)
    auth.register_setup(root)
    repository.register_status(root)
    trust.register(root)
    return root


def app(arguments: Sequence[str] | None = None) -> None:
    """Parse and run one command; usage errors exit 2 through argparse, failures raise."""
    args = build_parser().parse_args(arguments)
    state = State(config_argument=args.config)
    # Help and parsing need no valid config; commands that read it fail before doing any work.
    if args.needs_config:
        _ = state.config
    try:
        args.handler(state, args)
    except UsageError as error:
        args.parser.error(str(error))


def _interrupt_on_sigterm(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def _complete() -> bool:
    """Answer the Fish completion callback instead of running a command."""
    current = os.environ.get(COMPLETE_VARIABLE)
    if current is None:
        return False
    for value, description in candidates(build_parser(), [*sys.argv[1:], current]):
        sys.stdout.write(f"{value}\t{description}\n" if description else f"{value}\n")
    return True


def main() -> None:
    previous_sigterm = signal.signal(signal.SIGTERM, _interrupt_on_sigterm)
    try:
        if not _complete():
            app()
        sys.stdout.flush()
    except BrokenPipeError:
        with contextlib.suppress(OSError):
            devnull = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(devnull, sys.stdout.fileno())
            finally:
                os.close(devnull)
        raise SystemExit(141) from None
    except KeyboardInterrupt:
        sys.stderr.write("Cancelled.\n")
        raise SystemExit(130) from None
    except CancelledError:
        sys.stderr.write("Cancelled.\n")
        raise SystemExit(1) from None
    except (DotError, OSError, sqlite3.Error, ValueError) as error:
        sys.stderr.write(f"dot: {error}\n")
        raise SystemExit(1) from error
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
