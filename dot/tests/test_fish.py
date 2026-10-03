"""Exercise interactive aliases without loading private shell configuration."""

import os
import subprocess
from pathlib import Path

import pytest


def test_fish_aliases_load_without_errors() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "fish",
            "--no-config",
            "--interactive",
            "--command",
            "source dot_config/fish/conf.d/aliases.fish; abbr --query a ac ai ap ar i k ux vd vs",
        ],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    # Fish can return success after an invalid abbr option in a sourced file.
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("exit_status", [0, 1])
def test_zellij_exit_returns_to_shell_without_reattaching(tmp_path: Path, exit_status: int) -> None:
    root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Avoid starting real shell integrations or touching their caches.
    for name in ("mise", "carapace", "fzf", "atuin", "starship", "zoxide"):
        executable = bin_dir / name
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    zellij = bin_dir / "zellij"
    zellij.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$ZELLIJ_TEST_CALLS"\nexit "$ZELLIJ_TEST_STATUS"\n',
        encoding="utf-8",
    )
    zellij.chmod(0o755)
    calls = tmp_path / "calls"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"ZELLIJ", "TMUX", "NVIM", "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"}
    }
    env.update(
        HOME=str(tmp_path),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        ZELLIJ_TEST_BIN=str(bin_dir),
        ZELLIJ_TEST_CALLS=str(calls),
        ZELLIJ_TEST_STATUS=str(exit_status),
        TERM_PROGRAM="ghostty",
    )
    result = subprocess.run(
        [
            "fish",
            "--no-config",
            "--interactive",
            "--command",
            (
                'set -gx PATH "$ZELLIJ_TEST_BIN" $PATH; '
                "source dot_config/fish/conf.d/plugins.fish; "
                "emit fish_prompt; echo shell-survived; emit fish_prompt; echo second-prompt"
            ),
        ],
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert result.stdout.splitlines() == ["shell-survived", "second-prompt"]
    assert calls.read_text(encoding="utf-8").splitlines() == ["attach --create main"]
