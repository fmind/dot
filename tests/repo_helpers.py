"""Shared repository helpers and pytest isolation fixtures across test suites."""

from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
_REAL_HOME = os.environ.get("HOME")

# Repository workflows and shipped workflow templates.
WORKFLOWS = [
    *sorted((ROOT / ".github/workflows").glob("*.yml")),
    *sorted((ROOT / "skills/github/references/ci-cd/templates").glob("*.yml")),
    ROOT / "skills/gcloud/references/cloud-run/templates/deploy.yml",
    ROOT / "skills/code-security/templates/codeql.yml",
    ROOT / "skills/docs/references/site/templates/docs.yml",
    ROOT / "skills/infra-as-code/templates/tofu.yml",
]

# Repository composite actions and shipped composite-action templates.
ACTIONS = [
    *sorted((ROOT / ".github/actions").glob("*/action.yml")),
    *sorted((ROOT / "skills/github/references/ci-cd/templates").glob("*/action.yml")),
]


def load_script(name: str, path: Path) -> ModuleType:
    """Load a standalone Python script file as an isolated module."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native_binary(name: str) -> Path | None:
    """Resolve a command, unwrapping a mise shim against the real HOME before isolated_home replaces it."""
    if not (executable := shutil.which(name)):
        return None
    if (resolved := Path(executable).resolve()).name != "mise":
        return Path(executable)
    env = os.environ | ({"HOME": _REAL_HOME} if _REAL_HOME else {})
    try:
        out = subprocess.run(
            [str(resolved), "which", name], env=env, capture_output=True, text=True, timeout=30, check=True
        ).stdout
    except subprocess.CalledProcessError, subprocess.TimeoutExpired:
        return None
    return p if (p := Path(out.strip())).is_absolute() and p.is_file() else None


def chezmoi(
    source: Path, *arguments: str, config: Path | None = None, stdin: str = "", env: Mapping[str, str] | None = None
) -> str:
    """Run chezmoi against a synthetic source and return stdout."""
    command = [shutil.which("chezmoi") or "chezmoi", "--source", str(source), "--config", str(config or os.devnull)]
    command += ["--config-format", "toml", *arguments]
    result = subprocess.run(
        command, input=stdin, env=env, capture_output=True, encoding="utf-8", timeout=30, check=False
    )
    if result.returncode or result.stderr:
        message = f"chezmoi failed (exit {result.returncode}): {shlex.join(command)}"
        raise RuntimeError(f"{message}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result.stdout


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop Git hook variables so fixture git commands cannot mutate this checkout."""
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def isolated_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop desktop, multiplexer, and XDG variables during isolated tests."""
    for key in (
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
        "CLOUDSDK_CONFIG",
        "DBUS_SESSION_BUS_ADDRESS",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_WORKSPACE_CLI_CONFIG_DIR",
        "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE",
        "GOOGLE_WORKSPACE_CLI_TOKEN",
        "GWS_PROJECT",
        "HF_HOME",
        "HF_HUB_CACHE",
        "HUGGINGFACE_HUB_CACHE",
        "MISE_STATE_DIR",
        "SSH_CONNECTION",
        "SSH_TTY",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_STATE_HOME",
        "ZELLIJ",
        "ZELLIJ_PANE_ID",
        "ZELLIJ_SESSION_NAME",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def plain_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force plain uncolored output from CLI helpers under test."""
    monkeypatch.setenv("NO_COLOR", "1")
    for key in ("FORCE_COLOR", "PYTHON_COLORS"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolated_home(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate HOME unless marked with `real_home` for mise shim execution."""
    if request.node.get_closest_marker("real_home") is None:
        monkeypatch.setenv("HOME", str(request.getfixturevalue("tmp_path")))


@pytest.fixture(autouse=True)
def isolated_dot_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear DOT_CONFIG_PATH so tests do not inherit caller config."""
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)


@pytest.fixture(scope="session", autouse=True)
def native_chezmoi() -> Iterator[None]:
    """Resolve a mise shim before synthetic homes alter PATH/HOME lookups."""
    executable = native_binary("chezmoi")
    if executable is None:
        yield
        return
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("PATH", str(executable.parent) + os.pathsep + os.environ["PATH"])
        yield
