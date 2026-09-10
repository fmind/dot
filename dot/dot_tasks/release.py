"""Prepare and reconcile this repository's release without runtime CLI coupling."""

import argparse
import json
import os
import re
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep

from fmind_dot.errors import DotError
from fmind_dot.state import State


@dataclass(frozen=True)
class ReleaseConfig:
    remote: str = "origin"
    default_branch: str = "main"


_RELEASE_VERSION_FILE = Path("dot/pyproject.toml")
_RELEASE_CHANGELOG_FILE = Path("CHANGELOG.md")
_RELEASE_LOCK_FILE = Path("dot/uv.lock")
_RELEASE_GENERATED_FILES = (_RELEASE_CHANGELOG_FILE, _RELEASE_VERSION_FILE, _RELEASE_LOCK_FILE)
_RELEASE_CLIFF_CONFIG = Path("dot_config/git-cliff/cliff.toml")
_REMOTE_TAG_OUTPUT_LIMIT = 4 * 1024
_SEMVER_TAG = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_PROJECT_SECTION = re.compile(r"(?m)^\[project\]\s*$")
_SECTION = re.compile(r"(?m)^\[[^\n]+\]\s*$")
_VERSION_ASSIGNMENT = re.compile(r'(?m)^version\s*=\s*"([^"\r\n]+)"\s*$')


@dataclass(frozen=True)
class _ReleaseSnapshot:
    version: bytes
    changelog: bytes
    lock: bytes
    version_mode: int
    changelog_mode: int
    lock_mode: int


def _project_version_match(content: str) -> re.Match[str]:
    project = _PROJECT_SECTION.search(content)
    if project is None:
        raise DotError(f"{_RELEASE_VERSION_FILE} must contain a [project] table")
    next_section = _SECTION.search(content, project.end())
    section = content[project.end() : next_section.start() if next_section else len(content)]
    matches = list(_VERSION_ASSIGNMENT.finditer(section))
    if len(matches) != 1:
        raise DotError(
            f"{_RELEASE_VERSION_FILE} [project] must contain exactly one string version; found {len(matches)}"
        )
    match = matches[0]
    return _VERSION_ASSIGNMENT.match(content, project.end() + match.start(), project.end() + match.end()) or match


def _require_tool(state: State, command: str, guidance: str | None = None) -> None:
    if state.runner.which(command) is None:
        suffix = f"; {guidance}" if guidance else ""
        raise DotError(f"{command} is not installed{suffix}")


def _confirm(state: State, prompt: str) -> bool:
    state.stdout.write(prompt)
    answer = state.stdin.readline().strip().lower()
    return answer in {"y", "yes"}


def read_release_version(root: Path) -> str:
    """Read the sole PEP 621 project version used by release preparation."""
    path = root / _RELEASE_VERSION_FILE
    try:
        content = path.read_text()
        parsed = tomllib.loads(content)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise DotError(f"failed to read {_RELEASE_VERSION_FILE}: {error}") from error
    match = _project_version_match(content)
    value = parsed.get("project", {}).get("version")
    if not isinstance(value, str) or value != match.group(1):
        raise DotError(f"{_RELEASE_VERSION_FILE} has an ambiguous project version")
    return value


def write_release_version(root: Path, tag: str) -> None:
    """Replace only the PEP 621 project version assignment."""
    if not _SEMVER_TAG.fullmatch(tag):
        raise DotError(f"invalid semantic version tag {tag!r}")
    path = root / _RELEASE_VERSION_FILE
    content = path.read_text()
    match = _project_version_match(content)
    start, end = match.span(1)
    updated = content[:start] + tag.removeprefix("v") + content[end:]
    path.write_text(updated)


def validate_release_status(status_output: str) -> None:
    """Reject validation changes outside the generated release files."""
    allowed = {str(path) for path in _RELEASE_GENERATED_FILES}
    unexpected: list[str] = []
    for record in status_output.split("\0"):
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise DotError(f"malformed git status record {record!r}")
        if "R" in record[:2] or "C" in record[:2]:
            raise DotError(f"release validation does not allow renamed or copied paths: {record[3:]!r}")
        path = record[3:]
        if path not in allowed:
            unexpected.append(path)
        elif record[:2] != " M":
            raise DotError(
                f"release validation allows only ordinary worktree modifications, got {record[:2]!r} for {path}"
            )
    if unexpected:
        raise DotError(f"release validation changed unrelated paths: {', '.join(unexpected)}")


def _snapshot_release(root: Path) -> _ReleaseSnapshot:
    version_path = root / _RELEASE_VERSION_FILE
    changelog_path = root / _RELEASE_CHANGELOG_FILE
    lock_path = root / _RELEASE_LOCK_FILE
    return _ReleaseSnapshot(
        version=version_path.read_bytes(),
        changelog=changelog_path.read_bytes(),
        lock=lock_path.read_bytes(),
        version_mode=stat.S_IMODE(version_path.stat().st_mode),
        changelog_mode=stat.S_IMODE(changelog_path.stat().st_mode),
        lock_mode=stat.S_IMODE(lock_path.stat().st_mode),
    )


def _restore_release(root: Path, snapshot: _ReleaseSnapshot) -> None:
    version_path = root / _RELEASE_VERSION_FILE
    changelog_path = root / _RELEASE_CHANGELOG_FILE
    lock_path = root / _RELEASE_LOCK_FILE
    version_path.write_bytes(snapshot.version)
    version_path.chmod(snapshot.version_mode)
    changelog_path.write_bytes(snapshot.changelog)
    changelog_path.chmod(snapshot.changelog_mode)
    lock_path.write_bytes(snapshot.lock)
    lock_path.chmod(snapshot.lock_mode)


def _git_output(state: State, *args: str, cwd: Path | None = None, check: bool = True) -> str:
    return state.runner.run(["git", *args], cwd=cwd, check=check).stdout.strip()


def push_prepared_commit(state: State, remote: str, branch: str, commit: str) -> None:
    """Push a prepared commit, reconciling an uncertain command result."""
    refspec = f"{commit}:refs/heads/{branch}"
    state.runner.interactive(
        ["git", "push", remote, refspec], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    try:
        _git_output(state, "fetch", remote, branch)
        accepted = _git_output(state, "rev-parse", f"{remote}/{branch}")
    except DotError:
        accepted = ""
    if accepted != commit:
        raise DotError(f"failed to push prepared commit {commit} to {refspec}")


def _remote_release_tag_objects(state: State, remote: str, refspec: str) -> tuple[str, str]:
    """Resolve the exact direct tag object and its peeled commit."""
    peeled_ref = f"{refspec}^{{}}"
    result = state.runner.run_bounded(
        ["git", "ls-remote", "--tags", remote, refspec, peeled_ref],
        max_output_bytes=_REMOTE_TAG_OUTPUT_LIMIT,
    )
    if result.output_truncated:
        raise DotError(f"remote tag query for {refspec} exceeded {_REMOTE_TAG_OUTPUT_LIMIT} bytes")
    output = result.stdout.strip()
    direct = peeled = ""
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2:
            raise DotError(f"invalid ls-remote record for {refspec}: {line!r}")
        value, reference = fields
        if reference == refspec:
            if direct and direct != value:
                raise DotError(f"conflicting remote values for {refspec}")
            direct = value
        elif reference == peeled_ref:
            if peeled and peeled != value:
                raise DotError(f"conflicting remote values for {peeled_ref}")
            peeled = value
        else:
            raise DotError(f"unexpected remote tag ref {reference!r} while resolving {refspec}")
    if peeled and not direct:
        raise DotError(f"remote returned {peeled_ref} without its tag object {refspec}")
    return direct, peeled


def remote_release_tag_commit(state: State, remote: str, refspec: str) -> str:
    """Resolve the peeled commit only when the exact remote tag is annotated."""
    direct, peeled = _remote_release_tag_objects(state, remote, refspec)
    return peeled if direct and peeled else ""


def push_release_tag(state: State, remote: str, tag: str, commit: str) -> None:
    """Create and push an annotated tag, reconciling uncertain remote success."""
    refspec = f"refs/tags/{tag}"
    try:
        object_type = _git_output(state, "cat-file", "-t", refspec)
    except DotError:
        _git_output(state, "tag", "-a", tag, "-m", tag, commit)
    else:
        if object_type != "tag":
            raise DotError(f"local tag {tag} must be annotated, found Git object type {object_type!r}")
    tag_object = _git_output(state, "rev-parse", refspec)
    captured_type = _git_output(state, "cat-file", "-t", tag_object)
    if captured_type != "tag":
        raise DotError(f"local tag {tag} must be annotated, found Git object type {captured_type!r}")
    local = _git_output(state, "rev-parse", f"{tag_object}^{{}}")
    if local != commit:
        raise DotError(f"local tag {tag} resolves to {local}, expected release commit {commit}")
    exact_refspec = f"{tag_object}:{refspec}"
    state.runner.interactive(
        ["git", "push", remote, exact_refspec], stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
    )
    try:
        accepted_object, accepted_commit = _remote_release_tag_objects(state, remote, refspec)
    except DotError:
        accepted_object = accepted_commit = ""
    if accepted_object != tag_object or accepted_commit != commit:
        raise DotError(f"failed to push tag {tag} to {remote}")


def _prepared_release_tag(state: State, root: Path) -> str | None:
    try:
        subject = _git_output(state, "log", "-1", "--pretty=%s")
    except DotError:
        return None
    tag = subject.removeprefix("chore(release): ")
    if not _SEMVER_TAG.fullmatch(tag) or subject != f"chore(release): {tag}":
        return None
    try:
        version = read_release_version(root)
    except DotError:
        return None
    return tag if tag == f"v{version}" else None


def _calculate_release_version(state: State, root: Path) -> tuple[str, str]:
    config = str(_RELEASE_CLIFF_CONFIG)
    bumped = state.runner.run(["git-cliff", "--config", config, "--bumped-version"], cwd=root).stdout.strip()
    if not _SEMVER_TAG.fullmatch(bumped):
        raise DotError(f"git-cliff returned invalid semantic version tag {bumped!r}")
    try:
        current = _git_output(state, "describe", "--tags", "--abbrev=0")
    except DotError:
        current = "v0.0.0"
    return bumped, current


def _validate_prepared_release(state: State, root: Path, expected_tag: str, *, require_clean: bool = False) -> None:
    for task in ("format", "check", "test", "build"):
        state.stdout.write(f"Running {task}...\n")
        code = state.runner.interactive(
            ["mise", "run", task], cwd=root, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
        )
        if code != 0:
            raise DotError(f"project {task} failed")
    status_output = state.runner.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root
    ).stdout
    if require_clean:
        if status_output:
            raise DotError("prepared release validation changed the working tree")
    else:
        validate_release_status(status_output)
    actual_version = read_release_version(root)
    expected_version = expected_tag.removeprefix("v")
    if actual_version != expected_version:
        raise DotError(
            f"release validation changed the package version to {actual_version!r}, expected {expected_version!r}"
        )


def _rollback_staged_release(state: State, root: Path, snapshot: _ReleaseSnapshot, cause: Exception) -> None:
    errors = [str(cause)]
    try:
        state.runner.run(["git", "reset", "--mixed", "HEAD"], cwd=root, timeout=10)
    except DotError as error:
        errors.append(f"failed to restore release index: {error}")
    try:
        _restore_release(root, snapshot)
    except OSError as error:
        errors.append(f"failed to restore release files: {error}")
    raise DotError("; ".join(errors)) from cause


def _recover_interrupted_release(state: State, root: Path, snapshot: _ReleaseSnapshot, *, staged: bool) -> None:
    """Best-effort rollback that preserves KeyboardInterrupt for the CLI's exit 130."""
    errors: list[str] = []
    if staged:
        try:
            state.runner.run(["git", "reset", "--mixed", "HEAD"], cwd=root, timeout=10)
        except (DotError, OSError) as error:
            errors.append(f"failed to restore release index: {error}")
    try:
        _restore_release(root, snapshot)
    except OSError as error:
        errors.append(f"failed to restore release files: {error}")
    for error in errors:
        state.stderr.write(f"Release interruption recovery failed: {error}\n")


def _refresh_installed_cli(state: State, root: Path) -> None:
    # The release commit changes package metadata, so refresh the workstation
    # entrypoint before reporting success. A retry is safe after a remote push.
    state.runner.run(["mise", "run", "--force", "deploy"], cwd=root)


def run_release(state: State, *, yes: bool = False, settings: ReleaseConfig | None = None) -> str | None:
    """Prepare, validate, commit, and push one release and its exact tag."""
    _require_tool(state, "git")
    if _git_output(state, "status", "--porcelain"):
        raise DotError("working directory has uncommitted or staged changes; commit or stash them first")
    _require_tool(state, "gh")
    state.runner.run(["gh", "auth", "status"])
    _require_tool(state, "git-cliff", "run 'mise run tools' or install it via mise")
    _require_tool(state, "mise", "release validation cannot run")
    _require_tool(state, "uv", "release lock regeneration cannot run")
    root_text = _git_output(state, "rev-parse", "--show-toplevel")
    if not root_text:
        raise DotError("git returned an empty repository root")
    root = Path(root_text).absolute()
    config = settings or ReleaseConfig()
    branch = _git_output(state, "branch", "--show-current")
    if not branch:
        raise DotError("cannot prepare a release from a detached HEAD")
    if branch != config.default_branch:
        raise DotError(f"release preparation requires branch {config.default_branch!r}, current branch is {branch!r}")
    _git_output(state, "fetch", "--prune", "--tags", config.remote)
    head = _git_output(state, "rev-parse", "HEAD")
    upstream = _git_output(state, "rev-parse", f"{config.remote}/{config.default_branch}")
    prepared = _prepared_release_tag(state, root)
    if head != upstream:
        if prepared is None:
            raise DotError(
                f"release branch diverged: HEAD {head} does not equal {config.remote}/{config.default_branch} {upstream}"
            )
        if _git_output(state, "rev-parse", "HEAD^") != upstream:
            raise DotError(f"prepared release commit is not directly ahead of {config.remote}/{config.default_branch}")
    if prepared is not None:
        # A retry can start from a manually created lookalike commit. Re-run the
        # complete gate and require a clean result before any remote mutation.
        _validate_prepared_release(state, root, prepared, require_clean=True)
        if head != upstream:
            push_prepared_commit(state, config.remote, config.default_branch, head)
        push_release_tag(state, config.remote, prepared, head)
        _refresh_installed_cli(state, root)
        state.stdout.write(
            f"✓ Publication dispatched for {prepared} at {head}.\nhttps://github.com/fmind/dot/actions/workflows/cd.yml\n"
        )
        return prepared

    bumped, current = _calculate_release_version(state, root)
    if bumped == current:
        state.stdout.write(f"No new conventional commits since {current}. Nothing to release.\n")
        return None
    state.stdout.write(f"Current version: {current}\nNext version:    {bumped}\n")
    if not yes and not _confirm(state, f"Prepare and tag {bumped} for publication? [y/N]: "):
        state.stdout.write("Release canceled.\n")
        return None
    try:
        snapshot = _snapshot_release(root)
    except OSError as error:
        raise DotError(f"failed to snapshot release files: {error}") from error
    try:
        write_release_version(root, bumped)
        state.runner.run(
            ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--bump", "-o", str(_RELEASE_CHANGELOG_FILE)],
            cwd=root,
        )
        state.runner.run(["uv", "lock", "--project", str(_RELEASE_VERSION_FILE.parent)], cwd=root)
        _validate_prepared_release(state, root, bumped)
    except KeyboardInterrupt:
        _recover_interrupted_release(state, root, snapshot, staged=False)
        raise
    except (DotError, OSError) as error:
        try:
            _restore_release(root, snapshot)
        except OSError as restore_error:
            raise DotError(f"{error}; failed to restore release files: {restore_error}") from error
        raise
    try:
        state.runner.run(["git", "add", *(str(path) for path in _RELEASE_GENERATED_FILES)], cwd=root)
        state.runner.run(["git", "commit", "-m", f"chore(release): {bumped}"], cwd=root)
    except KeyboardInterrupt:
        _recover_interrupted_release(state, root, snapshot, staged=True)
        raise
    except (DotError, OSError) as error:
        _rollback_staged_release(state, root, snapshot, DotError(f"git commit preparation failed: {error}"))
    head = _git_output(state, "rev-parse", "HEAD")
    push_prepared_commit(state, config.remote, config.default_branch, head)
    push_release_tag(state, config.remote, bumped, head)
    _refresh_installed_cli(state, root)
    state.stdout.write(
        f"✓ Publication dispatched for {bumped} at {head}.\nhttps://github.com/fmind/dot/actions/workflows/cd.yml\n"
    )
    return bumped


def wait_for_release(state: State, tag: str, *, timeout_seconds: float = 1800) -> str:
    """Observe the exact release commit's CD and its published artifacts."""
    head = _git_output(state, "rev-parse", "HEAD")
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        response = state.runner.run_bounded(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "fmind/dot",
                "--workflow",
                "cd.yml",
                "--commit",
                head,
                "--branch",
                tag,
                "--limit",
                "20",
                "--json",
                "headSha,status,conclusion,url",
            ],
            timeout=min(30, deadline - monotonic()),
            max_output_bytes=64 * 1024,
        )
        if response.output_truncated:
            raise DotError("release workflow response exceeded the output limit")
        runs = json.loads(response.stdout)
        if not isinstance(runs, list):
            raise DotError("invalid release workflow response")
        selected = next((run for run in runs if isinstance(run, dict) and run.get("headSha") == head), None)
        if selected and selected.get("status") == "completed":
            if selected.get("conclusion") != "success":
                raise DotError(f"CD failed for {tag}; inspect https://github.com/fmind/dot/actions/workflows/cd.yml")
            release_result = state.runner.run_bounded(
                ["gh", "release", "view", tag, "--repo", "fmind/dot", "--json", "tagName,isDraft,url,assets"],
                timeout=max(0.001, min(30, deadline - monotonic())),
                max_output_bytes=64 * 1024,
            )
            if release_result.output_truncated:
                raise DotError("release metadata exceeded the output limit")
            release = json.loads(release_result.stdout)
            if not isinstance(release, dict) or release.get("tagName") != tag or release.get("isDraft") is not False:
                raise DotError("CD succeeded but the expected public release is unavailable")
            assets = release.get("assets", [])
            names = (
                [asset["name"] for asset in assets if isinstance(asset, dict) and isinstance(asset.get("name"), str)]
                if isinstance(assets, list)
                else []
            )
            if not any(name.endswith(".whl") for name in names) or not any(name.endswith(".tar.gz") for name in names):
                raise DotError("published release is missing its wheel or source distribution")
            url = f"https://github.com/fmind/dot/releases/tag/{tag}"
            state.stdout.write(f"✓ Published {tag}: {url}\n")
            return url
        state.stderr.write(f"Waiting for publication of {tag} at {head[:12]}...\n")
        sleep(min(5, max(0, deadline - monotonic())))
    raise DotError(f"timed out waiting for {tag}; publication may still complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    args = parser.parse_args()
    if not 0 < args.timeout_seconds < float("inf"):
        parser.error("--timeout-seconds must be positive and finite")
    os.chdir(Path(__file__).resolve().parents[2])
    state = State()
    try:
        tag = run_release(state, yes=args.yes, settings=ReleaseConfig(args.remote, args.branch))
        if args.wait and tag:
            wait_for_release(state, tag, timeout_seconds=args.timeout_seconds)
    except KeyboardInterrupt:
        return 130
    except (DotError, OSError, ValueError) as error:
        sys.stderr.write(f"release: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
