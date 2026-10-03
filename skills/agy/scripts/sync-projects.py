#!/usr/bin/env python3
"""Sync Antigravity's Remote Control project list with the Git checkouts in ~/*/*/.git."""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse


def checkouts(home: Path) -> dict[str, str]:
    """Map each checkout's resolved folder URI to its display name, skipping hidden directories like the shell."""
    found: dict[str, str] = {}
    for marker in sorted(home.glob("*/*/.git")):
        name = marker.parent.relative_to(home)
        if not any(part.startswith(".") for part in name.parts):
            found.setdefault(marker.parent.resolve().as_uri(), str(name))
    return found


def folders(project: dict) -> list[str]:
    resources = project.get("projectResources", {}).get("resources", [])
    return [r.get("folderUri") or r.get("gitFolder", {}).get("folderUri") or "" for r in resources]


def plan(home: Path, registry: Path) -> tuple[list[Path], dict[str, str]]:
    """Return entries to remove and checkouts to add; entries without folders (native defaults) stay."""
    missing = checkouts(home)
    stale = []
    for source in sorted(registry.glob("*.json")):
        uris = folders(json.loads(source.read_text()))
        if not uris:
            continue
        # Keep one entry per checkout; duplicates and anything outside the glob go.
        if all(uri in missing for uri in uris):
            for uri in uris:
                del missing[uri]
        else:
            stale.append(source)
    return stale, missing


def write(registry: Path, uri: str, name: str) -> None:
    project_id = "local-" + hashlib.sha256(unquote(urlparse(uri).path).encode()).hexdigest()[:24]
    project = {"id": project_id, "name": name, "projectResources": {"resources": [{"folderUri": uri}]}}
    # Publish complete JSON only; a failed write leaves no partial entry.
    with tempfile.NamedTemporaryFile("w", dir=registry, prefix=".project-", suffix=".tmp", delete=False) as stream:
        json.dump(project, stream, indent=2)
        stream.write("\n")
    Path(stream.name).replace(registry / f"{project_id}.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes; default is a preview")
    args = parser.parse_args()
    home = Path.home()
    registry = home / ".gemini/config/projects"
    try:
        # A preview must not create the registry; glob on a missing directory finds nothing.
        if args.apply:
            registry.mkdir(parents=True, exist_ok=True, mode=0o700)
        stale, missing = plan(home, registry)
        for source in stale:
            sys.stdout.write(f"- {', '.join(folders(json.loads(source.read_text())))}\n")
            if args.apply:
                source.unlink(missing_ok=True)
        for uri, name in missing.items():
            sys.stdout.write(f"+ {name}\n")
            if args.apply:
                write(registry, uri, name)
    except (OSError, ValueError, AttributeError) as error:
        sys.stderr.write(f"Project sync failed ({type(error).__name__}); check {registry} JSON and permissions.\n")
        return 1
    verb = "applied" if args.apply else "previewed; rerun with --apply"
    sys.stdout.write(f"{len(missing)} added, {len(stale)} removed ({verb}).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
