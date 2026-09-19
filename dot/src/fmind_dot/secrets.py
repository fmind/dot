"""Explicit, process-scoped access to personal credentials."""

import os
import re
import stat
from pathlib import Path
from typing import Annotated

import typer

from fmind_dot.command_group import help_group
from fmind_dot.errors import DotError
from fmind_dot.state import State, require_tools, state_from

secret_app = help_group("Use personal credentials for one command without exporting them globally")
_PYPI_UPLOAD = "https://upload.pypi.org/legacy/"
_PYPI_CHECK = "https://pypi.org/simple/"


def personal_token(name: str) -> str:
    """An explicit environment value wins, including an empty value that fails closed."""
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
        raise typer.BadParameter("expected an uppercase environment variable name", param_hint="NAME")
    if name in os.environ:
        value = os.environ[name]
    else:
        path = Path.home() / ".config/dot/secrets" / name
        try:
            # Do not follow links or block on FIFOs; verify the opened inode before reading.
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise DotError(f"{name}: personal secret must be an owner-only regular file (chmod 600)")
                raw = stream.read(65537)
                if len(raw) > 65536:
                    raise DotError(f"{name}: personal secret exceeds 64 KiB")
                value = raw.decode("utf-8").rstrip("\r\n")
        except (OSError, UnicodeError) as error:
            raise DotError(f"{name}: cannot read personal secret; configure ~/.config/dot/secrets/{name}") from error
    if not value or any(character in value for character in "\x00\r\n"):
        raise DotError(f"{name}: credential is empty or contains a line break; no personal fallback was used")
    return value


def launch(state: State, command: list[str], name: str) -> None:
    require_tools(state, [command])
    code = state.runner.interactive(
        command,
        env={name: personal_token(name)},
        stdin=state.stdin,
        stdout=state.stdout,
        stderr=state.stderr,
    )
    raise typer.Exit(code if code >= 0 else 128 - code)


@secret_app.command("run", help="Supply NAME to COMMAND; an existing environment value wins")
def run(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help="Variable stored in ~/.config/dot/secrets/NAME")],
    command: Annotated[list[str], typer.Argument(help="Command and arguments, following --")],
) -> None:
    if name == "UV_PUBLISH_TOKEN":
        raise typer.BadParameter("use dot secret publish for the personal PyPI token", param_hint="NAME")
    launch(state_from(context), command, name)


@secret_app.command("publish", help="Publish to PyPI using the personal token; other registries use uv publish")
def publish(
    context: typer.Context,
    files: Annotated[list[str] | None, typer.Argument(help="Distribution paths or globs (default: dist/*)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Ask uv to validate without uploading")] = False,
) -> None:
    # Do not accidentally combine a customer's publishing configuration with a personal token.
    overrides = (
        "UV_PUBLISH_INDEX",
        "UV_PUBLISH_URL",
        "UV_PUBLISH_CHECK_URL",
        "UV_PUBLISH_USERNAME",
        "UV_PUBLISH_PASSWORD",
        "UV_CONFIG_FILE",
        "UV_INSECURE_HOST",
    )
    if any(name in os.environ for name in overrides):
        raise DotError("publishing overrides are set; use uv publish with your chosen credentials instead")
    command = [
        "uv",
        "publish",
        "--no-config",
        "--publish-url",
        _PYPI_UPLOAD,
        "--check-url",
        _PYPI_CHECK,
        "--trusted-publishing",
        "never",
        "--keyring-provider",
        "disabled",
    ]
    if dry_run:
        command.append("--dry-run")
    command.extend(["--", *(files or ["dist/*"])])
    launch(state_from(context), command, "UV_PUBLISH_TOKEN")
