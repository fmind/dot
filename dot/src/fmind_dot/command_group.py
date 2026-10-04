"""Consistent alphabetical discovery for every CLI command group."""

import sys
from typing import Annotated, Literal

import typer
from typer import _click
from typer._click.shell_completion import CompletionItem
from typer._completion_classes import FishComplete
from typer.core import TyperGroup

# Rich panels triple help size; agents and pipes read plain Click help instead.
HELP_MARKUP: Literal["rich"] | None = "rich" if sys.stdout.isatty() else None

# One help string keeps every structured-output flag documented identically.
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Emit structured JSON")]


class AlphabeticalGroup(TyperGroup):
    """Order help and completion independently of command registration."""

    def list_commands(self, ctx: _click.Context) -> list[str]:
        return sorted(super().list_commands(ctx))

    def invoke(self, ctx: _click.Context) -> object:
        # Typer's main turns a command's KeyboardInterrupt (Ctrl+C, or SIGTERM via cli.main)
        # into a silent Exit(130); Abort reaches cli.main, which reports the cancellation.
        try:
            return super().invoke(ctx)
        except KeyboardInterrupt as error:
            raise typer.Abort from error

    def shell_complete(self, ctx: _click.Context, incomplete: str) -> list[CompletionItem]:
        # Click cuts command summaries at 45 columns, hiding most of their meaning;
        # the shell fits the complete first line to the terminal instead.
        items = super().shell_complete(ctx, incomplete)
        for item in items:
            if (command := self.commands.get(item.value)) is not None:
                item.help = command.get_short_help_str(limit=sys.maxsize)
        return items


class FishCompletion(FishComplete):
    """Emit one line per candidate: Typer renders help through Rich, which wraps it at the
    terminal width, so a narrow pane would split a description into a bogus candidate."""

    def format_completion(self, item: CompletionItem) -> str:
        # dot help carries no Rich markup; collapsing whitespace is the only formatting needed.
        return f"{item.value}\t{' '.join(item.help.split())}" if item.help else str(item.value)


def help_group(description: str) -> typer.Typer:
    """Use one no-argument contract for every command group, including singletons."""
    group = typer.Typer(
        cls=AlphabeticalGroup,
        help=description,
        invoke_without_command=True,
        rich_markup_mode=HELP_MARKUP,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    @group.callback()
    def show_help(context: typer.Context) -> None:
        if context.invoked_subcommand is None:
            typer.echo(context.get_help())

    return group
