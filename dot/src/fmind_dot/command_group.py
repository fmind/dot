"""Consistent alphabetical discovery for every CLI command group."""

from typer import _click
from typer.core import TyperGroup


class AlphabeticalGroup(TyperGroup):
    """Order help and completion independently of command registration."""

    def list_commands(self, ctx: _click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))
