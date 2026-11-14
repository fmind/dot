"""Refresh the portable workstation lock without touching machine-local overrides."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path

from dot_tasks import ROOT
from dot_tasks.mise_locks import bundle, capture

_CHECKSUM_PREFIXES = ("sha256:", "sha512:", "blake3:")


def validate(configuration: Path, config_name: str = "config.toml") -> None:
    """Reject an incomplete or unverifiable lock before it replaces the portable baseline."""
    config = tomllib.loads((configuration / config_name).read_text(encoding="utf-8"))
    lock = tomllib.loads((configuration / "mise.lock").read_text(encoding="utf-8"))
    findings: list[str] = []
    python_version = config["tools"].get("python")
    for name, settings in config["tools"].items():
        entries = lock["tools"].get(name, [])
        if not entries or any(not entry.get("version") for entry in entries):
            findings.append(f"{name}: missing locked version")
            continue
        if name.startswith(("npm:", "pypi:")):
            if name.startswith("pypi:") and isinstance(python_version, str):
                if not isinstance(settings, dict) or settings.get("python") != python_version:
                    findings.append(f"{name}: missing python = {python_version!r}")
                elif any(entry.get("options", {}).get("python") != python_version for entry in entries):
                    findings.append(f"{name}: lock options missing python = {python_version!r}")
            # Native dependency graphs are verified by bundle() below.
            if any(not {"aube", "uv"}.intersection(entry) for entry in entries):
                findings.append(f"{name}: missing dependency graph")
            continue
        allowed_os = settings.get("os") if isinstance(settings, dict) else None
        for platform in config["settings"]["lockfile_platforms"]:
            if allowed_os and platform.split("-")[0] not in allowed_os:
                continue
            # Platform-specific asset options produce separate lock entries, so each
            # supported platform needs one complete artifact across them.
            artifacts = [entry.get(f"platforms.{platform}", {}) for entry in entries]
            if not any(artifact.get("url") for artifact in artifacts):
                findings.append(f"{name} {platform}: missing locked download")
            # Every tool must be verifiable from the lockfile alone: relock an unverifiable
            # tool on a checksummed backend (aqua, core, github) instead of exempting it.
            if not any(str(artifact.get("checksum", "")).startswith(_CHECKSUM_PREFIXES) for artifact in artifacts):
                findings.append(f"{name} {platform}: checksum missing")
    if findings:
        raise ValueError("Incomplete mise lock: " + "; ".join(findings))
    bundle(configuration / "mise.lock")


def undeclared(root: Path, tools: Sequence[str]) -> str:
    """Describe the requested tools that the managed configuration does not declare, if any."""
    declared = tomllib.loads((root / "dot_config/mise/config.toml").read_text(encoding="utf-8"))["tools"]
    if unknown := [tool for tool in tools if tool not in declared]:
        # An undeclared name would be locked without validation; mise lock NAME@VERSION would
        # also rewrite the request, which this refresh never captures.
        return (
            f"undeclared tools {', '.join(unknown)}: pass [tools] keys from dot_config/mise/config.toml "
            "without @VERSION, or declare the tool there first"
        )
    return ""


def refresh(root: Path, *, bump: bool = False, tools: Sequence[str] = ()) -> None:
    """Resolve the managed configuration in isolation and publish its complete bundle.

    ``bump`` re-resolves every tool; ``tools`` re-resolves only those declared tools, so every
    other entry and dependency graph stays byte-identical.
    """
    if bump and tools:
        raise ValueError("Choose either bump (every tool) or tools (only the named ones)")
    if problem := undeclared(root, tools):
        raise ValueError(problem)
    source = root / "dot_config/mise"
    environment = dict(os.environ)
    # Keep native graph resolution off RAM-backed /tmp on constrained Linux hosts.
    with tempfile.TemporaryDirectory(prefix="dot-mise-refresh-", dir="/var/tmp") as temporary:
        workspace = Path(temporary).resolve()
        configuration = workspace / ".config/mise"
        configuration.mkdir(parents=True)
        for relative, content in bundle(source / "mise.lock", verify=False).items():
            target = configuration / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (configuration / "config.toml").write_bytes((source / "config.toml").read_bytes())
        # Preserve HOME for credentials and installed tools, but exclude live
        # user and system config: --global also targets system lockfiles.
        environment.update(
            MISE_CONFIG_DIR=str(configuration),
            MISE_GLOBAL_CONFIG_FILE=str(configuration / "config.toml"),
            MISE_STATE_DIR=str(workspace / "state-mise"),
            MISE_SYSTEM_CONFIG_DIR=str(workspace / "system-mise"),
            MISE_SYSTEM_CONFIG_FILE=str(workspace / "system-mise/config.toml"),
            MISE_TRUSTED_CONFIG_PATHS=str(workspace),
            # The managed config sets `locked` so installs never rewrite this lock; its one writer
            # must still add newly declared tools, which locked mode refuses.
            MISE_LOCKED="0",
        )
        # An unbumped lock resolves "latest" to the installed version, so named tools always bump.
        command = ["mise", "lock", "--global", "--yes", *(["--bump"] if bump or tools else []), *tools]
        subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            command, cwd=workspace, env=environment, check=True, timeout=1800
        )
        validate(configuration)
        capture(configuration / "mise.lock", source / "mise.lock")


def main() -> int:
    """Refresh or upgrade the source-owned workstation tool baseline."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
        suggest_on_error=True,
        epilog=(
            "Right after an upstream release, mise can still serve the previous latest version from "
            "its cache: run `mise cache clear` (or `mise cache clear TOOL`), check `mise latest TOOL`, "
            "then retry; set UV_NO_CACHE=1 when a fresh PyPI release fails to resolve."
        ),
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--bump", action="store_true", help="resolve latest versions instead of retaining locked versions"
    )
    selection.add_argument(
        "--tool",
        action="extend",
        nargs="+",
        default=[],
        metavar="TOOL",
        help="resolve the latest version of only these [tools] keys (repeatable); keep every other entry",
    )
    arguments = parser.parse_args()
    try:
        if problem := undeclared(ROOT, arguments.tool):
            parser.error(problem)  # Invalid input exits 2 before anything is resolved.
        refresh(ROOT, bump=arguments.bump, tools=arguments.tool)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Cannot refresh mise lockfiles: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
