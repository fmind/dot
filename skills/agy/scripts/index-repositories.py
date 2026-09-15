#!/usr/bin/env python3
"""Register local GitHub checkouts in Antigravity's host-only project registry."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


class IndexingError(Exception):
    """An actionable diagnostic containing no host paths or native error output."""


def raise_walk_error(error: OSError) -> None:
    """Do not report an incomplete scan as successful."""
    raise IndexingError("Cannot scan repositories; check directory access under the scan roots.") from error


def discover(root: Path) -> list[Path]:
    """Skip hidden state, dependency trees and symlinks; accept Git worktrees."""
    found = []
    for path, directories, _files in root.walk(on_error=raise_walk_error):
        directories[:] = [
            name
            for name in directories
            if not name.startswith(".") and name not in {"node_modules", "modules", "vendor", "dist", "build"}
        ]
        if (path / ".git").exists():
            try:
                result = subprocess.run(
                    ["/usr/bin/env", "git", "config", "--get-regexp", r"^remote\..*\.url$"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
            except subprocess.TimeoutExpired as error:
                raise IndexingError(
                    "Git remote lookup timed out after 10 seconds; check local Git responsiveness."
                ) from error
            except OSError as error:
                raise IndexingError("Cannot run Git; check its installation and checkout access.") from error
            if result.returncode not in (0, 1):
                raise IndexingError("Cannot read Git remotes; check Git availability and checkout configuration.")
            if any(
                re.search(r"(?:https?://(?:[^/@]+@)?|ssh://git@|git@)github\.com[:/]", line)
                for line in result.stdout.splitlines()
            ):
                found.append(path.resolve())
    return found


def refresh(roots: list[Path], registry: Path, apply: bool) -> tuple[int, int]:
    """Add missing folders only; existing projects, grants and history stay native."""
    known = set()
    try:
        for source in registry.glob("*.json"):
            project = json.loads(source.read_text())
            for resource in project.get("projectResources", {}).get("resources", []):
                uri = resource.get("folderUri") or resource.get("gitFolder", {}).get("folderUri")
                if uri:
                    known.add(uri)
    except (ValueError, TypeError, AttributeError) as error:
        raise IndexingError(
            "Invalid project JSON; repair the JSON syntax and resource structure in the local registry."
        ) from error
    except OSError as error:
        raise IndexingError("Cannot read the project registry; check directory and file permissions.") from error
    repositories = sorted({path for root in roots for path in discover(root)})
    pending = [path for path in repositories if path.as_uri() not in known]
    # Validate every collision before publishing any new entries.
    entries = []
    for path in pending:
        project_id = "local-" + hashlib.sha256(str(path).encode()).hexdigest()[:24]
        destination = registry / f"{project_id}.json"
        if destination.exists():
            raise IndexingError("Project ID collision; inspect existing local registry entries before retrying.")
        entries.append(
            (
                destination,
                {
                    "id": project_id,
                    "name": str(path.relative_to(Path.home())) if path.is_relative_to(Path.home()) else path.name,
                    "projectResources": {"resources": [{"folderUri": path.as_uri()}]},
                },
            )
        )
    if apply:
        try:
            registry.mkdir(parents=True, exist_ok=True, mode=0o700)
            for destination, project in entries:
                # Exclusive creation prevents overwriting a project created concurrently.
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(project, stream, indent=2)
                    stream.write("\n")
        except OSError as error:
            raise IndexingError(
                "Cannot write the project registry; check permissions, free space and concurrent registration."
            ) from error
    return len(repositories), len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", type=Path, help="Scan roots (default: home and chezmoi source)")
    parser.add_argument("--apply", action="store_true", help="Register missing projects; default is preview")
    args = parser.parse_args()
    roots = args.roots or [Path.home(), Path.home() / ".local/share/chezmoi"]
    try:
        roots = [root.expanduser().resolve(strict=True) for root in roots]
        if any(not root.is_dir() for root in roots):
            raise ValueError("Every scan root must be a directory.")
    except (OSError, ValueError, RuntimeError) as _error:
        sys.stderr.write("Cannot resolve scan roots; supply existing, accessible directories.\n")
        return 1
    try:
        found, added = refresh(roots, Path.home() / ".gemini/config/projects", args.apply)
    except IndexingError as error:
        sys.stderr.write(f"Repository index failed: {error}\n")
        return 1
    sys.stdout.write(f"{found} GitHub checkouts; {added} projects {'added' if args.apply else 'to add'}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
