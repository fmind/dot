"""Keep native tool selection stable when tests replace HOME."""

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the repository Git exports to hooks: a pre-push run from a linked worktree gets an absolute GIT_DIR,
    and every fixture `git -C TMP` command would otherwise commit to, and reconfigure, this repository."""
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def isolated_home(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point HOME at a fresh directory so no test can read or write the real archive, config, or secrets.

    Tests that need their own layout still set HOME themselves. Only `real_home` tests, which run
    repository tasks through mise shims that resolve tools from the real HOME, keep it.
    """
    if request.node.get_closest_marker("real_home") is None:
        monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


@pytest.fixture(autouse=True)
def isolated_dot_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI invocations without --config must not read the configuration the caller selected."""
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)


@pytest.fixture(scope="session", autouse=True)
def native_chezmoi() -> Iterator[None]:
    """Resolve a mise shim before synthetic homes change its tool/trust lookup."""
    chezmoi = shutil.which("chezmoi")
    mise = shutil.which("mise")
    executable = None
    if chezmoi and mise and Path(chezmoi).resolve() == Path(mise).resolve():
        # A slow or failing mise must not error every test; only the chezmoi tests need the binary.
        try:
            result = subprocess.run([mise, "which", "chezmoi"], capture_output=True, text=True, check=True, timeout=30)
        except subprocess.CalledProcessError, subprocess.TimeoutExpired:
            result = None
        candidate = Path(result.stdout.strip()) if result else None
        if candidate and candidate.is_absolute() and candidate.is_file():
            executable = candidate
    if executable is None:
        yield
        return
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("PATH", str(executable.parent) + os.pathsep + os.environ["PATH"])
        yield
