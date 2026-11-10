"""Shared runner and state fakes for CLI tests that must never touch the workstation."""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
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
    """Run `fmind_dot.cli.app` in-process with captured streams.

    A failure `cli.main` would report as `dot: <error>` stays on `exception` with exit code 1,
    so tests assert on the error itself; `main` has its own reporting tests.
    """

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
        except Exception as error:  # noqa: BLE001 - mirror the entry point: every failure becomes exit code 1
            exit_code, exception = 1, error
        finally:
            sys.stdin = previous
        return CliResult(exit_code, stdout.getvalue(), stderr.getvalue(), exception)


ROOT = Path(__file__).resolve().parents[2]
_REAL_HOME = os.environ.get("HOME")


def native_binary(name: str) -> Path | None:
    """Resolve a command, unwrapping a mise shim against the real HOME before isolated_home replaces it."""
    executable = shutil.which(name)
    if not executable:
        return None
    resolved = Path(executable).resolve()
    if resolved.name != "mise":
        return Path(executable)
    env = os.environ | ({"HOME": _REAL_HOME} if _REAL_HOME else {})
    try:
        result = subprocess.run(
            [str(resolved), "which", name], env=env, capture_output=True, text=True, timeout=30, check=True
        )
    except subprocess.CalledProcessError, subprocess.TimeoutExpired:
        return None
    candidate = Path(result.stdout.strip())
    return candidate if candidate.is_absolute() and candidate.is_file() else None


# Repository workflows and shipped workflow templates.
WORKFLOWS = [
    *sorted((ROOT / ".github/workflows").glob("*.yml")),
    *sorted((ROOT / "skills/github-actions/references/ci-cd/templates").glob("*.yml")),
    ROOT / "skills/cloud-run/templates/deploy.yml",
    ROOT / "skills/documentation-site/templates/docs.yml",
]
# The Copilot session database tables the parser reads.
COPILOT_SCHEMA = """
CREATE TABLE sessions(id TEXT, cwd TEXT, created_at TEXT);
CREATE TABLE turns(id INTEGER, session_id TEXT, turn_index INTEGER, user_message TEXT, assistant_response TEXT, timestamp TEXT);
CREATE TABLE assistant_usage_events(session_id TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER);
"""


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
    ) -> None:
        super().__init__()
        self.installed = installed or set()
        self.run_handler = run
        self.calls: list[list[str]] = []
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
        del env
        command = list(args)
        self.calls.append(command)
        self.timeouts[tuple(command)] = timeout
        result = self.run_handler(command, cwd, input_text, check) if self.run_handler else CommandResult("ok\n", "", 0)
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
        on_stderr_line: Callable[[str], None] | None = None,
    ) -> int:
        # Never launch a real process from a test.
        del args, cwd, stdin, stdout, stderr, env, on_stderr_line
        return 0


def doctor_sections(results: Sequence[CheckResult]) -> dict[str, Any]:
    """Group doctor checks by section, as the text report renders them, plus the overall verdict."""
    sections: dict[str, Any] = {}
    for item in results:
        sections.setdefault(item.group, []).append(
            {key: value for key, value in item.payload().items() if key != "group"}
        )
    return sections | {"passed": all(item.status != "fail" for item in results)}


def make_state(runner: Runner | None = None, config: Config | None = None, *, stdin: str = "") -> State:
    """A State with captured streams and an injected configuration."""
    state = State(runner=runner or Runner(), stdin=io.StringIO(stdin), stdout=io.StringIO(), stderr=io.StringIO())
    state.__dict__["_config"] = config or Config()
    return state
