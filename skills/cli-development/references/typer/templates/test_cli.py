from __future__ import annotations

import os
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from <package> import __version__, app, main

runner = CliRunner()


@pytest.fixture(autouse=True)
def plain_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")
    for key in ("CLICOLOR_FORCE", "FORCE_COLOR", "GITHUB_ACTIONS", "PY_COLORS"):
        monkeypatch.delenv(key, raising=False)


def test_greet() -> None:
    result = runner.invoke(app, ["greet", "--name", "Ada"])

    assert result.exit_code == 0
    assert result.stdout == "Hello, Ada!\n"
    assert result.stderr == ""


@pytest.mark.parametrize("command", [[], ["greet"]])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help(command: list[str], flag: str) -> None:
    result = runner.invoke(app, [*command, flag])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "\x1b[" not in result.stdout
    assert result.stderr == ""


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == f"{__version__}\n"
    assert result.stderr == ""


def test_empty_group_shows_help() -> None:
    # Typer's implicit help goes to stdout but retains a usage-error status.
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage:" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize("args", [["--unknown-option"], ["greet", "--name"]])
def test_usage_errors(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_in_fresh_process(shell: str) -> None:
    complete_var = "_<slug>_COMPLETE".replace("-", "_").upper()
    result = subprocess.run(
        [sys.executable, "-c", "from <package> import app; app(prog_name='<slug>')"],
        env={**os.environ, complete_var: f"source_{shell}"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "<slug>" in result.stdout
    assert result.stderr == ""


def test_console_entrypoint(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["<slug>", "greet", "--name", "Ada"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == "Hello, Ada!\n"
    assert captured.err == ""
