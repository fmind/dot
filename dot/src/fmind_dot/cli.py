"""Command tree and entry point for dot."""

import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path

from fmind_dot import __version__, auth, context_budget, repository, system, trust
from fmind_dot.command import COMPLETE_VARIABLE, Parser, candidates
from fmind_dot.errors import DotError, UsageError, flush_stdout_on_error, suppress_broken_pipe_stdout
from fmind_dot.state import State

_EPILOG = (
    "Exit codes: 0 success; 1 failure or unhealthy result; 2 usage error; 130 interrupted. "
    "Reports go to stdout; prompts and errors go to stderr.\n\n"
    "Reports accept --json (-j) and print one JSON document with a versioned schema field. "
    "login accepts --dry-run and --check. Run dot COMMAND --help for examples."
)


def build_parser() -> Parser:
    """Build the command tree; help lists commands in registration order."""
    root = Parser(prog="dot", summary="Manage workstation tools, repositories, and agent setup", epilog=_EPILOG)
    root.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="PATH",
        default=os.environ.get("DOT_CONFIG_PATH") or None,
        help="Path to the configuration file [env: DOT_CONFIG_PATH]",
    )
    root.add_argument(
        "-V", "--version", action="version", version=f"dot version {__version__}", help="Print the version and exit"
    )
    root.set_defaults(handler=root.show_help, needs_config=False, parser=root)
    context_budget.register(root)
    system.register_doctor(root)
    auth.register_login(root)
    repository.register_pull(root)
    repository.register_status(root)
    trust.register(root)
    return root


def app(arguments: Sequence[str] | None = None) -> None:
    """Parse and run one command; usage errors exit 2 through argparse, failures raise."""
    args = build_parser().parse_args(arguments)
    state = State(config_argument=args.config)
    if args.needs_config:
        _ = state.config
    try:
        args.handler(state, args)
    except UsageError as error:
        args.parser.error(str(error))


def _interrupt_on_sigterm(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> None:
    previous_sigterm = signal.signal(signal.SIGTERM, _interrupt_on_sigterm)
    try:
        try:
            if (current := os.environ.get(COMPLETE_VARIABLE)) is not None:
                for value, description in candidates(build_parser(), [*sys.argv[1:], current]):
                    sys.stdout.write(f"{value}\t{description}\n" if description else f"{value}\n")
            else:
                app()
        except SystemExit:
            sys.stdout.flush()
            raise
        sys.stdout.flush()
    except BrokenPipeError:
        suppress_broken_pipe_stdout()
    except KeyboardInterrupt:
        flush_stdout_on_error()
        sys.stderr.write("Cancelled.\n")
        raise SystemExit(130) from None
    except (DotError, OSError, ValueError) as error:
        flush_stdout_on_error()
        sys.stderr.write(f"dot: {error}\n")
        raise SystemExit(1) from error
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
