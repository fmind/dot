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
class _InFlightProbe:
    done: threading.Event = field(default_factory=threading.Event)
    outcome: CommandResult | DotError | None = None


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
    _in_flight_probes: dict[tuple[str, ...], _InFlightProbe] = field(default_factory=dict, init=False, repr=False)
    _probe_generation: int = field(default=0, init=False, repr=False)

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
        """Run each distinct readiness probe once across concurrent callers; logins invalidate cached results."""
        with self._lock:
            cached = self._probes.get(key)
            if cached is not None:
                if isinstance(cached, DotError):
                    raise cached
                return cached
            waiter = self._in_flight_probes.get(key)
            leader = waiter is None
            if waiter is None:
                waiter = _InFlightProbe()
                self._in_flight_probes[key] = waiter
            generation = self._probe_generation
        if not leader:
            waiter.done.wait()
            if isinstance(waiter.outcome, DotError):
                raise waiter.outcome
            if waiter.outcome is not None:
                return waiter.outcome
            return self.run_probe(key, execute)
        outcome: CommandResult | DotError | None = None
        try:
            result = execute()
            outcome = result
            return result
        except DotError as error:
            # Reuse timeouts and missing-tool errors too: sequential steps after warm_probes must not wait again.
            outcome = error
            raise
        finally:
            with self._lock:
                if self._in_flight_probes.get(key) is waiter:
                    self._in_flight_probes.pop(key, None)
                waiter.outcome = outcome
                if outcome is not None and self._probe_generation == generation:
                    self._probes[key] = outcome
                waiter.done.set()

    def clear_probes(self) -> None:
        """Discard cached probe results and prevent earlier in-flight probes from repopulating them."""
        with self._lock:
            self._probe_generation += 1
            self._in_flight_probes.clear()
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
