"""Prepare, tag, and push this repository's next release; CD publishes it."""

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

from fmind_dot.errors import DotError
from fmind_dot.state import State

_RELEASE_VERSION_FILE = Path("dot/pyproject.toml")
_RELEASE_CHANGELOG_FILE = Path("CHANGELOG.md")
_RELEASE_GENERATED_FILES = (_RELEASE_CHANGELOG_FILE, _RELEASE_VERSION_FILE, Path("dot/uv.lock"))
_RELEASE_CLIFF_CONFIG = Path("dot_config/git-cliff/cliff.toml")
_CD_URL = "https://github.com/fmind/dot/actions/workflows/cd.yml"
# Gates for the bumped release commit: the network scans refresh vulnerability data
# that CD rechecks, the host-only completion check never runs in CI, the build proves
# the new version packages, and the starter contracts re-resolve the latest upstream
# packages, so an upstream break since CI stops preparation here instead of failing
# CD after the tag consumed the version. None of them may depend on Git hooks.
_RELEASE_GATES = ("check:network", "test:starters", "build", "check:completions")
# Generous bounds for captured commands: a hung tool must fail the release instead of
# blocking it forever. Relayed commands (gates, commit hooks, push, deploy) stream their
# output and stay unbounded, like their CI counterparts.
_GIT_TIMEOUT_SECONDS = 300
_TOOL_TIMEOUT_SECONDS = 600
# Release versions only: a SemVer pre-release or build suffix normalizes differently
# in PEP 440 distribution names.
_SEMVER_TAG = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def read_release_version(root: Path) -> str:
    """Read the sole PEP 621 project version used by release preparation."""
    try:
        parsed = tomllib.loads((root / _RELEASE_VERSION_FILE).read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise DotError(f"failed to read {_RELEASE_VERSION_FILE}: {error}") from error
    project = parsed.get("project")
    value = project.get("version") if isinstance(project, dict) else None
    if not isinstance(value, str):
        raise DotError(f"{_RELEASE_VERSION_FILE} must define a static string [project] version")
    return value


def validate_release_status(status_output: str) -> None:
    """Reject validation changes outside the generated release files."""
    allowed = {str(path) for path in _RELEASE_GENERATED_FILES}
    changed = {record[3:] for record in status_output.split("\0") if record}
    if unexpected := sorted(changed - allowed):
        raise DotError(f"release validation changed unrelated paths: {', '.join(unexpected)}")


def _git(state: State, *args: str) -> str:
    return state.runner.run(["git", *args], timeout=_GIT_TIMEOUT_SECONDS).stdout.strip()


def _interactive(state: State, args: list[str], root: Path) -> int:
    return state.runner.interactive(args, cwd=root, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr)


def _require_tools(state: State, *commands: str) -> None:
    if missing := [command for command in commands if state.runner.which(command) is None]:
        raise DotError(f"missing release tools: {', '.join(missing)}; run 'mise run tools'")


def _prepare(state: State, root: Path, tag: str) -> None:
    """Write the version, lock, and changelog, then run the release-only gates."""
    # uv rewrites only [project].version and relocks; --no-sync leaves the venv alone.
    state.runner.run(
        ["uv", "version", tag.removeprefix("v"), "--project", str(_RELEASE_VERSION_FILE.parent), "--no-sync"],
        cwd=root,
        timeout=_TOOL_TIMEOUT_SECONDS,
    )
    state.runner.run(
        ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--bump", "-o", str(_RELEASE_CHANGELOG_FILE)],
        cwd=root,
        timeout=_TOOL_TIMEOUT_SECONDS,
    )
    # git-cliff output differs from dprint style and CD rejects a tree its formatter changes;
    # format here rather than relying on a pre-commit hook that may not be installed.
    state.runner.run(["dprint", "fmt", str(_RELEASE_CHANGELOG_FILE)], cwd=root, timeout=_TOOL_TIMEOUT_SECONDS)
    for task in _RELEASE_GATES:
        state.stdout.write(f"Running {task}...\n")
        state.stdout.flush()
        if _interactive(state, ["mise", "run", task], root) != 0:
            raise DotError(f"project {task} failed")
    status = ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    validate_release_status(state.runner.run(status, cwd=root, timeout=_GIT_TIMEOUT_SECONDS).stdout)


def run_release(state: State, *, yes: bool = False, remote: str = "origin", branch: str = "main") -> str | None:
    """Prepare, validate, commit, tag, and atomically push one release."""
    _require_tools(state, "dprint", "git", "git-cliff", "mise", "uv")
    if _git(state, "status", "--porcelain"):
        raise DotError("working directory has uncommitted or staged changes; commit or stash them first")
    root = Path(_git(state, "rev-parse", "--show-toplevel")).absolute()
    if (current_branch := _git(state, "branch", "--show-current")) != branch:
        raise DotError(f"release preparation requires branch {branch!r}, current branch is {current_branch!r}")
    _git(state, "fetch", "--prune", "--tags", remote)
    if _git(state, "rev-parse", "HEAD") != _git(state, "rev-parse", f"{remote}/{branch}"):
        raise DotError(f"HEAD must equal {remote}/{branch}; push or integrate first")
    bumped = state.runner.run(
        ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--bumped-version"],
        cwd=root,
        timeout=_TOOL_TIMEOUT_SECONDS,
    ).stdout.strip()
    if not _SEMVER_TAG.fullmatch(bumped):
        raise DotError(f"git-cliff returned invalid semantic version tag {bumped!r}")
    current = f"v{read_release_version(root)}"
    if bumped == current:
        state.stdout.write(f"No new conventional commits since {current}. Nothing to release.\n")
        return None
    # Tagging runs after the commit, outside the rollback, so reject a leftover tag first.
    if _git(state, "tag", "--list", bumped):
        raise DotError(f"tag {bumped} already exists locally; delete it with: git tag -d {bumped}")
    state.stdout.write(f"Current version: {current}\nNext version:    {bumped}\n")
    if not yes:
        # Without a terminal the prompt would read EOF and silently cancel with exit 0.
        if not state.stdin.isatty():
            raise DotError("release requires confirmation; rerun in a terminal or pass --yes")
        state.stdout.write(f"Prepare and tag {bumped} for publication? [y/N]: ")
        state.stdout.flush()
        if state.stdin.readline().strip().lower() not in {"y", "yes"}:
            state.stdout.write("Release canceled.\n")
            return None
    try:
        _prepare(state, root, bumped)
        state.runner.run(
            ["git", "add", *(str(path) for path in _RELEASE_GENERATED_FILES)], cwd=root, timeout=_GIT_TIMEOUT_SECONDS
        )
        # The commit runs the Lefthook checks; relay their output so a failed hook is diagnosable.
        commit = ["git", "commit", "-m", f"chore(release): {bumped}"]
        if _interactive(state, commit, root) != 0:
            raise DotError("release commit failed; see the hook output above")
    except BaseException:
        # The tree was clean before preparation, so HEAD holds the exact originals.
        generated = [str(path) for path in _RELEASE_GENERATED_FILES]
        state.runner.run(["git", "restore", "--staged", "--worktree", "--", *generated], cwd=root, check=False)
        raise
    _git(state, "tag", "-a", bumped, "-m", bumped)
    # Atomic: the remote accepts the release commit and its tag together or neither.
    push = ["git", "push", "--atomic", remote, f"HEAD:refs/heads/{branch}", f"refs/tags/{bumped}"]
    if _interactive(state, push, root) != 0:
        raise DotError(
            f"push failed; the release commit and tag {bumped} are local. Retry with: "
            f"git push --atomic {remote} HEAD:refs/heads/{branch} refs/tags/{bumped}"
        )
    # The release commit changes package metadata, so refresh the installed CLI.
    if _interactive(state, ["mise", "run", "deploy"], root) != 0:
        raise DotError(f"pushed {bumped}, but refreshing the installed CLI failed; retry: mise run deploy")
    state.stdout.write(f"✓ Pushed {bumped}; CD gates and publishes it.\n{_CD_URL}\n")
    return bumped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parents[2])
    try:
        run_release(State(), yes=args.yes, remote=args.remote, branch=args.branch)
    except KeyboardInterrupt:
        return 130
    except (DotError, OSError) as error:
        sys.stderr.write(f"release: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
