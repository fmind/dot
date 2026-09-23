"""Print validated runnable platform/digest pairs from a Buildx image index."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def platform_digests(index_path: Path, platforms: str) -> str:
    """Require exactly the requested platforms before returning any output."""
    expected = set(platforms.split(","))
    found: dict[str, str] = {}
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in index["manifests"]:
        platform = item["platform"]
        if (
            platform == {"architecture": "unknown", "os": "unknown"}
            and item.get("annotations", {}).get("vnd.docker.reference.type") == "attestation-manifest"
        ):
            continue  # BuildKit provenance is not a runnable platform.
        name = f"{platform['os']}/{platform['architecture']}"
        digest = item["digest"]
        if name not in expected or name in found or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise SystemExit("Unexpected, duplicate, or malformed platform descriptor")
        found[name] = digest
    if set(found) != expected:
        raise SystemExit("Image index does not contain every requested platform")
    return "".join(f"{name}\t{digest}\n" for name, digest in sorted(found.items()))


def main() -> None:
    """Validate a saved image index without registry access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path, help="JSON output of buildx imagetools inspect --raw")
    parser.add_argument("platforms", help="Comma-separated OS/architecture pairs")
    args = parser.parse_args()
    try:
        output = platform_digests(args.index, args.platforms)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SystemExit("Cannot read or validate the image index") from error
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
