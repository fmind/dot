"""Bounded multi-repository synchronization and status."""

import stat
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

import typer

from fmind_dot.command_group import JsonOption
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, diagnostic_line, run_parallel
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools, state_from


@dataclass(frozen=True)
class RepoResult:
    """Outcome of updating one configured repository."""

    path: Path
    branch: str = ""
    commits: int = 0
    ahead: int = 0
    dirty: bool = False
    no_upstream: bool = False
    pushed: bool = False
    error: str = ""
    push_error: str = ""
    skipped: str = ""


@dataclass(frozen=True)
class RepositoryStatus:
    """Branch and working-tree state for one repository."""

    name: str
    parent: str
    branch: str = ""
    dirty: bool = False
    error: str = ""
    path: str = ""
    upstream: str = ""
    ahead: int = 0
    behind: int = 0
    operation: str = ""

    @property
    def needs_attention(self) -> bool:
        return bool(self.error or self.dirty or not self.upstream or self.ahead or self.behind or self.operation)


# Read-only inspection must not refresh the index: that takes index.lock and can
# collide with an editor, hook, or agent writing the same repository.
_STATUS = ("--no-optional-locks", "status", "--porcelain")
_GIT_ROOT_TIMEOUT_SECONDS = 30
# Status reads only local refs; it needs no network allowance like pull.timeout_seconds.
_STATUS_TIMEOUT_SECONDS = 30
DirtyPolicy = Literal["skip", "allow"]
# Concurrent workers fail fast instead of waiting on a terminal or askpass credential prompt.
_GIT_ENVIRONMENT = {"GIT_TERMINAL_PROMPT": "0", "SSH_ASKPASS_REQUIRE": "never"}
# Ordered classification of git stderr into stable causes that never echo remote output.
_GIT_FAILURE_CAUSES = (
    (
        "non-fast-forward",
        ("non-fast-forward", "not possible to fast-forward", "diverging branches", "fetch first", "[rejected]"),
    ),
    (
        "authentication failed",
        (
            "authentication failed",
            "permission denied",
            "could not read username",
            "terminal prompts disabled",
            "invalid username or password",
        ),
    ),
    ("push rejected by remote", ("[remote rejected]", "declined", "protected branch")),
    ("remote repository not found", ("repository not found", "does not appear to be a git repository")),
    (
        "network unavailable",
        (
            "could not resolve host",
            "unable to access",
            "connection timed out",
            "connection refused",
            "network is unreachable",
            "could not read from remote repository",
            "early eof",
        ),
    ),
    ("repository locked", ("index.lock", "cannot lock ref")),
)


def git_failure(arguments: Sequence[str], result: CommandResult) -> str:
    """Describe a failed git command by a classified cause, else its sanitized first error line."""
    subcommand = next((argument for argument in arguments if not argument.startswith("-")), "command")
    diagnostic = f"{result.stderr}\n{result.stdout}".lower()
    # Push and fetch lead with progress such as "To github.com:o/r.git"; the cause follows.
    lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    first_error = next((line for line in lines if line.startswith(("error:", "fatal:", "!"))), "")
    cause = next(
        (label for label, markers in _GIT_FAILURE_CAUSES if any(marker in diagnostic for marker in markers)),
        "",
    ) or diagnostic_line(first_error or result.stderr)
    return f"git {subcommand} failed ({result.returncode})" + (f": {cause}" if cause else "")


def _git(state: State, path: Path, arguments: Sequence[str], deadline: float, *, check: bool = True) -> str:
    result = state.runner.run(
        ["git", *arguments], cwd=path, env=_GIT_ENVIRONMENT, timeout=_remaining_timeout(deadline), check=False
    )
    if check and result.returncode:
        raise DotError(git_failure(arguments, result))
    return result.stdout


def git_root(state: State, cwd: Path | None = None) -> Path:
    """Resolve the repository root and fail with a safe diagnostic."""
    require_tools(state, [["git"]])
    location = str(cwd) if cwd is not None else "current directory"
    try:
        result = state.runner.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, timeout=_GIT_ROOT_TIMEOUT_SECONDS, check=False
        )
    except (DotError, OSError) as error:
        raise DotError(f"failed to inspect {location} with git: {error}") from error
    if result.returncode:
        raise DotError(f"{location} is not inside a git work tree")
    output = result.stdout.strip()
    if not output:
        raise DotError("git returned an empty repository root")
    return Path(output)


def find_git_repositories(state: State, paths: Sequence[Path] = ()) -> list[Path]:
    """Resolve explicit repositories or direct children of configured workspaces."""
    if paths:
        return sorted({git_root(state, expand_path(path)).resolve() for path in paths})
    repositories: list[Path] = []
    for configured in state.config.pull.directories:
        root = expand_path(configured).resolve()
        if (root / ".git").exists():
            repositories.append(root)
            continue
        try:
            entries = sorted(root.iterdir(), key=lambda path: path.name)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise DotError(f"failed to inspect repository workspace {root}: {error}") from error
        # Workspace links can point outside the configured root; never let pull or
        # its optional push operate on a repository reached through that boundary.
        for path in entries:
            try:
                # Path predicates suppress permission errors; stat keeps an incomplete
                # inventory from appearing to be a successful status or pull.
                if stat.S_ISDIR(path.lstat().st_mode):
                    (path / ".git").stat()
                    repositories.append(path)
            except FileNotFoundError:
                continue
            except OSError as error:
                raise DotError(f"failed to inspect repository {path}: {error}") from error
    return sorted(set(repositories))


def _remaining_timeout(deadline: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise DotError("repository operation timed out")
    return remaining


def _upstream(state: State, path: Path, deadline: float) -> str:
    """Return the configured upstream ref, or an empty string when the branch tracks none."""
    # Timeouts and launch errors still raise. Git exits 128 without an upstream, and still prints
    # the literal `@{u}` when the configured upstream ref is gone, so only success yields a ref.
    result = state.runner.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=path,
        env=_GIT_ENVIRONMENT,
        timeout=_remaining_timeout(deadline),
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _upstream_push(git: Callable[[Sequence[str]], str], branch: str) -> list[str]:
    """Push HEAD to the exact upstream the ahead count used, never a same-named branch or extra tags.

    A bare `git push` follows push.default and push.followTags, so with `current` a branch
    tracking a differently named upstream would create a new remote branch instead.
    """
    target = git(["for-each-ref", "--format=%(upstream:remotename)%00%(upstream:remoteref)", f"refs/heads/{branch}"])
    remote, _, ref = target.strip().partition("\0")
    if not remote or not ref.startswith("refs/heads/"):
        raise DotError(f"cannot resolve the upstream push target for {branch}; push it manually")
    return ["push", "--no-follow-tags", remote, f"HEAD:{ref}"]


def _branch(state: State, path: Path, deadline: float) -> str:
    branch = _git(state, path, ["branch", "--show-current"], deadline).strip()
    return branch or _git(state, path, ["rev-parse", "--short", "HEAD"], deadline).strip()


def _dirty(state: State, path: Path, deadline: float) -> bool:
    return bool(_git(state, path, _STATUS, deadline).strip())


def _fetch(state: State, path: Path, deadline: float) -> None:
    try:
        _git(state, path, ["fetch", "--prune"], deadline)
    except DotError as error:
        raise DotError(f"failed to fetch repository: {error}") from error


def _count(value: str, label: str) -> int:
    try:
        return int(value.strip())
    except ValueError as error:
        raise DotError(f"failed to parse {label} count") from error


def _pull_repository(
    state: State,
    path: Path,
    push: bool,
    timeout: float,
    *,
    dirty_policy: DirtyPolicy = "skip",
) -> RepoResult:
    deadline = monotonic() + timeout
    branch = ""
    dirty = False

    def git(arguments: Sequence[str]) -> str:
        return _git(state, path, arguments, deadline)

    try:
        branch = _branch(state, path, deadline)
        dirty = _dirty(state, path, deadline)
        if dirty and dirty_policy == "skip":
            return RepoResult(path=path, branch=branch, dirty=True, skipped="dirty worktree")
        _fetch(state, path, deadline)
        try:
            upstream = _upstream(state, path, deadline)
        except DotError as upstream_error:
            raise DotError(f"failed to inspect upstream: {upstream_error}") from upstream_error
        if not upstream:
            return RepoResult(path=path, branch=branch, dirty=dirty, no_upstream=True)
        behind_raw = git(["rev-list", "--count", "HEAD..@{u}"])
        behind = _count(behind_raw, "behind")
        # Fetch once, then fast-forward the upstream snapshot inspected above.
        git(["merge", "--ff-only", "@{u}"])
        ahead = _count(git(["rev-list", "--count", "@{u}..HEAD"]), "ahead")
        pushed = False
        push_error = ""
        # Fetch/merge can take long enough for an editor or another process to
        # change the worktree. Never authorize a push using the pre-fetch check.
        if push and ahead and not dirty:
            dirty = _dirty(state, path, deadline)
        if push and ahead and not dirty:
            try:
                git(_upstream_push(git, branch))
                pushed = True
            except DotError as error:
                push_error = str(error)
        return RepoResult(
            path=path,
            branch=branch,
            commits=behind,
            ahead=ahead,
            dirty=dirty,
            pushed=pushed,
            push_error=push_error,
        )
    except (DotError, OSError) as error:
        return RepoResult(path=path, branch=branch, dirty=dirty, error=str(error))


def run_pull(
    state: State,
    *,
    push: bool = False,
    paths: Sequence[Path] = (),
    dry_run: bool = False,
    as_json: bool = False,
    dirty_policy: DirtyPolicy = "skip",
) -> list[RepoResult]:
    """Fetch and fast-forward configured repositories concurrently."""
    require_tools(state, [["git"]])
    repositories = find_git_repositories(state, paths)
    if dry_run:
        plan = {
            "schema": "dot.pull.plan/v1",
            "remote_state": "not refreshed",
            "push": push,
            "dirty_policy": dirty_policy,
            "repositories": [str(path) for path in repositories],
        }
        if as_json:
            write_json(state.stdout, plan)
        else:
            state.stdout.write(f"Pull plan (no fetch or changes): dirty={dirty_policy}, push={push}\n")
            for path in repositories:
                state.stdout.write(f"  {path}\n")
        return []
    if not repositories:
        if as_json:
            write_json(state.stdout, {"schema": "dot.pull/v1", "complete": True, "repositories": []})
        else:
            state.stdout.write("No git repositories found in configured pull directories.\n")
        return []
    timeout = state.config.pull.timeout_seconds
    results = run_parallel(
        state.runner,
        lambda path: _pull_repository(state, path, push, timeout, dirty_policy=dirty_policy),
        repositories,
        state.config.pull.concurrency,
    )
    if as_json:
        write_json(
            state.stdout,
            {
                "schema": "dot.pull/v1",
                "complete": not any(item.error or item.push_error for item in results),
                "repositories": [asdict(item) | {"path": str(item.path)} for item in results],
            },
        )
        if any(item.error or item.push_error for item in results):
            raise DotError("pull completed with repository errors")
        return results
    failures = 0
    for item in results:
        flags = " [dirty]" if item.dirty else ""
        flags += " [no upstream]" if item.no_upstream else ""
        state.stdout.write(f"▶ {item.path.parent.name}/{item.path.name} [{item.branch or 'error'}]{flags}\n")
        if item.error:
            failures += 1
            state.stdout.write(f"  ✗ Pull failed: {item.error}\n")
        elif item.skipped:
            state.stdout.write(f"  ∅ skipped ({item.skipped})\n")
        elif item.no_upstream:
            state.stdout.write("  ∅ skipped (no upstream)\n")
        else:
            summary = f"pulled {item.commits} commit(s)" if item.commits else "up to date"
            state.stdout.write(f"  ✓ Pull successful ({summary})\n")
            if item.push_error:
                failures += 1
                state.stdout.write(f"  ✗ Push failed: {item.push_error}\n")
            elif item.pushed:
                state.stdout.write(f"  ↑ pushed {item.ahead} commit(s)\n")
            elif item.ahead:
                state.stdout.write(f"  ↑ {item.ahead} unpushed\n")
    if failures:
        raise DotError(f"failed to pull {failures} repositories")
    return results


def _repository_status(state: State, path: Path, *, fetch: bool = False) -> RepositoryStatus:
    # Fetching contacts the remote, so it gets the network allowance that pull uses.
    deadline = monotonic() + (state.config.pull.timeout_seconds if fetch else _STATUS_TIMEOUT_SECONDS)
    try:
        if fetch:
            _fetch(state, path, deadline)
        branch = _branch(state, path, deadline)
        dirty = _dirty(state, path, deadline)
        upstream = _upstream(state, path, deadline)
        ahead = behind = 0
        if upstream:
            counts = _git(state, path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"], deadline).split()
            if len(counts) != 2:
                raise DotError("failed to parse upstream counts")
            ahead, behind = (_count(value, "upstream") for value in counts)
        git_directory = _git(state, path, ["rev-parse", "--absolute-git-dir"], deadline).strip()
        if not git_directory:
            raise DotError("Git returned an empty metadata directory")
        metadata = Path(git_directory)
        operation = next(
            (
                label
                for marker, label in (
                    ("rebase-merge", "rebase"),
                    ("rebase-apply", "rebase"),
                    ("MERGE_HEAD", "merge"),
                    ("CHERRY_PICK_HEAD", "cherry-pick"),
                    ("REVERT_HEAD", "revert"),
                )
                if (metadata / marker).exists()
            ),
            "",
        )
        return RepositoryStatus(
            path.name,
            path.parent.name,
            branch,
            dirty,
            path=str(path),
            upstream=upstream,
            ahead=ahead,
            behind=behind,
            operation=operation,
        )
    except (DotError, OSError) as error:
        return RepositoryStatus(path.name, path.parent.name, error=str(error), path=str(path))


def gather_status(state: State, paths: Sequence[Path] = (), *, fetch: bool = False) -> list[RepositoryStatus]:
    """Collect repository status concurrently, optionally fetching (never merging) first."""
    require_tools(state, [["git"]])
    repositories = find_git_repositories(state, paths)
    return run_parallel(
        state.runner,
        lambda path: _repository_status(state, path, fetch=fetch),
        repositories,
        state.config.pull.concurrency,
    )


def run_status(
    state: State,
    *,
    as_json: bool = False,
    paths: Sequence[Path] = (),
    needs_attention: bool = False,
    fetch: bool = False,
) -> list[RepositoryStatus]:
    """Render repository status for humans or scripts."""
    status = gather_status(state, paths, fetch=fetch)
    failed = any(item.error for item in status)
    visible = [item for item in status if not needs_attention or item.needs_attention]
    if as_json:
        # Healthy entries omit the empty error field.
        repositories = [
            {key: value for key, value in asdict(item).items() if key != "error" or value}
            | {"needs_attention": item.needs_attention}
            for item in visible
        ]
        document = {
            "schema": "dot.status/v1",
            "repositories": repositories,
            "complete": not failed,
            "needs_attention": any(item.needs_attention for item in status),
            "remote_state": "fetched" if fetch else "cached",
        }
        write_json(state.stdout, document)
        if failed:
            raise DotError("repository inspection is incomplete")
        return status
    state.stdout.write("Git Repositories\n")
    if not status:
        state.stdout.write("  No repositories found in configured pull directories.\n")
    elif needs_attention and not visible:
        state.stdout.write(f"  ✓ All {len(status)} repositories are clean and in sync.\n")
    if not fetch:
        state.stdout.write("  Upstream counts use cached refs; pass --fetch to refresh.\n")
    for item in visible:
        dirty = " [dirty]" if item.dirty else ""
        tracking = f" ahead={item.ahead} behind={item.behind}" if item.upstream else " [no upstream]"
        state.stdout.write(
            f"  ▶ {item.parent}/{item.name} [{item.branch or 'error'}]{dirty}{tracking} {item.operation}\n"
        )
        if item.error:
            state.stdout.write(f"    ✗ {item.error}\n")
    if failed:
        raise DotError("repository inspection is incomplete")
    return status


def pull_command(
    context: typer.Context,
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Repositories to update; defaults to configured workspaces")
    ] = None,
    push: Annotated[bool, typer.Option("--push", "-P", help="Push clean repositories that are ahead")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="List targets without fetching or changing repositories")
    ] = False,
    as_json: JsonOption = False,
    dirty: Annotated[
        DirtyPolicy, typer.Option("--dirty", help="Dirty worktrees: skip (default) or allow fast-forward")
    ] = "skip",
) -> None:
    run_pull(state_from(context), push=push, paths=paths or (), dry_run=dry_run, as_json=as_json, dirty_policy=dirty)


def status_command(
    context: typer.Context,
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Repositories to inspect; defaults to configured workspaces")
    ] = None,
    as_json: JsonOption = False,
    needs_attention: Annotated[
        bool,
        typer.Option(
            "--needs-attention",
            help="Only show repositories that are dirty, diverged, untracked, mid-operation, or failed",
        ),
    ] = False,
    fetch: Annotated[
        bool, typer.Option("--fetch", "-f", help="Fetch each remote first (never merges) so ahead/behind are current")
    ] = False,
) -> None:
    run_status(state_from(context), as_json=as_json, paths=paths or (), needs_attention=needs_attention, fetch=fetch)


def register(parent: typer.Typer) -> None:
    parent.command("pull", help="Update configured repositories with bounded concurrency")(pull_command)
    parent.command(
        "status",
        help="Show repository status using cached upstream refs (--fetch refreshes them)",
        epilog="Exit 1 when any repository cannot be inspected; --json still prints every result.",
    )(status_command)
