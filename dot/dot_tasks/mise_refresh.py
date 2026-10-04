"""Refresh the portable workstation lock without touching machine-local overrides."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from dot_tasks.mise_locks import bundle, capture


def validate(configuration: Path) -> None:
    """Reject incomplete generation before replacing the portable baseline."""
    config = tomllib.loads((configuration / "config.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((configuration / "mise.lock").read_text(encoding="utf-8"))
    for name, settings in config["tools"].items():
        entries = lock["tools"].get(name, [])
        if not entries or any(not entry.get("version") for entry in entries):
            raise ValueError(f"Missing locked version for {name}")
        if name.startswith(("npm:", "pipx:")):
            if any(not {"aube", "uv"}.intersection(entry) for entry in entries):
                raise ValueError(f"Missing dependency graph for {name}")
            continue
        allowed_os = settings.get("os") if isinstance(settings, dict) else None
        for platform in config["settings"]["lockfile_platforms"]:
            if allowed_os and platform.split("-")[0] not in allowed_os:
                continue
            if not any(entry.get(f"platforms.{platform}", {}).get("url") for entry in entries):
                raise ValueError(f"Missing locked download for {name} on {platform}")
    bundle(configuration / "mise.lock")


def refresh(root: Path, *, bump: bool = False) -> None:
    """Resolve the managed configuration in isolation and publish its complete bundle."""
    source = root / "dot_config/mise"
    environment = dict(os.environ)
    render_command = ["chezmoi", "execute-template", "--source", str(root), "--file", str(source / "config.toml.tmpl")]
    rendered = subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
        render_command,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Keep native graph resolution off RAM-backed /tmp on constrained Linux hosts.
    with tempfile.TemporaryDirectory(prefix="dot-mise-refresh-", dir="/var/tmp") as temporary:
        workspace = Path(temporary)
        configuration = workspace / ".config/mise"
        configuration.mkdir(parents=True)
        for relative, content in bundle(source / "mise.lock", verify=False).items():
            target = configuration / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (configuration / "config.toml").write_text(rendered.stdout, encoding="utf-8")
        # Preserve HOME for credentials and installed tools, but exclude live
        # user and system config: --global also targets system lockfiles.
        environment.update(
            MISE_CONFIG_DIR=str(configuration),
            MISE_GLOBAL_CONFIG_FILE=str(configuration / "config.toml"),
            MISE_SYSTEM_CONFIG_DIR=str(workspace / "system-mise"),
            MISE_SYSTEM_CONFIG_FILE=str(workspace / "system-mise/config.toml"),
            MISE_TRUSTED_CONFIG_PATHS=str(workspace),
        )
        command = ["mise", "lock", "--global", "--yes"]
        if bump:
            command.append("--bump")
        subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            command, cwd=workspace, env=environment, check=True, timeout=1800
        )
        validate(configuration)
        capture(configuration / "mise.lock", source / "mise.lock")


def main() -> int:
    """Refresh or upgrade the source-owned workstation tool baseline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bump", action="store_true", help="resolve latest versions instead of retaining locked versions"
    )
    arguments = parser.parse_args()
    try:
        refresh(Path(__file__).resolve().parents[2], bump=arguments.bump)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Cannot refresh mise lockfiles: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
