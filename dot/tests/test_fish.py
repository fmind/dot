"""Exercise interactive aliases without loading private shell configuration."""

import subprocess
from pathlib import Path


def test_fish_aliases_load_without_errors() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "fish",
            "--no-config",
            "--interactive",
            "--command",
            "source dot_config/fish/conf.d/aliases.fish; abbr --query a ac ai ap i k ux vd vs",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    # Fish can return success after an invalid abbr option in a sourced file.
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout
