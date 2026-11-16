"""<description>."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import version

__version__ = version("<slug>")


def greet(name: str = "world", *, as_json: bool = False) -> None:
    """Print a greeting in plain text or machine-readable JSON."""
    if not name.strip():
        raise ValueError("name must not be empty")
    message = f"Hello, {name}!"
    payload = json.dumps({"greeting": message}) if as_json else message
    sys.stdout.write(f"{payload}\n")


def build_parser() -> argparse.ArgumentParser:
    """Define every command in one place; help and usage errors derive from it."""
    parser = argparse.ArgumentParser(
        prog="<slug>", description="<description>.", allow_abbrev=False, suggest_on_error=True
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(title="commands", metavar="COMMAND", required=True)
    command = commands.add_parser(
        "greet", help="Print a greeting", description="Print a greeting.", allow_abbrev=False, suggest_on_error=True
    )
    command.add_argument("--name", default="world", metavar="NAME", help="Name to greet")
    command.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output on stdout")
    command.set_defaults(handler=lambda args: greet(name=args.name, as_json=args.as_json))
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point invoked by the `<slug>` console script or `uv run`."""
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Error: {type(error).__name__}. Check the input and retry.\n")
        raise SystemExit(1) from error
