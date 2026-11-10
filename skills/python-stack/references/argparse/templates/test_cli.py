from __future__ import annotations

import sys

import pytest

from <package> import __version__, main


@pytest.fixture(autouse=True)
def plain_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    # argparse colors help and errors whenever a terminal or CI forces color.
    monkeypatch.setenv("NO_COLOR", "1")
    for key in ("FORCE_COLOR", "PYTHON_COLORS"):
        monkeypatch.delenv(key, raising=False)


def run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    """Run the CLI in-process and return its exit code, stdout, and stderr."""
    code = 0
    try:
        main(args)
    except SystemExit as stopped:
        code = stopped.code if isinstance(stopped.code, int) else int(stopped.code is not None)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_greet(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "greet", "--name", "Ada") == (0, "Hello, Ada!\n", "")


@pytest.mark.parametrize("command", [[], ["greet"]])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help(capsys: pytest.CaptureFixture[str], command: list[str], flag: str) -> None:
    code, out, err = run(capsys, *command, flag)
    assert code == 0
    assert out.startswith("usage: <slug>")
    assert "\x1b[" not in out
    assert err == ""


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "--version") == (0, f"{__version__}\n", "")


@pytest.mark.parametrize("args", [[], ["--unknown-option"], ["greet", "--name"], ["gret"], ["greet", "--nam", "Ada"]])
def test_usage_errors(capsys: pytest.CaptureFixture[str], args: list[str]) -> None:
    code, out, err = run(capsys, *args)
    assert code == 2
    assert out == ""
    assert err.startswith("usage: <slug>")
    assert "Traceback" not in err


def test_console_entrypoint(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["<slug>", "greet", "--name", "Ada"])

    main()

    captured = capsys.readouterr()
    assert captured.out == "Hello, Ada!\n"
    assert captured.err == ""
