#!/usr/bin/env python3
"""Print validated runnable platform/digest pairs from a Buildx image index."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def platform_digests(index_path: Path, platforms: str) -> str:
    """Require exactly the requested platforms before returning any output."""
    raw_platforms = [item.strip() for item in platforms.split(",")]
    if not raw_platforms or any(not item for item in raw_platforms) or len(raw_platforms) != len(set(raw_platforms)):
        raise ValueError("Malformed platforms list")
    expected = set(raw_platforms)
    found: dict[str, str] = {}
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index, dict) or not isinstance(index.get("manifests"), list):
        raise TypeError("Malformed image index")
    for item in index["manifests"]:
        if not isinstance(item, dict) or not isinstance(item.get("platform"), dict):
            raise TypeError("Malformed manifest entry")
        platform = item["platform"]
        annotations = item.get("annotations")
        if annotations is not None and not isinstance(annotations, dict):
            raise TypeError("Malformed manifest annotations")
        if (
            platform == {"architecture": "unknown", "os": "unknown"}
            and (annotations or {}).get("vnd.docker.reference.type") == "attestation-manifest"
        ):
            continue  # BuildKit provenance is not a runnable platform.
        os_name, arch, digest = platform["os"], platform["architecture"], item["digest"]
        variant = platform.get("variant")
        if (
            not isinstance(os_name, str)
            or not isinstance(arch, str)
            or not isinstance(digest, str)
            or (variant is not None and not isinstance(variant, str))
        ):
            raise TypeError("Malformed platform fields")
        name = f"{os_name}/{arch}/{variant}" if variant else f"{os_name}/{arch}"
        if name not in expected or name in found or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise SystemExit("Unexpected, duplicate, or malformed platform descriptor")
        found[name] = digest
    if set(found) != expected:
        raise SystemExit("Image index does not contain every requested platform")
    return "".join(f"{name}\t{digest}\n" for name, digest in sorted(found.items()))


def main() -> None:
    """Validate a saved image index without registry access."""
    # Guard suggest_on_error=True for Python 3.10+ portability.
    parser_kwargs: dict[str, Any] = {"suggest_on_error": True} if sys.version_info >= (3, 14) else {}
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, **parser_kwargs)
    parser.add_argument("index", type=Path, help="JSON output of buildx imagetools inspect --raw")
    parser.add_argument("platforms", help="Comma-separated OS/architecture[/variant] tuples")
    args = parser.parse_args()
    try:
        output = platform_digests(args.index, args.platforms)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
        raise SystemExit("Cannot read or validate the image index") from error
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
