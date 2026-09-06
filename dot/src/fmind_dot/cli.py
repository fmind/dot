"""Typer command tree for dot."""

from __future__ import annotations

import logging
import os
import signal
import sqlite3
import sys
from pathlib import Path
from types import FrameType
from typing import Annotated

import typer
from typer import _click
from typer.core import TyperGroup

from fmind_dot import __version__
from fmind_dot.commands import AliasedGroup, add_group, aliased_command, state_from
from fmind_dot.config import Config, dump_config, load_config
from fmind_dot.errors import DotError
from fmind_dot.state import State

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


class _AlphabeticalGroup(AliasedGroup):
    """Keep the top-level command inventory stable and easy to scan."""


app = typer.Typer(
    name="dot",
    help="Unified CLI utility to manage dotfiles and workspaces",
    cls=_AlphabeticalGroup,
    invoke_without_command=True,
    no_args_is_help=False,
    pretty_exceptions_enable=False,
    context_settings=_CONTEXT_SETTINGS,
)
config_app = typer.Typer(
    help="Inspect, scaffold, edit, and validate the dot configuration file", context_settings=_CONTEXT_SETTINGS
)


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
    verbose: Annotated[
        bool, typer.Option("--verbose", envvar="DOT_VERBOSE", help="Enable verbose debug logging")
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=_version_option, is_eager=True, help="Print the version and exit"),
    ] = False,
) -> None:
    del version
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, stream=sys.stderr)
    state = State(config_argument=config, verbose=verbose)
    context.obj = state
    # Only config repair commands may bypass a missing or malformed file. Eager
    # validation keeps a --config typo from mutating state with built-in defaults.
    if context.invoked_subcommand not in {None, "config", "f"}:
        _ = state.config
    if context.invoked_subcommand is None:
        typer.echo(context.get_help())


@aliased_command(
    config_app, "show", "s", help_text="Print the effective configuration (defaults merged with the file) as YAML"
)
def config_show(context: typer.Context) -> None:
    typer.echo(dump_config(state_from(context).config), nl=False)


@aliased_command(config_app, "path", "p", help_text="Print the resolved configuration file path")
def config_path(context: typer.Context) -> None:
    typer.echo(state_from(context).config_path)


@aliased_command(
    config_app, "init", "i", help_text="Write a starter configuration file populated with the built-in defaults"
)
def config_init(
    context: typer.Context,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite an existing configuration file")] = False,
) -> None:
    path = state_from(context).config_path
    try:
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError(f"failed to create config directory: {error}") from error
    mode = "w" if force else "x"
    try:
        with path.open(mode, encoding="utf-8") as stream:
            stream.write(dump_config(Config()))
    except FileExistsError as error:
        raise DotError(f"config file already exists at {path} (use --force to overwrite)") from error
    except OSError as error:
        raise DotError(f"failed to write config file: {error}") from error
    typer.echo(f"✓ Wrote default configuration to {path}")


@aliased_command(
    config_app, "edit", "e", help_text="Open the configuration file in $EDITOR (scaffolds it first if missing)"
)
def config_edit(context: typer.Context) -> None:
    state = state_from(context)
    if not state.config_path.exists():
        config_init(context)
    editor = os.environ.get("EDITOR", "").split() or ["vi"]
    if state.runner.which(editor[0]) is None:
        raise DotError(f"editor {editor[0]!r} not found in PATH")
    code = state.runner.interactive(
        [*editor, str(state.config_path)], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    if code != 0:
        raise DotError(f"editor exited with status {code}")


@aliased_command(
    config_app, "validate", "v", help_text="Validate that the configuration file parses (strict, unknown keys rejected)"
)
def config_validate(context: typer.Context) -> None:
    state = state_from(context)
    if not state.config_path.exists() and state.config_argument is None:
        typer.echo(f"○ No config file at {state.config_path}; built-in defaults are in effect.")
        return
    load_config(state.config_argument)
    typer.echo(f"✓ Configuration at {state.config_path} is valid.")


@aliased_command(app, "version", "i", help_text="Print the installed package version")
def version_command() -> None:
    typer.echo(f"dot version {__version__}")


def _resolve_help(context: typer.Context, path: list[str]) -> str:
    current = context.find_root()
    command = current.command
    for name in path:
        if not isinstance(command, TyperGroup):
            raise _click.exceptions.UsageError(f"No help topic for {name!r}", current)
        child = command.get_command(current, name)
        if child is None:
            raise _click.exceptions.UsageError(f"No help topic for {name!r}", current)
        current = child.make_context(child.name, [], parent=current, resilient_parsing=True)
        command = child
    return command.get_help(current)


@aliased_command(app, "help", "h", help_text="Show help for dot or one nested command path")
def help_command(
    context: typer.Context,
    path: Annotated[list[str] | None, typer.Argument(help="Nested command path")] = None,
) -> None:
    typer.echo(_resolve_help(context, path or []))


add_group(app, config_app, "config", "f")

# Command modules register after the shared helpers exist, keeping each workflow
# independently testable without a second framework layer.
from fmind_dot import context as context_commands  # noqa: E402
from fmind_dot import maintenance, repository, system  # noqa: E402
from fmind_dot.agent import agent_app  # noqa: E402

add_group(app, agent_app, "agent", "a")
system.register(app)
maintenance.register(app)
repository.register_repository_commands(app)
context_commands.register_context_command(app)


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
            raise SystemExit(130) from None
        except _click.exceptions.NoSuchOption as error:
            error.show(file=sys.stderr)
            raise SystemExit(1) from error
        except _click.exceptions.UsageError as error:
            error.show(file=sys.stderr)
            missing_command = error.message.startswith(("No such command ", "No help topic for "))
            exit_code = 3 if missing_command else 1
            raise SystemExit(exit_code) from error
        except (DotError, OSError, sqlite3.Error, ValueError) as error:
            typer.echo(f"dot: {error}", err=True)
            raise SystemExit(1) from error
        if exit_code:
            raise SystemExit(exit_code)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
