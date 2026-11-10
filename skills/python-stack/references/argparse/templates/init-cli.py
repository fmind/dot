"""<description>."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version

__version__ = version("<slug>")


def greet(name: str = "world") -> None:
    """Print a greeting."""
    sys.stdout.write(f"Hello, {name}!\n")


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
    command.set_defaults(handler=lambda args: greet(name=args.name))
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point invoked by the `<slug>` console script or `uv run`."""
    args = build_parser().parse_args(argv)
    args.handler(args)
