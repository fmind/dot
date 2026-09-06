"""Runtime dependencies shared by command modules."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from fmind_dot.config import Config, config_file_path, load_config
from fmind_dot.process import Runner


@dataclass
class State:
    """Lazily load configuration so repair commands can bypass invalid YAML."""

    config_argument: Path | None = None
    verbose: bool = False
    runner: Runner = field(default_factory=Runner)
    # Resolve standard streams at invocation time so Typer/test capture and callers
    # that redirect streams observe the same process state as the command.
    stdin: IO[str] = field(default_factory=lambda: sys.stdin)
    stdout: IO[str] = field(default_factory=lambda: sys.stdout)
    stderr: IO[str] = field(default_factory=lambda: sys.stderr)
    _config: Config | None = field(default=None, init=False, repr=False)

    @property
    def config_path(self) -> Path:
        return config_file_path(self.config_argument)[0]

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = load_config(self.config_argument)
        return self._config
