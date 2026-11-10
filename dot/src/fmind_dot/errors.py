"""Shared failures with safe, user-facing messages."""


class DotError(RuntimeError):
    """A failure that can be printed without exposing command output or secrets."""


class CommandTimeoutError(DotError):
    """A bounded command exceeded its deadline and was terminated."""


class NotGitWorkTreeError(DotError):
    """A path that git does not place inside any work tree."""


class UsageError(Exception):
    """Arguments that parse but cannot be combined or resolved; the CLI reports them with exit status 2."""


class CancelledError(Exception):
    """The user declined a confirmation or closed the prompt; the CLI reports it with exit status 1."""
