"""Runtime dependencies shared by command modules."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from pydantic import ValidationError

from fmind_dot.config import Config, config_file_path, load_config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner


@dataclass
class State:
    """Lazily load configuration so repair commands can bypass invalid YAML."""

    config_argument: Path | None = None
    runner: Runner = field(default_factory=Runner)
    # Resolve standard streams at invocation time so test capture and callers
    # that redirect streams observe the same process state as the command.
    stdin: IO[str] = field(default_factory=lambda: sys.stdin)
    stdout: IO[str] = field(default_factory=lambda: sys.stdout)
    stderr: IO[str] = field(default_factory=lambda: sys.stderr)
    _config: Config | None = field(default=None, init=False, repr=False)
    # Readiness probe results reused within one invocation; every login clears them.
    _probes: dict[tuple[str, ...], CommandResult | DotError] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def config_path(self) -> Path:
        return config_file_path(self.config_argument)[0]

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
            # Reuse timeouts and missing-tool errors too: sequential steps after warm_probes must not wait again.
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
    """Load configuration, naming the file and the repair command when validation fails."""
    try:
        return load_config(path)
    except ValidationError as error:
        # Locations and messages only: input values could hold credentials.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc']) or '<root>'}: {item['msg']}"
            for item in error.errors(include_url=False, include_input=False, include_context=False)
        )
        raise DotError(
            f"invalid config file at {config_file_path(path)[0]} ({error.error_count()} validation error(s)): "
            f"{problems}; fix it with: dot config edit"
        ) from error


def require_tools(state: State, commands: list[list[str]]) -> None:
    """Fail closed with one actionable message listing every missing executable."""
    missing = sorted({args[0] for args in commands if state.runner.which(args[0]) is None})
    if missing:
        raise DotError(f"required tools are missing: {', '.join(missing)}; install them with mise and retry")
