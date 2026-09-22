"""Publish this repository's built release and reconcile an existing publication."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from dot_tasks.release import read_release_version
from fmind_dot.errors import DotError
from fmind_dot.process import diagnostic_line
from fmind_dot.state import State

ROOT = Path(__file__).resolve().parents[2]
# Uploading two distributions is slow on a busy runner; a hung gh must still end the job.
_CREATE_TIMEOUT_SECONDS = 900
_VIEW_TIMEOUT_SECONDS = 120


def validate_release_inputs(root: Path, tag: str, notes: Path) -> list[Path]:
    """Bind the tag, distributions, and notes together before attestation or any remote call."""
    version = read_release_version(root)
    if tag != f"v{version}":
        raise DotError(f"release tag {tag!r} must match the project version v{version}")
    wheels = sorted((root / "dot/dist").glob("*.whl"))
    sources = sorted((root / "dot/dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1 or not notes.is_file():
        raise DotError("publication requires one wheel, one source distribution, and a release notes file")
    # CD builds the distributions in another job; reject an artifact built from a different version.
    if f"-{version}-" not in wheels[0].name or not sources[0].name.endswith(f"-{version}.tar.gz"):
        raise DotError(f"built distributions do not carry the project version {version}")
    return wheels + sources


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return f"sha256:{hashlib.file_digest(stream, 'sha256').hexdigest()}"


def publish_release(state: State, root: Path, tag: str, notes: Path) -> None:
    """Create a release without overwrites; a retry must find byte-identical public assets."""
    assets = validate_release_inputs(root, tag, notes)
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
        timeout=_CREATE_TIMEOUT_SECONDS,
        check=False,
    )
    # gh reports why create failed (existing release, auth, network) on stderr; keep one sanitized line.
    create_failure = (
        f"gh release create failed ({created.returncode}): {diagnostic_line(created.stderr) or 'no diagnostic'}"
        if created.returncode
        else ""
    )
    if create_failure:
        state.stderr.write(f"{create_failure}; verifying the existing release\n")
    try:
        result = state.runner.run(
            ["gh", "release", "view", tag, "--json", "tagName,isDraft,assets"], cwd=root, timeout=_VIEW_TIMEOUT_SECONDS
        )
    except DotError as error:
        raise DotError(f"{error}; {create_failure}" if create_failure else str(error)) from error
    release = json.loads(result.stdout)
    if not isinstance(release, dict) or release.get("tagName") != tag or release.get("isDraft") is not False:
        suffix = f" ({create_failure})" if create_failure else ""
        raise DotError(
            f"publication did not produce the expected public release{suffix}; inspect the release before retrying"
        )
    remote_assets = release.get("assets")
    if not isinstance(remote_assets, list):
        raise DotError("release response has no asset list")
    digests = {asset.get("name"): asset.get("digest") for asset in remote_assets if isinstance(asset, dict)}
    for asset in assets:
        if asset.name not in digests:
            raise DotError("release is missing expected assets; inspect the incomplete release before retrying")
        # A name match alone would accept a rebuilt or substituted file; compare content.
        if digests[asset.name] != _sha256(asset):
            raise DotError(
                f"release asset {asset.name} differs from the local build ({digests[asset.name]!r}); "
                "published assets are never overwritten: verify the existing release with "
                "'gh attestation verify', or release a new version"
            )
    action = "Published" if created.returncode == 0 else "Verified existing release"
    state.stdout.write(f"{action} {tag}.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--notes-file", required=True, type=Path, help="Absolute or repository-relative notes path")
    parser.add_argument("--validate-only", action="store_true", help="check inputs without contacting GitHub")
    args = parser.parse_args()
    # uv --directory dot changes cwd; task arguments still name paths from the repository root.
    notes = ROOT / args.notes_file
    try:
        if args.validate_only:
            validate_release_inputs(ROOT, args.tag, notes)
        else:
            publish_release(State(), ROOT, args.tag, notes)
    except (DotError, OSError, ValueError) as error:
        sys.stderr.write(f"publish: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
