"""Shared failures with safe, user-facing messages."""


class DotError(RuntimeError):
    """A failure that can be printed without exposing command output or secrets."""
