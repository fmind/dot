"""Bounded multi-repository synchronization and status."""

import json
import stat
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Annotated

import typer

from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.state import State


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
class DockerStatus:
    """Availability and health of the local Docker daemon."""

    installed: bool = False
    running: bool = False
    details: str = ""


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


@dataclass(frozen=True)
class SystemStatus:
    """Combined Docker and configured repository status."""

    docker: DockerStatus
    repositories: list[RepositoryStatus]


def git_root(state: State, cwd: Path | None = None) -> Path:
    """Resolve the repository root and fail with a safe diagnostic."""
    _tool(state, "git")
    try:
        output = state.runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).stdout.strip()
    except DotError as error:
        raise DotError("current directory is not inside a git work tree") from error
    if not output:
        raise DotError("git returned an empty repository root")
    return Path(output)


def _tool(state: State, name: str) -> Path:
    path = state.runner.which(name)
    if path is None:
        raise DotError(f"required tool is not installed: {name}")
    return path


def find_git_repositories(state: State, paths: Sequence[Path] = ()) -> list[Path]:
    """Resolve explicit repositories or direct children of configured workspaces."""
    if paths:
        return sorted({git_root(state, expand_path(path)).resolve() for path in paths})
    repositories: list[Path] = []
    for configured in state.config.pull.directories:
        root = expand_path(configured)
        if (root / ".git").exists():
            repositories.append(root.resolve())
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


def _branch(state: State, path: Path, deadline: float) -> str:
    branch = state.runner.run(
        ["git", "branch", "--show-current"], cwd=path, timeout=_remaining_timeout(deadline)
    ).stdout.strip()
    if branch:
        return branch
    return state.runner.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=path, timeout=_remaining_timeout(deadline)
    ).stdout.strip()


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
    cancelled: Event | None = None,
    *,
    dirty_policy: str = "skip",
) -> RepoResult:
    deadline = monotonic() + timeout
    branch = ""
    dirty = False

    def git(arguments: Sequence[str], *, check: bool = True) -> str:
        if cancelled is not None and cancelled.is_set():
            raise DotError("operation cancelled")
        return state.runner.run(
            ["git", *arguments],
            cwd=path,
            timeout=_remaining_timeout(deadline),
            check=check,
        ).stdout

    def has_upstream() -> bool:
        result = state.runner.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=path,
            timeout=_remaining_timeout(deadline),
            check=False,
        )
        return result.returncode == 0

    try:
        branch = _branch(state, path, deadline)
        dirty = bool(git(["status", "--porcelain"]).strip())
        if dirty and dirty_policy == "skip":
            return RepoResult(path=path, branch=branch, dirty=True, skipped="dirty worktree")
        try:
            git(["fetch", "--prune"])
        except DotError as fetch_error:
            try:
                upstream = has_upstream()
            except DotError as upstream_error:
                raise DotError(f"failed to inspect upstream after fetch failure: {upstream_error}") from upstream_error
            if not upstream:
                return RepoResult(path=path, branch=branch, dirty=dirty, no_upstream=True)
            raise DotError(f"failed to fetch repository: {fetch_error}") from fetch_error
        try:
            upstream = has_upstream()
        except DotError as upstream_error:
            raise DotError(f"failed to inspect upstream: {upstream_error}") from upstream_error
        if not upstream:
            return RepoResult(path=path, branch=branch, dirty=dirty, no_upstream=True)
        behind_raw = git(["rev-list", "--count", "HEAD..@{u}"])
        behind = _count(behind_raw, "behind")
        git(["pull", "--ff-only"])
        ahead = _count(git(["rev-list", "--count", "@{u}..HEAD"]), "ahead")
        pushed = False
        push_error = ""
        if push and ahead and not dirty:
            try:
                git(["push"])
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
    except DotError as error:
        return RepoResult(path=path, branch=branch, dirty=dirty, error=str(error))


def run_pull(
    state: State,
    *,
    push: bool = False,
    paths: Sequence[Path] = (),
    dry_run: bool = False,
    as_json: bool = False,
    dirty_policy: str = "skip",
) -> list[RepoResult]:
    """Fetch and fast-forward configured repositories concurrently."""
    _tool(state, "git")
    if dirty_policy not in {"skip", "allow"}:
        raise DotError("--dirty must be skip or allow")
    repositories = find_git_repositories(state, paths) if paths else find_git_repositories(state)
    if dry_run:
        plan = {
            "schema": "dot.pull.plan/v1",
            "remote_state": "not refreshed",
            "push": push,
            "dirty_policy": dirty_policy,
            "repositories": [str(path) for path in repositories],
        }
        if as_json:
            state.stdout.write(json.dumps(plan, indent=2) + "\n")
        else:
            state.stdout.write(f"Pull plan (no fetch or changes): dirty={dirty_policy}, push={push}\n")
            for path in repositories:
                state.stdout.write(f"  {path}\n")
        return []
    if not repositories:
        state.stdout.write("[]\n" if as_json else "No git repositories found in configured pull directories.\n")
        return []
    timeout = state.config.pull.timeout_seconds
    cancelled = Event()
    executor = ThreadPoolExecutor(max_workers=state.config.pull.concurrency)
    try:
        results = list(
            executor.map(
                lambda path: _pull_repository(state, path, push, timeout, cancelled, dirty_policy=dirty_policy),
                repositories,
            )
        )
    except BaseException:
        cancelled.set()
        state.runner.cancel()
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    if as_json:
        state.stdout.write(json.dumps([asdict(item) | {"path": str(item.path)} for item in results], indent=2) + "\n")
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


def _docker_status(state: State) -> DockerStatus:
    docker = state.runner.which("docker")
    if docker is None:
        return DockerStatus(details="command not found")
    try:
        details = state.runner.run(
            [
                str(docker),
                "info",
                "--format",
                "{{.Name}} (Containers: {{.Containers}}, Running: {{.ContainersRunning}})",
            ],
            timeout=30,
        ).stdout.strip()
    except DotError:
        return DockerStatus(installed=True, details="inspection command failed")
    if not details or "(Containers:" not in details or ", Running:" not in details:
        return DockerStatus(installed=True, details="inspection returned malformed output" if details else "")
    return DockerStatus(installed=True, running=True, details=details)


def _repository_status(state: State, path: Path) -> RepositoryStatus:
    deadline = monotonic() + 30
    try:
        branch = _branch(state, path, deadline)
        dirty = bool(
            state.runner.run(
                ["git", "status", "--porcelain"], cwd=path, timeout=_remaining_timeout(deadline)
            ).stdout.strip()
        )
        upstream_result = state.runner.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=path,
            timeout=_remaining_timeout(deadline),
            check=False,
        )
        upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else ""
        ahead = behind = 0
        if upstream:
            counts = state.runner.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
                cwd=path,
                timeout=_remaining_timeout(deadline),
            ).stdout.split()
            if len(counts) != 2:
                raise DotError("failed to parse upstream counts")
            ahead, behind = (_count(value, "upstream") for value in counts)
        git_directory = state.runner.run(
            ["git", "rev-parse", "--absolute-git-dir"], cwd=path, timeout=_remaining_timeout(deadline)
        ).stdout.strip()
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
    except DotError as error:
        return RepositoryStatus(path.name, path.parent.name, error=str(error), path=str(path))


def gather_status(state: State, paths: Sequence[Path] = ()) -> SystemStatus:
    """Collect Docker and repository status concurrently."""
    _tool(state, "git")
    repositories = find_git_repositories(state, paths) if paths else find_git_repositories(state)
    with ThreadPoolExecutor(max_workers=8) as executor:
        docker_future = executor.submit(_docker_status, state)
        repo_statuses = list(executor.map(lambda path: _repository_status(state, path), repositories))
    return SystemStatus(docker=docker_future.result(), repositories=repo_statuses)


def run_status(
    state: State,
    *,
    as_json: bool = False,
    paths: Sequence[Path] = (),
    needs_attention: bool = False,
    stats: bool = False,
) -> SystemStatus:
    """Render Docker and repository status for humans or scripts."""
    status = gather_status(state, paths) if paths else gather_status(state)
    failed = any(item.error for item in status.repositories)
    if stats:
        totals = {
            "repositories": len(status.repositories),
            "dirty": sum(item.dirty for item in status.repositories),
            "ahead": sum(item.ahead > 0 for item in status.repositories),
            "behind": sum(item.behind > 0 for item in status.repositories),
            "diverged": sum(item.ahead > 0 and item.behind > 0 for item in status.repositories),
            "no_upstream": sum(not item.upstream and not item.error for item in status.repositories),
            "in_progress": sum(bool(item.operation) for item in status.repositories),
            "errors": sum(bool(item.error) for item in status.repositories),
        }
        document = {"schema": "dot.status.stats/v1", "remote_state": "cached", "complete": not failed, **totals}
        state.stdout.write(
            json.dumps(document, indent=2) + "\n"
            if as_json
            else "Repository statistics (cached upstream state)\n"
            + "".join(f"{key}: {value}\n" for key, value in totals.items())
        )
        if failed:
            raise DotError("repository statistics are incomplete")
        return status
    visible = [item for item in status.repositories if not needs_attention or item.needs_attention]
    if as_json:
        docker: dict[str, object] = {
            "installed": status.docker.installed,
            "running": status.docker.running,
        }
        if status.docker.details:
            docker["details"] = status.docker.details
        repositories: list[dict[str, object]] = []
        for item in visible:
            repository: dict[str, object] = {
                "name": item.name,
                "parent": item.parent,
                "branch": item.branch,
                "dirty": item.dirty,
                "path": item.path,
                "upstream": item.upstream,
                "ahead": item.ahead,
                "behind": item.behind,
                "operation": item.operation,
            }
            if item.error:
                repository["error"] = item.error
            repositories.append(repository)
        document = {
            "docker": docker,
            "repositories": repositories,
            "complete": not failed,
            "remote_state": "cached",
        }
        state.stdout.write(json.dumps(document, indent=2) + "\n")
        if failed:
            raise DotError("repository inspection is incomplete")
        return status
    state.stdout.write("Docker Daemon\n")
    if not status.docker.installed:
        state.stdout.write("  ✗ Not installed.\n")
    elif status.docker.running:
        state.stdout.write(f"  ✓ Running: {status.docker.details}\n")
    else:
        detail = f": {status.docker.details}" if status.docker.details else ""
        state.stdout.write(f"  ✗ Stopped or unreachable{detail}.\n")
    state.stdout.write("\nGit Repositories\n")
    if not status.repositories:
        state.stdout.write("  No repositories found in configured pull directories.\n")
    state.stdout.write("  Upstream counts use cached refs; fetch explicitly to refresh.\n")
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


def _state_from(context: typer.Context) -> State:
    state = context.find_root().obj
    if not isinstance(state, State):
        raise DotError("CLI state is unavailable")
    return state


def pull_command(
    context: typer.Context,
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Repositories to update; defaults to configured workspaces")
    ] = None,
    push: Annotated[bool, typer.Option("--push", "-P", help="Push clean repositories that are ahead")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="List targets without fetching or changing repositories")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    dirty: Annotated[
        str, typer.Option("--dirty", help="Dirty worktrees: skip (default) or allow fast-forward")
    ] = "skip",
) -> None:
    run_pull(_state_from(context), push=push, paths=paths or (), dry_run=dry_run, as_json=as_json, dirty_policy=dirty)


def status_command(
    context: typer.Context,
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Repositories to inspect; defaults to configured workspaces")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Emit structured JSON")] = False,
    needs_attention: Annotated[
        bool, typer.Option("--needs-attention", help="Only show repositories requiring attention")
    ] = False,
    stats: Annotated[bool, typer.Option("--stats", help="Summarize repository health counts")] = False,
) -> None:
    run_status(_state_from(context), as_json=as_json, paths=paths or (), needs_attention=needs_attention, stats=stats)


def register_repository_commands(parent: typer.Typer) -> None:
    parent.command("pull", help="Update configured repositories with bounded concurrency")(pull_command)
    parent.command("status", help="Show repository and Docker status")(status_command)
