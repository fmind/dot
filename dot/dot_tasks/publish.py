"""Publish this repository's built release and reconcile an existing publication."""

import argparse
import hashlib
import json
import re
import sys
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from dot_tasks.release import read_release_version
from fmind_dot.errors import DotError
from fmind_dot.process import diagnostic_line
from fmind_dot.state import State

ROOT = Path(__file__).resolve().parents[2]
# Uploading two distributions is slow on a busy runner; a hung gh must still end the job.
_CREATE_TIMEOUT_SECONDS = 900
_VIEW_TIMEOUT_SECONDS = 120
_METADATA_LIMIT = 1024 * 1024


def _validate_distribution(path: Path, name: str, version: str) -> None:
    """Inspect archive identity without extracting or executing package contents."""
    normalized_name = re.sub(r"[-_.]+", "_", name).lower()
    prefix = f"{normalized_name}-{version}"
    try:
        if path.suffix == ".whl":
            # This project emits a pure-Python wheel without a build tag.
            if path.name != f"{prefix}-py3-none-any.whl":
                raise DotError(f"distribution filename must match project {name} version {version}")
            with zipfile.ZipFile(path) as archive:
                entries = [entry for entry in archive.infolist() if entry.filename.endswith(".dist-info/METADATA")]
                if len(entries) != 1 or entries[0].filename != f"{prefix}.dist-info/METADATA":
                    raise DotError("wheel must contain exactly one matching distribution metadata file")
                if entries[0].file_size > _METADATA_LIMIT:
                    raise DotError("distribution metadata exceeds 1 MiB")
                content = archive.read(entries[0])
        else:
            if path.name != f"{prefix}.tar.gz":
                raise DotError(f"distribution filename must match project {name} version {version}")
            with tarfile.open(path, "r:gz") as archive:
                entries = [entry for entry in archive if entry.name == f"{prefix}/PKG-INFO"]
                if len(entries) != 1 or not entries[0].isfile():
                    raise DotError("source distribution must contain one regular root PKG-INFO file")
                if entries[0].size > _METADATA_LIMIT:
                    raise DotError("distribution metadata exceeds 1 MiB")
                stream = archive.extractfile(entries[0])
                if stream is None:
                    raise DotError("source distribution metadata is unreadable")
                with stream:
                    content = stream.read(_METADATA_LIMIT + 1)
        metadata = BytesParser().parsebytes(content, headersonly=True)
        names, versions = metadata.get_all("Name", []), metadata.get_all("Version", [])
        if len(names) != 1 or re.sub(r"[-_.]+", "_", str(names[0])).lower() != normalized_name or versions != [version]:
            raise DotError(f"distribution metadata must match project {name} version {version}")
    except DotError:
        raise
    except (OSError, EOFError, tarfile.TarError, zipfile.BadZipFile, RuntimeError) as error:
        raise DotError(f"cannot read distribution metadata from {path.name}: {type(error).__name__}") from error


def validate_release_inputs(root: Path, tag: str, notes: Path) -> list[Path]:
    """Bind the tag, distributions, and notes together before attestation or any remote call."""
    version = read_release_version(root)
    if tag != f"v{version}":
        raise DotError(f"release tag {tag!r} must match the project version v{version}")
    wheels = sorted((root / "dot/dist").glob("*.whl"))
    sources = sorted((root / "dot/dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1 or not notes.is_file():
        raise DotError("publication requires one wheel, one source distribution, and a release notes file")
    name = tomllib.loads((root / "dot/pyproject.toml").read_text())["project"].get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise DotError("project name must be a valid distribution name")
    for asset in wheels + sources:
        _validate_distribution(asset, name, version)
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
