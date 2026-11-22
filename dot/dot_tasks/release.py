"""Prepare, tag, and push this repository's next release; CD publishes it."""

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

from dot_tasks import ROOT
from fmind_dot.errors import DotError
from fmind_dot.repository import git_failure
from fmind_dot.state import State, require_tools

_RELEASE_VERSION_FILE = Path("dot/pyproject.toml")
_RELEASE_CHANGELOG_FILE = Path("CHANGELOG.md")
_RELEASE_GENERATED_FILES = (_RELEASE_CHANGELOG_FILE, _RELEASE_VERSION_FILE, Path("dot/uv.lock"))
_RELEASE_CLIFF_CONFIG = Path("dot_config/git-cliff/cliff.toml")
_CD_URL = "https://github.com/fmind/dot/actions/workflows/cd.yml"
_RELEASE_GATES = ("all", "test:starters", "check:completions")
_GIT_TIMEOUT_SECONDS = 300
_TOOL_TIMEOUT_SECONDS = 600
# Pre-releases/build suffixes normalize differently in PEP 440 distribution names.
_SEMVER_TAG = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_KEEP_HINT = (
    "Release preparation stopped; changes were kept in CHANGELOG.md, dot/pyproject.toml, and dot/uv.lock. "
    "Review git diff and git diff --cached before retrying; to drop only the generated release edits, "
    "run git restore --staged --worktree -- CHANGELOG.md dot/pyproject.toml dot/uv.lock\n"
)


def read_release_version(root: Path) -> str:
    """Read the sole PEP 621 project version used by release preparation."""
    try:
        parsed = tomllib.loads((root / _RELEASE_VERSION_FILE).read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise DotError(f"failed to read {_RELEASE_VERSION_FILE}: {error}") from error
    proj = parsed.get("project")
    value = proj.get("version") if isinstance(proj, dict) else None
    if not isinstance(value, str):
        raise DotError(f"{_RELEASE_VERSION_FILE} must define a static string [project] version")
    return value


def validate_release_status(status_output: str) -> None:
    """Reject validation changes outside the generated release files."""
    allowed, changed, records = {str(p) for p in _RELEASE_GENERATED_FILES}, set(), iter(status_output.split("\0"))
    for record in records:
        if record:
            changed.add(record[3:])
            if "R" in record[:2] or "C" in record[:2]:  # Rename/copy adds a separate trailing path record.
                changed.add(next(records, ""))
    if unexpected := sorted(changed - allowed):
        raise DotError(f"release validation changed unrelated paths: {', '.join(unexpected)}")


def _git(state: State, *args: str) -> str:
    result = state.runner.run(["git", *args], timeout=_GIT_TIMEOUT_SECONDS, check=False)
    if result.returncode:
        if "would clobber existing tag" in result.stderr:
            clobber = "local tags differ from the remote; back them up, then run: git fetch --tags --force"
            raise DotError(f"git fetch failed (1): {clobber}")
        raise DotError(git_failure(args, result))
    return result.stdout.strip()


def _interactive(state: State, args: list[str], root: Path) -> int:
    return state.runner.interactive(args, cwd=root, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr)


def _prepare(state: State, root: Path, tag: str) -> None:
    """Write the version, lock, and changelog, then run the release-only gates."""
    cliff_cmd = ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--unreleased", "--bump"]
    for cmd in (
        ["uv", "version", tag.removeprefix("v"), "--project", str(_RELEASE_VERSION_FILE.parent), "--no-sync"],
        [*cliff_cmd, "--prepend", str(_RELEASE_CHANGELOG_FILE)],
        ["dprint", "fmt", str(_RELEASE_CHANGELOG_FILE)],
    ):
        state.runner.run(cmd, cwd=root, timeout=_TOOL_TIMEOUT_SECONDS)
    for task in _RELEASE_GATES:
        state.stdout.write(f"Running {task}...\n")
        state.stdout.flush()
        if _interactive(state, ["mise", "run", task], root) != 0:
            raise DotError(f"project {task} failed")
    status = ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    validate_release_status(state.runner.run(status, cwd=root, timeout=_GIT_TIMEOUT_SECONDS).stdout)


def run_release(state: State, *, yes: bool = False) -> str | None:
    """Prepare, validate, commit, tag, and atomically push one release."""
    remote, branch = "origin", "main"
    require_tools(state, [["dprint"], ["git"], ["git-cliff"], ["mise"], ["uv"]])
    if _git(state, "status", "--porcelain"):
        raise DotError("working directory has uncommitted or staged changes; commit or stash them first")
    root = Path(_git(state, "rev-parse", "--show-toplevel")).absolute()
    if (cur := _git(state, "branch", "--show-current")) != branch:
        raise DotError(f"release preparation requires branch {branch!r}, current branch is {cur!r}")
    _git(state, "fetch", "--prune", "--tags", remote)
    if _git(state, "rev-parse", "HEAD") != _git(state, "rev-parse", f"{remote}/{branch}"):
        raise DotError(f"HEAD must equal {remote}/{branch}; push or integrate first")
    bump_cmd = ["git-cliff", "--config", str(_RELEASE_CLIFF_CONFIG), "--bumped-version"]
    bumped = state.runner.run(bump_cmd, cwd=root, timeout=_TOOL_TIMEOUT_SECONDS).stdout.strip()
    if not _SEMVER_TAG.fullmatch(bumped):
        raise DotError(f"git-cliff returned invalid semantic version tag {bumped!r}")
    if bumped == (current := f"v{read_release_version(root)}"):
        state.stdout.write(f"No new conventional commits since {current}. Nothing to release.\n")
        return None
    if _git(state, "tag", "--list", bumped):
        raise DotError(f"tag {bumped} already exists locally; delete it with: git tag -d {bumped}")
    state.stdout.write(f"Current version: {current}\nNext version:    {bumped}\n")
    if not yes:
        if not state.stdin.isatty():
            raise DotError("release requires confirmation; rerun in a terminal or pass --yes")
        state.stderr.write(f"Prepare and tag {bumped} for publication? [y/N]: ")
        state.stderr.flush()
        if state.stdin.readline().strip().lower() not in {"y", "yes"}:
            state.stdout.write("Release canceled.\n")
            return None
    try:
        _prepare(state, root, bumped)
        state.runner.run(["git", "add", *map(str, _RELEASE_GENERATED_FILES)], cwd=root, timeout=_GIT_TIMEOUT_SECONDS)
        if _interactive(state, ["git", "commit", "-m", f"chore(release): {bumped}"], root) != 0:
            raise DotError("release commit failed; see the hook output above")
    except BaseException:
        state.stderr.write(_KEEP_HINT)
        raise
    push = ["git", "push", "--atomic", remote, f"HEAD:refs/heads/{branch}", f"refs/tags/{bumped}"]
    push_s = " ".join(push)
    try:
        _git(state, "tag", bumped, "-m", bumped)
    except DotError as error:
        tail = f"fix the cause, then run: git tag {bumped} -m {bumped} && {push_s} && mise run deploy"
        raise DotError(f"tagging failed after the local release commit ({error}); {tail}") from error
    if _interactive(state, push, root) != 0:
        hint = f"the release commit and tag {bumped} are local. Retry with: {push_s}, then: mise run deploy"
        raise DotError(f"push failed; {hint}")
    if _interactive(state, ["mise", "run", "deploy"], root) != 0:
        raise DotError(f"pushed {bumped}, but refreshing the installed CLI failed; retry: mise run deploy")
    state.stdout.write(f"✓ Pushed {bumped}; CD gates and publishes it.\n{_CD_URL}\n")
    return bumped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("--yes", "-y", action="store_true")
    os.chdir(ROOT)
    try:
        run_release(State(), yes=parser.parse_args().yes)
    except KeyboardInterrupt:
        return 130
    except (DotError, OSError) as error:
        sys.stderr.write(f"release: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
