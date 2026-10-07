"""Shared scripted command runner for CLI tests that must never touch the workstation."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO, Any

from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.system import CheckResult

RunHandler = Callable[[list[str], Path | None, str | None, bool], CommandResult]


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
        del env, timeout
        command = list(args)
        self.calls.append(command)
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
