"""Shared runner and state fakes for CLI tests that must never touch the workstation."""

from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from fmind_dot.system import CheckResult

RunHandler = Callable[[list[str], Path | None, str | None, bool], CommandResult]


@dataclass
class CliResult:
    """What one in-process CLI invocation printed and how it ended."""

    exit_code: int
    stdout: str
    stderr: str
    exception: Exception | None = None

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class CliRunner:
    """Run `fmind_dot.cli.app` in-process with captured streams."""

    def invoke(
        self, app: Callable[[Sequence[str]], None], arguments: Sequence[str] = (), *, stdin: str = ""
    ) -> CliResult:
        stdout, stderr, previous = io.StringIO(), io.StringIO(), sys.stdin
        exit_code, exception = 0, None
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                app(list(arguments))
        except SystemExit as stopped:
            exit_code = stopped.code if isinstance(stopped.code, int) else int(stopped.code is not None)
        except Exception as error:  # noqa: BLE001 - mirror entry point: every failure becomes exit code 1
            exit_code, exception = 1, error
        finally:
            sys.stdin = previous
        return CliResult(exit_code, stdout.getvalue(), stderr.getvalue(), exception)


class TerminalIO(io.StringIO):
    """StringIO that reports itself as a terminal."""

    def isatty(self) -> bool:
        return True


class ScriptedRunner(Runner):
    def __init__(
        self,
        installed: set[str] | None = None,
        *,
        run: RunHandler | None = None,
        responses: Mapping[tuple[str, ...], Sequence[CommandResult]] | None = None,
    ) -> None:
        super().__init__()
        self.installed, self.run_handler = installed or set(), run
        self.responses = {key: list(items) for key, items in (responses or {}).items()}
        self.calls: list[list[str]] = []
        self.envs: dict[tuple[str, ...], Mapping[str, str] | None] = {}
        self.interactive_envs: list[Mapping[str, str] | None] = []
        self.timeouts: dict[tuple[str, ...], float | None] = {}

    def which(self, command: str) -> Path | None:
        return Path("/bin") / command if command in self.installed else None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        command = list(args)
        key = tuple(command)
        self.calls.append(command)
        self.envs[key], self.timeouts[key] = env, timeout
        if self.run_handler is not None:
            result = self.run_handler(command, cwd, input_text, check)
        elif key in self.responses:
            result = self.responses[key].pop(0)
        else:
            result = CommandResult("ok\n", "", 0)
        if check and result.returncode != 0:
            raise DotError(f"command failed ({result.returncode}): {command[0]}")
        return result

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        open_url: Any = None,
    ) -> int:
        del cwd, stdin, stdout, stderr, open_url
        self.calls.append(list(args))
        self.interactive_envs.append(env)
        return 0


def doctor_sections(results: Sequence[CheckResult]) -> dict[str, Any]:
    """Group doctor checks by section, plus overall verdict."""
    sections: dict[str, Any] = {}
    for item in results:
        sections.setdefault(item.group, []).append({k: v for k, v in item.payload().items() if k != "group"})
    return sections | {"passed": all(item.status != "fail" for item in results)}


def buf(stream: IO[str]) -> str:
    """Return captured text from a StringIO stream."""
    assert isinstance(stream, io.StringIO)
    return stream.getvalue()


def make_state(runner: Runner | None = None, config: Config | None = None, *, stdin: str = "") -> State:
    """A State with captured streams and an injected configuration."""
    state = State(runner=runner or Runner(), stdin=io.StringIO(stdin), stdout=io.StringIO(), stderr=io.StringIO())
    state.__dict__["_config"] = config or Config()
    return state
