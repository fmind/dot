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
    findings, py = [], config["tools"].get("python")
    for name, settings in config["tools"].items():
        if not (entries := lock["tools"].get(name, [])) or any(not e.get("version") for e in entries):
            findings.append(f"{name}: missing locked version")
            continue
        if name.startswith(("npm:", "pypi:")):
            if name.startswith("pypi:") and isinstance(py, str):
                if not isinstance(settings, dict) or settings.get("python") != py:
                    findings.append(f"{name}: missing python = {py!r}")
                elif any(e.get("options", {}).get("python") != py for e in entries):
                    findings.append(f"{name}: lock options missing python = {py!r}")
            if any(not {"aube", "uv"}.intersection(e) for e in entries):
                findings.append(f"{name}: missing dependency graph")
            continue
        allowed_os = settings.get("os") if isinstance(settings, dict) else None
        for plat in config["settings"]["lockfile_platforms"]:
            if allowed_os and plat.split("-")[0] not in allowed_os:
                continue
            artifacts = [e.get(f"platforms.{plat}", {}) for e in entries]
            if not any(a.get("url") for a in artifacts):
                findings.append(f"{name} {plat}: missing locked download")
            if not any(str(a.get("checksum", "")).startswith(_CHECKSUM_PREFIXES) for a in artifacts):
                findings.append(f"{name} {plat}: checksum missing")
    if findings:
        raise ValueError("Incomplete mise lock: " + "; ".join(findings))
    bundle(configuration / "mise.lock")


def undeclared(root: Path, tools: Sequence[str]) -> str:
    """Describe requested tools missing from the managed configuration."""
    declared = tomllib.loads((root / "dot_config/mise/config.toml").read_text(encoding="utf-8"))["tools"]
    if not (unknown := [t for t in tools if t not in declared]):
        return ""
    return f"undeclared tools {', '.join(unknown)}: pass [tools] keys from dot_config/mise/config.toml without @VERSION, or declare the tool there first"


def refresh(root: Path, *, bump: bool = False, tools: Sequence[str] = ()) -> None:
    """Resolve the managed configuration in isolation and publish its complete bundle."""
    if bump and tools:
        raise ValueError("Choose either bump (every tool) or tools (only the named ones)")
    if problem := undeclared(root, tools):
        raise ValueError(problem)
    source = root / "dot_config/mise"
    with tempfile.TemporaryDirectory(prefix="dot-mise-refresh-", dir="/var/tmp") as temporary:
        ws = Path(temporary).resolve()
        (cfg := ws / ".config/mise").mkdir(parents=True)
        for rel, content in bundle(source / "mise.lock", verify=False).items():
            (target := cfg / rel).parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (cfg / "config.toml").write_bytes((source / "config.toml").read_bytes())
        env = dict(os.environ) | {
            "MISE_CONFIG_DIR": str(cfg),
            "MISE_GLOBAL_CONFIG_FILE": str(cfg / "config.toml"),
            "MISE_STATE_DIR": str(ws / "state-mise"),
            "MISE_SYSTEM_CONFIG_DIR": str(ws / "system-mise"),
            "MISE_SYSTEM_CONFIG_FILE": str(ws / "system-mise/config.toml"),
            "MISE_TRUSTED_CONFIG_PATHS": str(ws),
            "MISE_LOCKED": "0",
        }
        cmd = ["mise", "lock", "--global", "--yes", *(["--bump"] if bump or tools else []), *tools]
        subprocess.run(cmd, cwd=ws, env=env, check=True, timeout=1800)  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
        validate(cfg)
        capture(cfg / "mise.lock", source / "mise.lock")


def main() -> int:
    """Refresh or upgrade the source-owned workstation tool baseline."""
    epilog = "Right after an upstream release, mise can still serve the previous latest version from its cache: run `mise cache clear` (or `mise cache clear TOOL`), check `mise latest TOOL`, then retry; set UV_NO_CACHE=1 when a fresh PyPI release fails to resolve."
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True, epilog=epilog)
    sel = parser.add_mutually_exclusive_group()
    sel.add_argument("--bump", action="store_true", help="resolve latest versions instead of retaining locked versions")
    sel.add_argument("--tool", action="extend", nargs="+", default=[], metavar="TOOL", help="resolve only named tools")
    args = parser.parse_args()
    try:
        if problem := undeclared(ROOT, args.tool):
            parser.error(problem)
        refresh(ROOT, bump=args.bump, tools=args.tool)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Cannot refresh mise lockfiles: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
