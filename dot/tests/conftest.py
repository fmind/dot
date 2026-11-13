"""Keep native tool selection stable when tests replace HOME."""

import os
import sys
from collections.abc import Iterator

import pytest

from tests.fakes import native_binary

# Tests import skill scripts from skills/, which harnesses read through ~/.agents/skills:
# direct pytest runs outside mise (no PYTHONDONTWRITEBYTECODE) must not leave bytecode there.
sys.dont_write_bytecode = True


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop the repository Git exports to hooks: a pre-push run from a linked worktree gets an absolute GIT_DIR,
    and every fixture `git -C TMP` command would otherwise commit to, and reconfigure, this repository."""
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def isolated_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep suites run inside Zellij or a desktop session from querying the live session, its user bus,
    or writing the real cache."""
    for key in (
        "DBUS_SESSION_BUS_ADDRESS",
        "HF_HOME",
        "HF_HUB_CACHE",
        "HUGGINGFACE_HUB_CACHE",
        "MISE_STATE_DIR",
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
    """argparse colors help and usage errors when a CI or a terminal forces color; assert on plain text."""
    monkeypatch.setenv("NO_COLOR", "1")
    for key in ("FORCE_COLOR", "PYTHON_COLORS"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolated_home(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point HOME at the test's tmp_path so no test can read or write the real archive, config, or secrets.

    Tests that need a separate layout still set HOME themselves. Only `real_home` tests, which run
    repository tasks through mise shims that resolve tools from the real HOME, keep it.
    """
    if request.node.get_closest_marker("real_home") is None:
        monkeypatch.setenv("HOME", str(request.getfixturevalue("tmp_path")))


@pytest.fixture(autouse=True)
def isolated_dot_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI invocations without --config must not read the configuration the caller selected."""
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)


@pytest.fixture(scope="session", autouse=True)
def native_chezmoi() -> Iterator[None]:
    """Resolve a mise shim before synthetic homes change its tool/trust lookup."""
    executable = native_binary("chezmoi")
    if executable is None:
        yield
        return
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("PATH", str(executable.parent) + os.pathsep + os.environ["PATH"])
        yield
