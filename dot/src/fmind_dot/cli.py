"""Typer command tree for dot."""

import os
import shlex
import signal
import sqlite3
import sys
from pathlib import Path
from types import FrameType
from typing import Annotated

import typer
from typer import _click
from typer._click.shell_completion import add_completion_class
from typer.completion import completion_init

from fmind_dot import __version__, orphan, repository, system, trust, workstation
from fmind_dot.agent import agent_app
from fmind_dot.auth import login_app, setup_app
from fmind_dot.command_group import HELP_MARKUP, AlphabeticalGroup, FishCompletion, help_group
from fmind_dot.config import dump_config, load_config
from fmind_dot.errors import DotError
from fmind_dot.secrets import secret_app
from fmind_dot.state import State, state_from

# Plain help (non-TTY) wraps at 80 columns and truncates command summaries; Rich ignores these.
_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "terminal_width": 160, "max_content_width": 160}


# Preserve the shell protocol used by `dot completion` without Typer's duplicate flags.
completion_init()
add_completion_class(FishCompletion, FishCompletion.name)
app = typer.Typer(
    cls=AlphabeticalGroup,
    name="dot",
    help="Manage workstation tools, repositories, and agent archives",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=HELP_MARKUP,
    context_settings=_CONTEXT_SETTINGS,
)
config_app = help_group("Inspect and edit the dot configuration file")


def _version_option(value: bool) -> None:
    if value:
        typer.echo(f"dot version {__version__}")
        raise typer.Exit


@app.callback()
def root(
    context: typer.Context,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", envvar="DOT_CONFIG_PATH", help="Path to the configuration file")
    ] = None,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=_version_option, is_eager=True, help="Print the version and exit"),
    ] = False,
) -> None:
    del version
    context.obj = State(config_argument=config)
    if context.invoked_subcommand is None:
        typer.echo(context.get_help())


@config_app.command("show", help="Print the effective configuration (defaults merged with the file) as YAML")
def config_show(context: typer.Context) -> None:
    typer.echo(dump_config(state_from(context).config), nl=False)


@config_app.command("path", help="Print the resolved configuration file path")
def config_path(context: typer.Context) -> None:
    typer.echo(state_from(context).config_path)


@config_app.command("edit", help="Open the configuration file in $EDITOR, then validate it")
def config_edit(context: typer.Context) -> None:
    state = state_from(context)
    editor = shlex.split(os.environ.get("EDITOR", "")) or ["vi"]
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
    load_config(state.config_argument)
    typer.echo("✓ Configuration is valid.")


app.add_typer(config_app, name="config")
app.add_typer(agent_app, name="agent")
app.add_typer(login_app, name="login")
app.add_typer(setup_app, name="setup")
app.add_typer(secret_app, name="secret")
for module in (workstation, system, repository, trust, orphan):
    module.register(app)


def _invoke_app() -> int:
    result = app(standalone_mode=False)
    return result if isinstance(result, int) else 0


def _interrupt_on_sigterm(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def main() -> None:
    previous_sigterm = signal.signal(signal.SIGTERM, _interrupt_on_sigterm)
    try:
        try:
            exit_code = _invoke_app()
        except KeyboardInterrupt:
            typer.echo("Cancelled.", err=True)
            raise SystemExit(130) from None
        except typer.Abort as error:
            # Typer converts Ctrl+C and EOF at prompts into Abort. The context
            # retains the distinction from a deliberate declined confirmation.
            typer.echo("Cancelled.", err=True)
            interrupted = isinstance(error.__context__, KeyboardInterrupt)
            raise SystemExit(130 if interrupted else 1) from None
        except _click.exceptions.UsageError as error:
            error.show(file=sys.stderr)
            raise SystemExit(2) from error
        except (DotError, OSError, sqlite3.Error, ValueError) as error:
            typer.echo(f"dot: {error}", err=True)
            raise SystemExit(1) from error
        if exit_code:
            raise SystemExit(exit_code)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
