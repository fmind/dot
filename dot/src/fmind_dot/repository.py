"""Bounded multi-repository synchronization and status."""

import stat
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from time import monotonic

from fmind_dot.command import Parser, add_json
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError, NotGitWorkTreeError
from fmind_dot.process import CommandResult, diagnostic_line, run_parallel
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools

_STATUS_BRANCH = ("--no-optional-locks", "status", "--porcelain=v2", "--branch")
_PULL_TIMEOUT_SECONDS = 120.0
_STATUS_TIMEOUT_SECONDS = 30.0
_PULL_CONCURRENCY = 8
_GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS_REQUIRE": "never"}
_OPS = (
    ("rebase-merge", "rebase"),
    ("rebase-apply", "rebase"),
    ("MERGE_HEAD", "merge"),
    ("CHERRY_PICK_HEAD", "cherry-pick"),
    ("REVERT_HEAD", "revert"),
)


@dataclass(frozen=True)
class RepoResult:
    path: Path
    branch: str = ""
    commits: int = 0
    ahead: int = 0
    dirty: bool = False
    no_upstream: bool = False
    error: str = ""
    skipped: str = ""


@dataclass(frozen=True)
class RepositoryStatus:
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


def git_failure(arguments: Sequence[str], result: CommandResult) -> str:
    """Describe a failed git command using its sanitized first error line."""
    subcommand = next((a for a in arguments if not a.startswith("-")), "command")
    first = next(
        (ln.strip() for ln in result.stderr.splitlines() if ln.strip().startswith(("error:", "fatal:", "!"))), ""
    )
    cause = diagnostic_line(first or result.stderr or result.stdout)
    return f"git {subcommand} failed ({result.returncode})" + (f": {cause}" if cause else "")


def _git(state: State, path: Path, arguments: Sequence[str], deadline: float) -> str:
    if (remaining := deadline - monotonic()) <= 0:
        raise DotError("repository operation timed out")
    result = state.runner.run(["git", *arguments], cwd=path, env=_GIT_ENV, timeout=remaining, check=False)
    if result.returncode:
        raise DotError(git_failure(arguments, result))
    return result.stdout


def _fetch(state: State, path: Path, deadline: float) -> None:
    try:
        _git(state, path, ["fetch", "--prune"], deadline)
    except DotError as error:
        raise DotError(f"failed to fetch repository: {error}") from error


def git_root(state: State, cwd: Path | None = None) -> Path:
    require_tools(state, [["git"]])
    location = str(cwd) if cwd is not None else "current directory"
    try:
        result = state.runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, timeout=30, check=False)
    except (DotError, OSError) as error:
        raise DotError(f"failed to inspect {location} with git: {getattr(error, 'strerror', None) or error}") from error
    if result.returncode:
        raise NotGitWorkTreeError(f"{location} is not inside a git work tree")
    if not (output := result.stdout.strip()):
        raise DotError("git returned an empty repository root")
    return Path(output)


def find_git_repositories(state: State, paths: Sequence[Path] = ()) -> list[Path]:
    """Resolve explicit repositories or direct children of configured workspaces."""
    if paths:
        return sorted({git_root(state, expand_path(p)).resolve() for p in paths})
    repositories: set[Path] = set()
    for configured in state.config.pull.directories:
        root = expand_path(configured).resolve()
        if (root / ".git").exists():
            repositories.add(root)
            continue
        try:
            entries = sorted(root.iterdir(), key=lambda p: p.name)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise DotError(f"failed to inspect repository workspace {root}: {error}") from error
        for path in entries:
            try:
                if stat.S_ISDIR(path.lstat().st_mode):
                    (path / ".git").stat()
                    repositories.add(path)
            except FileNotFoundError:
                continue
            except OSError as error:
                raise DotError(f"failed to inspect repository {path}: {error}") from error
    return sorted(repositories)


def _branch_status(state: State, path: Path, deadline: float) -> tuple[str, bool, str, int, int]:
    branch = upstream = ""
    counts: list[str] | None = None
    dirty = False
    for line in _git(state, path, _STATUS_BRANCH, deadline).splitlines():
        if not line.startswith("# "):
            dirty = dirty or bool(line.strip())
            continue
        key, _, value = line[2:].partition(" ")
        if key == "branch.head":
            branch = value.strip()
        elif key == "branch.upstream":
            upstream = value.strip()
        elif key == "branch.ab":
            counts = value.split()
    if not branch:
        raise DotError("failed to parse branch status")
    if branch == "(detached)":
        branch = _git(state, path, ["rev-parse", "--short", "HEAD"], deadline).strip()
    if counts is None:
        return branch, dirty, "", 0, 0
    if len(counts) != 2 or not counts[0].startswith("+") or not counts[1].startswith("-"):
        raise DotError("failed to parse upstream counts")
    try:
        return branch, dirty, upstream, int(counts[0][1:]), int(counts[1][1:])
    except ValueError as error:
        raise DotError("failed to parse upstream count") from error


def _pull_repository(state: State, path: Path) -> RepoResult:
    deadline = monotonic() + _PULL_TIMEOUT_SECONDS
    branch, dirty = "", False
    try:
        branch, dirty, *_ = _branch_status(state, path, deadline)
        if dirty:
            return RepoResult(path=path, branch=branch, dirty=True, skipped="dirty worktree")
        _fetch(state, path, deadline)
        branch, dirty, upstream, ahead, behind = _branch_status(state, path, deadline)
        if dirty:
            return RepoResult(path=path, branch=branch, dirty=True, skipped="dirty worktree")
        if not upstream:
            return RepoResult(path=path, branch=branch, no_upstream=True)
        if ahead and behind:
            return RepoResult(
                path=path,
                branch=branch,
                ahead=ahead,
                error=f"diverged from upstream ({ahead} ahead, {behind} behind); merge or rebase it yourself",
            )
        if behind:
            _git(state, path, ["merge", "--ff-only", "@{u}"], deadline)
        return RepoResult(path=path, branch=branch, commits=behind, ahead=ahead, dirty=dirty)
    except (DotError, OSError) as error:
        return RepoResult(path=path, branch=branch, dirty=dirty, error=str(error))


def run_pull(state: State, *, paths: Sequence[Path] = (), as_json: bool = False) -> list[RepoResult]:
    """Fetch and fast-forward configured repositories concurrently."""
    require_tools(state, [["git"]])
    results = run_parallel(
        state.runner, lambda p: _pull_repository(state, p), find_git_repositories(state, paths), _PULL_CONCURRENCY
    )
    if as_json:
        repos = [asdict(r) | {"path": str(r.path)} for r in results]
        write_json(
            state.stdout,
            {"schema": "dot.pull/v1", "complete": not any(r.error for r in results), "repositories": repos},
        )
        if any(item.error for item in results):
            raise DotError("pull completed with repository errors")
        return results
    if not results:
        state.stdout.write("No git repositories found in configured pull directories.\n")
        return []
    failures = 0
    for item in results:
        flags = (" [dirty]" if item.dirty else "") + (" [no upstream]" if item.no_upstream else "")
        state.stdout.write(f"▶ {item.path.parent.name}/{item.path.name} [{item.branch or 'error'}]{flags}\n")
        if item.error:
            failures += 1
            state.stdout.write(f"  ✗ Pull failed: {item.error}\n")
        elif item.skipped or item.no_upstream:
            state.stdout.write(f"  ∅ skipped ({item.skipped or 'no upstream'})\n")
        else:
            detail = f"pulled {item.commits} commit(s)" if item.commits else "up to date"
            state.stdout.write(f"  ✓ Pull successful ({detail})\n")
            if item.ahead:
                state.stdout.write(f"  ↑ {item.ahead} unpushed\n")
    if failures:
        raise DotError(f"failed to pull {failures} repositories")
    return results


def _repository_status(state: State, path: Path, *, fetch: bool = False) -> RepositoryStatus:
    deadline = monotonic() + (_PULL_TIMEOUT_SECONDS if fetch else _STATUS_TIMEOUT_SECONDS)
    try:
        if fetch:
            _fetch(state, path, deadline)
        branch, dirty, upstream, ahead, behind = _branch_status(state, path, deadline)
        if not (git_dir := _git(state, path, ["rev-parse", "--absolute-git-dir"], deadline).strip()):
            raise DotError("Git returned an empty metadata directory")
        operation = next((label for marker, label in _OPS if (Path(git_dir) / marker).exists()), "")
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
    require_tools(state, [["git"]])
    return run_parallel(
        state.runner,
        lambda p: _repository_status(state, p, fetch=fetch),
        find_git_repositories(state, paths),
        _PULL_CONCURRENCY,
    )


def run_status(
    state: State,
    *,
    as_json: bool = False,
    paths: Sequence[Path] = (),
    needs_attention: bool = False,
    fetch: bool = False,
) -> list[RepositoryStatus]:
    status = gather_status(state, paths, fetch=fetch)
    failed = any(item.error for item in status)
    visible = [item for item in status if not needs_attention or item.needs_attention]
    if as_json:
        repos = [
            {k: v for k, v in asdict(i).items() if k != "error" or v} | {"needs_attention": i.needs_attention}
            for i in visible
        ]
        attn, state_name = any(i.needs_attention for i in status), "fetched" if fetch else "cached"
        write_json(
            state.stdout,
            {
                "schema": "dot.status/v1",
                "repositories": repos,
                "complete": not failed,
                "needs_attention": attn,
                "remote_state": state_name,
            },
        )
    else:
        lines = ["Git Repositories\n"]
        if not status:
            lines.append("  No repositories found in configured pull directories.\n")
        elif needs_attention and not visible:
            lines.append(f"  ✓ All {len(status)} repositories are clean and in sync.\n")
        if not fetch:
            lines.append("  Upstream counts use cached refs; pass --fetch to refresh.\n")
        for item in visible:
            dirty = " [dirty]" if item.dirty else ""
            tracking = (
                "" if item.error else f" ahead={item.ahead} behind={item.behind}" if item.upstream else " [no upstream]"
            )
            op = f" {item.operation}" if item.operation else ""
            lines.append(f"  ▶ {item.parent}/{item.name} [{item.branch or 'error'}]{dirty}{tracking}{op}\n")
            if item.error:
                lines.append(f"    ✗ {item.error}\n")
        state.stdout.writelines(lines)
    if failed:
        raise DotError("repository inspection is incomplete")
    return status


def register_pull(commands: Parser) -> None:
    msg = (
        "Skips dirty worktrees and branches without an upstream, and reports diverged branches without changing them. "
        "Exit 1 when any repository fails or diverged.\n\n"
        "Examples: dot pull · dot pull ~/fmind/dot --json"
    )
    p = commands.command(
        "pull",
        "Fast-forward configured repositories; never merges, rebases, or touches dirty checkouts",
        lambda state, args: run_pull(state, paths=args.paths, as_json=args.as_json),
        epilog=msg,
    )
    p.add_argument("paths", nargs="*", type=Path, help="Repositories to update; defaults to configured workspaces")
    add_json(p)


def register_status(commands: Parser) -> None:
    s = commands.command(
        "status",
        "Show repository status using cached upstream refs (--fetch refreshes them)",
        lambda state, args: run_status(
            state, as_json=args.as_json, paths=args.paths, needs_attention=args.needs_attention, fetch=args.fetch
        ),
        epilog=(
            "Exit 1 when any repository cannot be inspected; --json still prints every result.\n\n"
            "Examples: dot status --needs-attention · dot status --fetch --json"
        ),
    )
    s.add_argument("paths", nargs="*", type=Path, help="Repositories to inspect; defaults to configured workspaces")
    add_json(s)
    s.add_argument("--needs-attention", action="store_true", help="Only report repositories needing attention")
    s.add_argument("-f", "--fetch", action="store_true", help="Fetch remotes first so ahead/behind are current")
