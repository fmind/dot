from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "skills/cli-development/references/typer/templates"
SCRIPT = ROOT / "skills/python-stack/references/python-script/templates/script.py"


def _invoke(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment: dict[str, str] = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
    for key in ("CLICOLOR_FORCE", "FORCE_COLOR", "GITHUB_ACTIONS", "PY_COLORS"):
        environment.pop(key, None)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=script.parent,
        env=environment,
        input="",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize("template", ["packaged", "script"])
@pytest.mark.parametrize("flag", ["-h", "--help", "--version"])
def test_cli_template_information_without_inputs(tmp_path: Path, template: str, flag: str) -> None:
    source = (
        (TEMPLATES / "init-cli.py").read_text() + '\nif __name__ == "__main__":\n    main()\n'
        if template == "packaged"
        else SCRIPT.read_text()
    )
    script = tmp_path / "cli.py"
    script.write_text(source.replace("<description>", "Fixture CLI").replace("<slug>", "fixture-cli"))
    result = _invoke(script, flag)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
    assert result.stderr == ""
    assert "\x1b[" not in result.stdout


def test_packaged_command_survives_a_second_command(tmp_path: Path) -> None:
    source = (TEMPLATES / "init-cli.py").read_text()
    script = tmp_path / "cli.py"
    script.write_text(source + '\nif __name__ == "__main__":\n    main()\n')
    before = _invoke(script, "greet", "--name", "Ada")
    script.write_text(source + '\n@app.command()\ndef farewell() -> None:\n    typer.echo("Goodbye")\n\nmain()\n')
    after = _invoke(script, "greet", "--name", "Ada")
    assert before.returncode == after.returncode == 0
    assert before.stdout == after.stdout == "Hello, Ada!\n"
    assert before.stderr == after.stderr == ""


@pytest.mark.parametrize("name", ["report[red].txt", "report[/].txt", "report:smile:.txt"])
def test_script_paths_are_literal(tmp_path: Path, name: str) -> None:
    script = tmp_path / "cli.py"
    script.write_text(SCRIPT.read_text())
    input_file = tmp_path / name
    input_file.parent.mkdir(parents=True, exist_ok=True)
    input_file.touch()
    result = _invoke(script, name, "--verbose")
    assert result.returncode == 0, result.stderr
    assert name in result.stdout
    assert name in result.stderr
    assert "\x1b[" not in result.stdout + result.stderr


@pytest.mark.parametrize("error", ["PermissionError", "RuntimeError"])
@pytest.mark.parametrize("verbose", [False, True])
def test_script_errors_do_not_disclose_exception_values(tmp_path: Path, error: str, verbose: bool) -> None:
    source = SCRIPT.read_text()
    placeholder = "# ... do the real work here ..."
    assert source.count(placeholder) == 1
    # Exercise the template's error boundary with a failing application operation.
    source = source.replace(placeholder, f'raise {error}("SYNTHETIC_CREDENTIAL_MARKER")')
    script = tmp_path / "cli.py"
    script.write_text(source)
    (tmp_path / "input.txt").touch()
    result = _invoke(script, "input.txt", *(["--verbose"] if verbose else []))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Error:" in result.stderr
    assert "SYNTHETIC_CREDENTIAL_MARKER" not in result.stderr
    assert "Traceback" not in result.stderr
