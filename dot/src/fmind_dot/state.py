"""Runtime dependencies shared by command modules."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from fmind_dot.config import Config, ConfigValidationError, config_file_path, load_config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner


@dataclass
class State:
    """Lazily load configuration so diagnostic/config commands work cleanly."""

    config_argument: Path | None = None
    runner: Runner = field(default_factory=Runner)
    stdin: IO[str] = field(default_factory=lambda: sys.stdin)
    stdout: IO[str] = field(default_factory=lambda: sys.stdout)
    stderr: IO[str] = field(default_factory=lambda: sys.stderr)
    _config: Config | None = field(default=None, init=False, repr=False)
    _probes: dict[tuple[str, ...], CommandResult | DotError] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def config(self) -> Config:
        if self._config is not None:
            return self._config
        with self._lock:
            if self._config is None:
                self._config = validated_config(self.config_argument)
            return self._config

    def run_probe(self, key: tuple[str, ...], execute: Callable[[], CommandResult]) -> CommandResult:
        """Reuse readiness probe outcomes within one invocation; logins invalidate cached results."""
        with self._lock:
            cached = self._probes.get(key)
        if cached is not None:
            if isinstance(cached, DotError):
                raise cached
            return cached
        try:
            result = execute()
        except DotError as error:
            with self._lock:
                self._probes[key] = error
            raise
        with self._lock:
            self._probes[key] = result
        return result

    def clear_probes(self) -> None:
        """Discard cached probe results after an authentication state change."""
        with self._lock:
            self._probes.clear()


def validated_config(path: Path | None) -> Config:
    """Load configuration, naming the file when validation fails."""
    resolved = config_file_path(path)[0]
    try:
        return load_config(path)
    except ConfigValidationError as error:
        raise DotError(f"invalid config file at {resolved} (validation error): {error}; fix {resolved}") from error


def require_tools(state: State, commands: list[list[str]]) -> None:
    """Fail closed with one actionable message listing every missing executable."""
    missing = sorted({args[0] for args in commands if state.runner.which(args[0]) is None})
    if missing:
        raise DotError(f"required tools are missing: {', '.join(missing)}; install them with mise and retry")
