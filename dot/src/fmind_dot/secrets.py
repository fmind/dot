"""Explicit, process-scoped access to personal credentials."""

import argparse
import os
import re
import stat
from pathlib import Path

from fmind_dot.command import Parser
from fmind_dot.errors import DotError, UsageError
from fmind_dot.state import State, require_tools

_MAX_SECRET_BYTES = 64 << 10


def personal_token(name: str) -> str:
    """An explicit environment value wins, including an empty value that fails closed."""
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
        raise UsageError("NAME: expected an uppercase environment variable name")
    if name in os.environ:
        value = os.environ[name]
        if not value or any(character in value for character in "\x00\r\n"):
            raise DotError(f"{name}: credential is empty or contains a line break; no personal fallback was used")
        return value
    path = Path.home() / ".config/dot/secrets" / name
    try:
        # Do not follow links or block on FIFOs; verify the opened inode before reading.
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise DotError(f"{name}: personal secret must be an owner-only regular file (chmod 600)")
            raw = stream.read(_MAX_SECRET_BYTES + 1)
            if len(raw) > _MAX_SECRET_BYTES:
                raise DotError(f"{name}: personal secret exceeds 64 KiB")
            value = raw.decode("utf-8").rstrip("\r\n")
    except (OSError, UnicodeError) as error:
        raise DotError(f"{name}: cannot read personal secret; configure ~/.config/dot/secrets/{name}") from error
    if not value or any(character in value for character in "\x00\r\n"):
        raise DotError(f"{name}: personal secret is empty or contains a line break")
    return value


def _run(state: State, args: argparse.Namespace) -> None:
    name, command = args.name, args.command
    # Packages publish through PyPI Trusted Publishing; a long-lived personal upload token is retired.
    if name == "UV_PUBLISH_TOKEN":
        raise UsageError("NAME: PyPI publishing uses Trusted Publishing, not a personal token")
    require_tools(state, [command])
    code = state.runner.interactive(
        command,
        env={name: personal_token(name)},
        stdin=state.stdin,
        stdout=state.stdout,
        stderr=state.stderr,
    )
    raise SystemExit(code if code >= 0 else 128 - code)


def register(commands: Parser) -> None:
    group = commands.group("secret", "Use personal credentials for one command without exporting them globally")
    # Scoped credentials never read dot.yaml, so an invalid configuration cannot block them.
    run = group.command(
        "run",
        "Supply NAME to COMMAND; an existing environment value wins",
        _run,
        config=False,
        epilog="Example: dot secret run OPENROUTER_MANAGEMENT_KEY -- python app.py. "
        "Exits with COMMAND's status; the value is never printed or exported to the shell.",
    )
    run.add_argument("name", metavar="NAME", help="Variable stored in ~/.config/dot/secrets/NAME")
    run.add_argument("command", nargs="+", metavar="COMMAND", help="Command and arguments, following --")
