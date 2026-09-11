"""Consistent alphabetical discovery for every CLI command group."""

from typing import Annotated

import typer
from typer import _click
from typer.core import TyperGroup

# One help string keeps every structured-output flag documented identically.
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Emit structured JSON")]


class AlphabeticalGroup(TyperGroup):
    """Order help and completion independently of command registration."""

    def list_commands(self, ctx: _click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))


def help_group(description: str) -> typer.Typer:
    """Use one no-argument contract for every command group, including singletons."""
    group = typer.Typer(
        cls=AlphabeticalGroup,
        help=description,
        invoke_without_command=True,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    @group.callback()
    def show_help(context: typer.Context) -> None:
        if context.invoked_subcommand is None:
            typer.echo(context.get_help())

    return group
