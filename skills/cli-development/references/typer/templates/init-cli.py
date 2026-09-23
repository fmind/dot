"""<description>."""

from __future__ import annotations

from typing import Annotated

import typer

__version__ = "0.1.0"
app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


def version_callback(value: bool) -> None:
    """Print the version before command validation or application setup."""
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=0)


@app.callback()
def cli(
    _version: Annotated[
        bool, typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    """<description>."""


@app.command()
def greet(name: Annotated[str, typer.Option(help="Name to greet")] = "world") -> None:
    """Print a greeting."""
    typer.echo(f"Hello, {name}!")


def main() -> None:
    """Entry point invoked by the `<slug>` console script or `uv run`."""
    app()
