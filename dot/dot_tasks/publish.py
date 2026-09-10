"""Publish this repository's built release and reconcile an existing publication."""

import argparse
import json
import sys
from pathlib import Path

from dot_tasks.release import read_release_version
from fmind_dot.errors import DotError
from fmind_dot.state import State


def publish_release(state: State, root: Path, tag: str, notes: Path) -> None:
    """Create a release without overwrites; a retry must find complete public assets."""
    if tag != f"v{read_release_version(root)}":
        raise DotError("release tag must match the built project's version")
    wheels = sorted((root / "dot/dist").glob("*.whl"))
    sources = sorted((root / "dot/dist").glob("*.tar.gz"))
    assets = wheels + sources
    if len(wheels) != 1 or len(sources) != 1 or not notes.is_file():
        raise DotError("publication requires one wheel, one source distribution, and a release notes file")
    # A failed create can mean an existing release or an uncertain network result.
    # Always verify public assets; never interpret a failed lookup as absence.
    created = state.runner.run(
        [
            "gh",
            "release",
            "create",
            tag,
            *(str(asset) for asset in assets),
            "--verify-tag",
            "--title",
            tag,
            "--notes-file",
            str(notes),
        ],
        cwd=root,
        check=False,
    )
    result = state.runner.run(["gh", "release", "view", tag, "--json", "tagName,isDraft,assets"], cwd=root)
    release = json.loads(result.stdout)
    if not isinstance(release, dict) or release.get("tagName") != tag or release.get("isDraft") is not False:
        raise DotError("publication did not produce the expected public release; inspect the release before retrying")
    remote_assets = release.get("assets")
    if not isinstance(remote_assets, list):
        raise DotError("release response has no asset list")
    names = {
        asset.get("name") for asset in remote_assets if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    if not {asset.name for asset in assets}.issubset(names):
        raise DotError("release is missing expected assets; inspect the incomplete release before retrying")
    action = "Published" if created.returncode == 0 else "Verified existing release"
    state.stdout.write(f"{action} {tag}.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--notes-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        publish_release(State(), Path(__file__).resolve().parents[2], args.tag, args.notes_file)
    except (DotError, OSError, ValueError) as error:
        sys.stderr.write(f"publish: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
