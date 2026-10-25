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
    guide = {"python-stack": "foundation", "cli-development": "typer", "python-web": "litestar"}[owner]
    content = (ROOT / "skills" / owner / "references" / guide / "templates" / name).read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    unresolved = {
        match.group() for match in re.finditer(r"<(?:slug|package|description|holder|python_major_minor)>", content)
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
    # An inherited UV_PROJECT would redirect uv; a generated project must resolve itself.
    environment.pop("UV_PROJECT", None)
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("COVERAGE_FILE", None)
    # Typer forces a terminal whenever GITHUB_ACTIONS, FORCE_COLOR or PY_COLORS is set,
    # and NO_COLOR does not undo it. Rich then splits option names across escape
    # sequences ("--name" becomes "\x1b[1m-\x1b[0m\x1b[1m-name"), so help assertions
    # only hold once every forcing variable is removed.
    for forced in ("CLICOLOR_FORCE", "FORCE_COLOR", "GITHUB_ACTIONS", "PY_COLORS"):
        environment.pop(forced, None)
    result = subprocess.run(
        list(command),
        cwd=str(root),
        env=environment,
        capture_output=True,
        text=True,
        # Resolution and installs use the network; a stalled download must fail this test.
        timeout=600,
    )
    assert result.returncode == expected_code, f"{' '.join(command)} failed:\n{result.stdout}{result.stderr}"
    return result.stdout


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
@pytest.mark.parametrize("profile", ["library", "cli", "web"])
def test_python_starter_install_check_test_build_and_entrypoint(tmp_path: Path, profile: str) -> None:
    # HOME is tmp_path, so uv and Ruff caches must stay outside the generated project.
    project = tmp_path / "starter"
    project.mkdir()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    replacements = {
        "<slug>": "starter-py",
        "<package>": "starter_py",
        "<description>": "Starter command line application",
        "<holder>": "Fixture Author",
        "<python_major_minor>": version,
    }
    manifest = _render("pyproject.toml.template", replacements)
    parsed = tomllib.loads(manifest)
    assert parsed["project"]["dependencies"] == []
    assert "scripts" not in parsed["project"]
    if profile != "library":
        manifest += '\n[project.scripts]\nstarter-py = "starter_py:main"\n'

    _write(project, "pyproject.toml", manifest)
    _write(project, ".python-version", f"{version}\n")
    _write(project, "README.md", "# Starter Python\n")
    _write(project, "LICENSE", "MIT\n")
    # Match bootstrap order: uv add builds the existing foundation before the profile replaces it.
    _write(project, "src/starter_py/__init__.py", _render("init-library.py", replacements))
    if profile == "library":
        _write(project, "tests/test_library.py", _render("test_library.py", replacements))
    elif profile == "cli":
        _run(project, "uv", "add", "typer>=0.27.2")
        _write(project, "src/starter_py/__init__.py", _render("init-cli.py", replacements, owner="cli-development"))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, owner="cli-development"))
        for name in ("test_smoke.py", "test_cli.py"):
            _write(project, f"tests/{name}", _render(name, replacements, owner="cli-development"))
    else:
        # Mirrors the guide's temporary pin: multidict 7.2.0 breaks litestar 2.25.0 Headers.
        with (project / "pyproject.toml").open("a", encoding="utf-8") as stream:
            stream.write('\n[tool.uv]\nconstraint-dependencies = ["multidict<7.2"]\n')
        _run(
            project,
            "uv",
            "add",
            "litestar>=2.24.0",
            "granian[reload,uvloop]>=2.8.1",
            "sqlalchemy[asyncio]>=2.0.52",
            "asyncpg>=0.31.0",
            "pydantic>=2.13.4",
            "pydantic-settings>=2.15.0",
            "structlog>=26.1.0",
        )
        _run(project, "uv", "add", "--dev", "anyio>=4.14.2", "testcontainers>=4.15.0")
        _write(
            project,
            "src/starter_py/__init__.py",
            _render("init.py", replacements, owner="python-web"),
        )
        _write(project, "src/starter_py/__main__.py", 'from . import main\n\nif __name__ == "__main__":\n    main()\n')
        for name in ("test_web.py", "test_integration.py"):
            _write(project, f"tests/{name}", _render(name, replacements, owner="python-web"))
        _write(project, "tests/conftest.py", _render("conftest.py", replacements, owner="python-web"))
        # SQLAlchemy loads asyncpg from the URL scheme, so the guide declares it for deptry.
        with (project / "pyproject.toml").open("a", encoding="utf-8") as stream:
            stream.write('\n[tool.deptry.per_rule_ignores]\nDEP002 = ["asyncpg"]\n')
        _write(project, ".env", _render("env.example", replacements, owner="python-web"))

    _run(project, "uv", "lock")
    _run(project, "uv", "sync", "--locked")
    _run(project, "uv", "run", "--frozen", "validate-pyproject", "pyproject.toml")
    # The documented gate formats materialized code for the selected Python target first.
    _run(project, "uv", "run", "--frozen", "ruff", "format")
    _run(project, "uv", "run", "--frozen", "ruff", "check")
    _run(project, "uv", "run", "--frozen", "ruff", "format", "--check")
    _run(project, "uv", "run", "--frozen", "ty", "check")
    _run(project, "uv", "run", "--frozen", "deptry", ".")
    _run(project, "uv", "run", "--frozen", "pytest", "-m", "not integration", "--cov", "--cov-fail-under=85")
    _run(project, "uv", "build", "--out-dir", "dist")
    # The strict docs build renders every module's API page and fails on broken cross-references.
    _write(project, "zensical.toml", _render("zensical.toml", replacements))
    _write(project, "docs/index.md", _render("docs-index.md", replacements))
    _run(project, "uv", "run", "--frozen", "zensical", "build", "--clean", "--strict")
    assert (project / "site/reference/starter_py/index.html").is_file()

    runtime = project / "runtime"
    _run(project, "uv", "venv", str(runtime))
    wheel = next((project / "dist").glob("*.whl"))
    requirements = _run(project, "uv", "export", "--locked", "--no-dev", "--no-emit-project")
    _write(project, "runtime-requirements.txt", requirements)
    _run(
        project,
        "uv",
        "pip",
        "install",
        "--python",
        str(runtime / "bin/python"),
        "-r",
        "runtime-requirements.txt",
        str(wheel),
    )
    outside = project / "outside"
    outside.mkdir()
    if profile == "web":
        _write(outside, ".env", _render("env.example", replacements, owner="python-web"))
    assert (
        _run(outside, str(runtime / "bin/python"), "-c", "import starter_py; print(starter_py.__version__)")
        == "0.1.0\n"
    )
    if profile == "cli":
        for command in ([str(runtime / "bin/starter-py")], [str(runtime / "bin/python"), "-m", "starter_py"]):
            assert _run(outside, *command, "greet", "--name", "Ada") == "Hello, Ada!\n"
            assert _run(outside, *command, "--version") == "0.1.0\n"
            for flag in ("-h", "--help"):
                assert "greet" in _run(outside, *command, flag)
                assert "--name" in _run(outside, *command, "greet", flag)
            _run(outside, *command, "--unknown-option", expected_code=2)
        for shell in ("bash", "zsh", "fish"):
            result = subprocess.run(
                [str(runtime / "bin/starter-py")],
                cwd=outside,
                env={**os.environ, "_STARTER_PY_COMPLETE": f"source_{shell}"},
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            assert "starter-py" in result.stdout
            if shell == "bash" and "Bash versions older than 4.4" in result.stderr:
                continue
            assert result.stderr == ""
