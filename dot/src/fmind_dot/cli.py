"""Typer command tree for dot."""

import logging
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
from typer.completion import completion_init

from fmind_dot import __version__
from fmind_dot.command_group import AlphabeticalGroup
from fmind_dot.config import Config, dump_config, load_config
from fmind_dot.errors import DotError
from fmind_dot.state import State, state_from

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


# Preserve the shell protocol used by `dot completion` without Typer's duplicate flags.
completion_init()
app = typer.Typer(
    cls=AlphabeticalGroup,
    name="dot",
    help="Unified CLI utility to manage dotfiles and workspaces",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    pretty_exceptions_enable=False,
    context_settings=_CONTEXT_SETTINGS,
)
config_app = typer.Typer(
    cls=AlphabeticalGroup,
    help="Inspect, scaffold, edit, and validate the dot configuration file",
    context_settings=_CONTEXT_SETTINGS,
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
    if context.invoked_subcommand not in {None, "config"}:
        _ = state.config
    if context.invoked_subcommand is None:
        typer.echo(context.get_help())


@config_app.command("show", help="Print the effective configuration (defaults merged with the file) as YAML")
def config_show(context: typer.Context) -> None:
    typer.echo(dump_config(state_from(context).config), nl=False)


@config_app.command("path", help="Print the resolved configuration file path")
def config_path(context: typer.Context) -> None:
    typer.echo(state_from(context).config_path)


@config_app.command("init", help="Write a starter configuration file populated with the built-in defaults")
def config_init(
    context: typer.Context,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite an existing configuration file")] = False,
) -> None:
    path = state_from(context).config_path
    if _managed_config(state_from(context)):
        raise DotError("configuration is managed by chezmoi; use dot config edit")
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


@config_app.command("edit", help="Open the configuration file in $EDITOR (scaffolds it first if missing)")
def config_edit(context: typer.Context) -> None:
    state = state_from(context)
    if _managed_config(state):
        code = state.runner.interactive(
            ["chezmoi", "edit", "--apply", "--force", str(state.config_path)],
            stdin=state.stdin,
            stdout=state.stdout,
            stderr=state.stderr,
        )
        if code:
            raise DotError(f"chezmoi editor exited with status {code}")
        load_config(state.config_argument)
        typer.echo("✓ Managed configuration is valid.")
        return
    if not state.config_path.exists():
        config_init(context)
    editor = shlex.split(os.environ.get("EDITOR", "")) or ["vi"]
    if state.runner.which(editor[0]) is None:
        raise DotError(f"editor {editor[0]!r} not found in PATH")
    code = state.runner.interactive(
        [*editor, str(state.config_path)], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    if code != 0:
        raise DotError(f"editor exited with status {code}")
    load_config(state.config_argument)
    typer.echo("✓ Configuration is valid.")


def _managed_config(state: State) -> bool:
    if state.runner.which("chezmoi") is None:
        return False
    result = state.runner.run(
        ["chezmoi", "managed", "--path-style=absolute", "--nul-path-separator"],
        timeout=30,
    )
    paths = result.stdout.split("\0")
    return str(state.config_path.absolute()) in paths


@config_app.command("validate", help="Validate that the configuration file parses (strict, unknown keys rejected)")
def config_validate(context: typer.Context) -> None:
    state = state_from(context)
    if not state.config_path.exists() and state.config_argument is None:
        typer.echo(f"○ No config file at {state.config_path}; built-in defaults are in effect.")
        return
    load_config(state.config_argument)
    typer.echo(f"✓ Configuration at {state.config_path} is valid.")


app.add_typer(config_app, name="config")

# Command modules register after the shared helpers exist, keeping each workflow
# independently testable without a second framework layer.
from fmind_dot import repository, system  # noqa: E402
from fmind_dot.agent import agent_app  # noqa: E402

app.add_typer(agent_app, name="agent")
system.register(app)
repository.register_repository_commands(app)


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
