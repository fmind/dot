"""Run chezmoi against a temporary source, never the workstation's configuration."""

import os
import shlex
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path


def chezmoi(
    source: Path, *arguments: str, config: Path | None = None, stdin: str = "", env: Mapping[str, str] | None = None
) -> str:
    """Return stdout; a nonzero exit or any stderr output raises with both streams.

    The config is always explicit, or XDG_CONFIG_HOME selects the workstation's: the empty default suits
    read-only commands, while apply needs a real path because chezmoi keeps its state beside it. The
    `native_chezmoi` fixture puts the binary first on PATH (resolved here, so `env` may restrict PATH),
    and HOME, the default destination, comes from `isolated_home` or `env`.
    """
    command = [shutil.which("chezmoi") or "chezmoi", "--source", str(source), "--config", str(config or os.devnull)]
    command += ["--config-format", "toml", *arguments]
    result = subprocess.run(
        command, input=stdin, env=env, capture_output=True, encoding="utf-8", timeout=30, check=False
    )
    if result.returncode or result.stderr:
        message = f"chezmoi failed (exit {result.returncode}): {shlex.join(command)}"
        raise RuntimeError(f"{message}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result.stdout
