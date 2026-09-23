import subprocess
import sys

from <package> import __main__ as module_entrypoint
from <package> import __version__


def test_module_entrypoint() -> None:
    assert module_entrypoint.__name__.endswith(".__main__")
    result = subprocess.run(
        [sys.executable, "-m", "<package>", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{__version__}\n"
    assert result.stderr == ""
