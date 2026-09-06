from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "skills/python-stack/references"


def _render(name: str, replacements: dict[str, str]) -> str:
    content = (TEMPLATES / name).read_text(encoding="utf-8")
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


def _run(root: Path, *command: str) -> str:
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
    result = subprocess.run(
        list(command),
        cwd=str(root),
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{' '.join(command)} failed:\n{result.stdout}{result.stderr}"
    return result.stdout


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_python_cli_starter_install_check_test_build_and_entrypoint(tmp_path: Path) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    replacements = {
        "<slug>": "starter-py",
        "<package>": "starter_py",
        "<description>": "Starter command line application",
        "<holder>": "Fixture Author",
        "<latest_stable_version_major_minor>": version,
    }
    manifest = _render("pyproject.toml.template", replacements)
    manifest = re.sub(
        r"dependencies = \[.*?\]\n\n\[dependency-groups\]",
        'dependencies = ["typer>=0.27.2"]\n\n[dependency-groups]',
        manifest,
        count=1,
        flags=re.DOTALL,
    )
    manifest = re.sub(r'^.*"testcontainers\[postgres\].*\n', "", manifest, count=1, flags=re.MULTILINE)

    _write(tmp_path, "pyproject.toml", manifest)
    _write(tmp_path, ".python-version", f"{version}\n")
    _write(tmp_path, "README.md", "# Starter Python\n")
    _write(tmp_path, "LICENSE", "MIT\n")
    _write(tmp_path, "src/starter_py/__init__.py", _render("init-cli.py", replacements))
    _write(tmp_path, "src/starter_py/__main__.py", _render("main.py", replacements))
    _write(tmp_path, "tests/test_smoke.py", _render("test_smoke.py", replacements))
    _write(tmp_path, "tests/test_cli.py", _render("test_cli.py", replacements))

    _run(tmp_path, "uv", "lock")
    _run(tmp_path, "uv", "sync", "--locked")
    _run(tmp_path, "uv", "run", "--frozen", "validate-pyproject", "pyproject.toml")
    _run(tmp_path, "uv", "run", "--frozen", "ruff", "check")
    _run(tmp_path, "uv", "run", "--frozen", "ruff", "format", "--check")
    _run(tmp_path, "uv", "run", "--frozen", "ty", "check")
    _run(tmp_path, "uv", "run", "--frozen", "pytest", "--cov", "--cov-fail-under=85")
    _run(tmp_path, "uv", "build", "--out-dir", "dist")

    runtime = tmp_path / "runtime"
    _run(tmp_path, "uv", "venv", str(runtime))
    wheel = next((tmp_path / "dist").glob("*.whl"))
    _run(
        tmp_path,
        "uv",
        "pip",
        "install",
        "--python",
        str(runtime / "bin/python"),
        "--offline",
        "typer==0.27.2",
        str(wheel),
    )
    assert _run(tmp_path, str(runtime / "bin/starter-py"), "--name", "Ada") == "Hello, Ada!\n"
