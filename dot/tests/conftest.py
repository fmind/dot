"""Keep native tool selection stable when tests replace HOME."""

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def native_chezmoi() -> Iterator[None]:
    """Resolve a mise shim before synthetic homes change its tool/trust lookup."""
    chezmoi = shutil.which("chezmoi")
    mise = shutil.which("mise")
    if chezmoi and mise and Path(chezmoi).resolve() == Path(mise).resolve():
        result = subprocess.run([mise, "which", "chezmoi"], capture_output=True, text=True, check=True, timeout=10)
        executable = Path(result.stdout.strip())
        if not executable.is_absolute() or not executable.is_file():
            raise RuntimeError("mise did not resolve an installed chezmoi executable")
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("PATH", str(executable.parent) + os.pathsep + os.environ["PATH"])
            yield
    else:
        yield
