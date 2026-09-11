from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _render(name: str, replacements: dict[str, str], *, owner: str = "python-stack") -> str:
    content = (ROOT / "skills" / owner / "references" / name).read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    unresolved = {
        match.group()
        for match in re.finditer(r"<(?:slug|package|description|holder|latest_stable_version_major_minor)>", content)
    }
    assert unresolved == set(), f"{name} retains placeholders: {sorted(unresolved)}"
    return content


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run(root: Path, *command: str, expected_code: int = 0) -> str:
    environment: dict[str, str] = {
        **os.environ,
        "CI": "1",
        "NO_COLOR": "1",
        "UV_NO_PROGRESS": "1",
        "UV_PYTHON": sys.executable or "python",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    # The dot repository exports UV_PROJECT; a generated project must resolve itself.
    environment.pop("UV_PROJECT", None)
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("COVERAGE_FILE", None)
    # Rich lets a forced-color variable override NO_COLOR, and it then splits option
    # names across escape sequences ("--name" becomes "\x1b[1m-\x1b[0m\x1b[1m-name"),
    # so help assertions only hold once the CI runner's forcing is removed.
    for forced in ("CLICOLOR_FORCE", "FORCE_COLOR"):
        environment.pop(forced, None)
    result = subprocess.run(
        list(command),
        cwd=str(root),
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected_code, f"{' '.join(command)} failed:\n{result.stdout}{result.stderr}"
    return result.stdout


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
@pytest.mark.parametrize("profile", ["library", "cli", "web"])
def test_python_starter_install_check_test_build_and_entrypoint(tmp_path: Path, profile: str) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    replacements = {
        "<slug>": "starter-py",
        "<package>": "starter_py",
        "<description>": "Starter command line application",
        "<holder>": "Fixture Author",
        "<latest_stable_version_major_minor>": version,
    }
    manifest = _render("pyproject.toml.template", replacements)
    parsed = tomllib.loads(manifest)
    assert parsed["project"]["dependencies"] == []
    assert "scripts" not in parsed["project"]
    if profile != "library":
        manifest += '\n[project.scripts]\nstarter-py = "starter_py:main"\n'

    _write(tmp_path, "pyproject.toml", manifest)
    _write(tmp_path, ".python-version", f"{version}\n")
    _write(tmp_path, "README.md", "# Starter Python\n")
    _write(tmp_path, "LICENSE", "MIT\n")
    # Match bootstrap order: uv add builds the existing foundation before the profile replaces it.
    _write(tmp_path, "src/starter_py/__init__.py", _render("init-library.py", replacements))
    if profile == "library":
        _write(tmp_path, "tests/test_library.py", _render("test_library.py", replacements))
    elif profile == "cli":
        _run(tmp_path, "uv", "add", "typer>=0.27.2")
        _write(tmp_path, "src/starter_py/__init__.py", _render("init-cli.py", replacements, owner="typer"))
        _write(tmp_path, "src/starter_py/__main__.py", _render("main.py", replacements, owner="typer"))
        for name in ("test_smoke.py", "test_cli.py"):
            _write(tmp_path, f"tests/{name}", _render(name, replacements, owner="typer"))
    else:
        _run(
            tmp_path,
            "uv",
            "add",
            "litestar>=2.24.0",
            "granian[reload,uvloop]>=2.8.1",
            "sqlalchemy>=2.0.52",
            "asyncpg>=0.31.0",
            "pydantic>=2.13.4",
            "pydantic-settings>=2.15.0",
            "structlog>=26.1.0",
        )
        _run(tmp_path, "uv", "add", "--dev", "anyio>=4.14.2", "testcontainers>=4.15.0")
        _write(tmp_path, "src/starter_py/__init__.py", _render("init.py", replacements, owner="litestar"))
        _write(tmp_path, "src/starter_py/__main__.py", 'from . import main\n\nif __name__ == "__main__":\n    main()\n')
        for name in ("test_web.py", "test_integration.py"):
            _write(tmp_path, f"tests/{name}", _render(name, replacements, owner="litestar"))
        _write(tmp_path, "conftest.py", _render("conftest.py", replacements, owner="litestar"))
        _write(tmp_path, ".env", _render("env.example", replacements, owner="litestar"))

    _run(tmp_path, "uv", "lock")
    _run(tmp_path, "uv", "sync", "--locked")
    _run(tmp_path, "uv", "run", "--frozen", "validate-pyproject", "pyproject.toml")
    # The documented gate formats materialized code for the selected Python target first.
    _run(tmp_path, "uv", "run", "--frozen", "ruff", "format")
    _run(tmp_path, "uv", "run", "--frozen", "ruff", "check")
    _run(tmp_path, "uv", "run", "--frozen", "ruff", "format", "--check")
    _run(tmp_path, "uv", "run", "--frozen", "ty", "check")
    _run(tmp_path, "uv", "run", "--frozen", "pytest", "-m", "not integration", "--cov", "--cov-fail-under=85")
    _run(tmp_path, "uv", "build", "--out-dir", "dist")

    runtime = tmp_path / "runtime"
    _run(tmp_path, "uv", "venv", str(runtime))
    wheel = next((tmp_path / "dist").glob("*.whl"))
    requirements = _run(tmp_path, "uv", "export", "--locked", "--no-dev", "--no-emit-project")
    _write(tmp_path, "runtime-requirements.txt", requirements)
    _run(
        tmp_path,
        "uv",
        "pip",
        "install",
        "--python",
        str(runtime / "bin/python"),
        "-r",
        "runtime-requirements.txt",
        str(wheel),
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    if profile == "web":
        _write(outside, ".env", _render("env.example", replacements, owner="litestar"))
    assert (
        _run(outside, str(runtime / "bin/python"), "-c", "import starter_py; print(starter_py.__version__)")
        == "0.1.0\n"
    )
    if profile == "cli":
        for command in ([str(runtime / "bin/starter-py")], [str(runtime / "bin/python"), "-m", "starter_py"]):
            assert _run(outside, *command, "--name", "Ada") == "Hello, Ada!\n"
            assert "--name" in _run(outside, *command, "--help")
            _run(outside, *command, "--unknown-option", expected_code=2)
