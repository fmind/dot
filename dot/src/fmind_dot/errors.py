"""Shared failures and broken-pipe exit helpers with safe, user-facing messages."""

import contextlib
import os
import sys
from typing import Never


class DotError(RuntimeError):
    """A failure that can be printed without exposing command output or secrets."""


class CommandTimeoutError(DotError):
    """A bounded command exceeded its deadline and was terminated."""


class NotGitWorkTreeError(DotError):
    """A path that git does not place inside any work tree."""


class UsageError(Exception):
    """Arguments that parse but cannot be combined or resolved; the CLI reports them with exit status 2."""


def suppress_broken_pipe_stdout() -> Never:
    """Redirect broken stdout to /dev/null and exit 141 without shutdown noise."""
    with contextlib.suppress(AttributeError, OSError, ValueError):
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)
    raise SystemExit(141) from None


def flush_stdout_on_error() -> None:
    """Flush stdout before error reporting so closed pipes exit 141 cleanly."""
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        suppress_broken_pipe_stdout()
