"""Expose shared test isolation fixtures for CLI package tests."""

import sys
from pathlib import Path

import pytest

from fmind_dot import auth_probes as _auth_probes
from repo_helpers import (
    isolated_dot_config,
    isolated_git,
    isolated_home,
    isolated_terminal,
    native_chezmoi,
    plain_terminal,
)

sys.dont_write_bytecode = True


@pytest.fixture(autouse=True)
def isolated_gce(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point GCE DMI detection at an isolated missing path unless a test overrides it."""
    monkeypatch.setattr(_auth_probes, "GCE_DMI_PRODUCT_PATH", tmp_path / "no-dmi")


__all__ = [
    "isolated_dot_config",
    "isolated_gce",
    "isolated_git",
    "isolated_home",
    "isolated_terminal",
    "native_chezmoi",
    "plain_terminal",
]
