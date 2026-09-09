"""Git repository, AI commit, pull request, pull, and status workflows."""

import json
import os
import shlex
import stat
import tempfile
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Annotated

import typer

from fmind_dot.commands import aliased_command
from fmind_dot.config import CommitConfig, PRConfig, duration_seconds, expand_path
from fmind_dot.errors import DotError
from fmind_dot.state import State

DEFAULT_AI_BINARY = "agy"
DEFAULT_MAX_DIFF_SIZE = 200_000
_SECURITY_MARKERS = ("auth", "credential", "permission", "secret", "security", ".github/workflows/")


@dataclass
class _DiffFile:
    path: str
    preamble: str
    hunks: list[str] = field(default_factory=list)
    added: int = 0
    deleted: int = 0


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


def _tool(state: State, name: str) -> Path:
    path = state.runner.which(name)
    if path is None:
        raise DotError(f"required tool is not installed: {name}")
    return path


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


def build_exclude_pathspecs(excludes: Iterable[str]) -> list[str]:
    """Build root-anchored pathspecs so AI input covers the whole repository."""
    return [":/", *(f":(exclude,top){pattern}" for pattern in excludes)]


def _git_diff(state: State, arguments: Sequence[str], excludes: Iterable[str], cwd: Path | None) -> str:
    _tool(state, "git")
    args = ["git", "diff", *arguments, "--", *build_exclude_pathspecs(excludes)]
    return state.runner.run(args, cwd=cwd).stdout


def get_cached_diff(state: State, *, excludes: Iterable[str] | None = None, cwd: Path | None = None) -> str:
    """Return the staged diff, optionally excluding configured path patterns."""
    selected = state.config.commit.exclude_diff if excludes is None else excludes
    return _git_diff(state, ["--cached"], selected, cwd)


def get_cached_diff_unfiltered(state: State, *, cwd: Path | None = None) -> str:
    """Return the complete staged diff for clean-index detection."""
    return _git_diff(state, ["--cached"], (), cwd)


def get_unstaged_diff(state: State, *, excludes: Iterable[str] | None = None, cwd: Path | None = None) -> str:
    """Return the unstaged tracked-file diff."""
    selected = state.config.commit.exclude_diff if excludes is None else excludes
    return _git_diff(state, (), selected, cwd)


def get_unstaged_diff_unfiltered(state: State, *, cwd: Path | None = None) -> str:
    """Return the complete unstaged tracked-file diff."""
    return _git_diff(state, (), (), cwd)


def get_base_diff(
    state: State,
    base_branch: str,
    *,
    excludes: Iterable[str] | None = None,
    cwd: Path | None = None,
) -> str:
    """Return the merge-base diff, falling back to a direct base diff."""
    selected = state.config.commit.exclude_diff if excludes is None else excludes
    try:
        return _git_diff(state, [f"{base_branch}..."], selected, cwd)
    except DotError:
        try:
            return _git_diff(state, [base_branch], selected, cwd)
        except DotError as error:
            raise DotError(f"failed to get git diff against {base_branch}") from error


def get_base_diff_unfiltered(state: State, base_branch: str, *, cwd: Path | None = None) -> str:
    """Return the complete branch diff for change detection."""
    return get_base_diff(state, base_branch, excludes=(), cwd=cwd)


def _decode_diff_path(value: str) -> str:
    try:
        parts = shlex.split(value)
    except ValueError:
        parts = [value.strip()]
    path = parts[-1] if parts else value.strip()
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def _parse_diff(diff: str) -> list[_DiffFile]:
    try:
        diff.encode("utf-8")
    except UnicodeEncodeError as error:
        raise DotError("diff is not valid UTF-8") from error
    files: list[_DiffFile] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            files.append(_DiffFile(path=_decode_diff_path(line.removeprefix("diff --git ")), preamble=line))
            continue
        if not files:
            if line.strip():
                raise DotError("input is not a unified Git diff")
            continue
        current = files[-1]
        if line.startswith(("@@ ", "@@@ ")):
            current.hunks.append(line)
            continue
        if not current.hunks:
            current.preamble += line
            if line.startswith(("--- ", "+++ ")):
                marker_path = _decode_diff_path(line[4:])
                if marker_path != "/dev/null":
                    current.path = marker_path
            continue
        current.hunks[-1] += line
        if line.startswith("+") and not line.startswith("+++"):
            current.added += 1
        elif line.startswith("-") and not line.startswith("---"):
            current.deleted += 1
    if not files:
        raise DotError("input contains no changed files")
    return files


def _security_sensitive(file: _DiffFile, unit: int) -> bool:
    text = file.path
    if file.hunks:
        text += "\n" + file.hunks[unit]
    lowered = text.lower()
    return any(marker in lowered for marker in _SECURITY_MARKERS)


def _diff_units(files: Sequence[_DiffFile]) -> list[tuple[int, int]]:
    security: list[tuple[int, int]] = []
    fair: list[tuple[int, int]] = []
    remaining: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    maximum = max((max(1, len(file.hunks)) for file in files), default=0)
    for file_index, file in enumerate(files):
        for unit in range(max(1, len(file.hunks))):
            candidate = (file_index, unit)
            if _security_sensitive(file, unit):
                security.append(candidate)
                seen.add(candidate)
    for unit in range(maximum):
        for file_index, file in enumerate(files):
            candidate = (file_index, unit)
            if unit >= max(1, len(file.hunks)) or candidate in seen:
                continue
            (fair if unit == 0 else remaining).append(candidate)
    return [*security, *fair, *remaining]


def _int_ranges(values: Sequence[int]) -> str:
    if not values:
        return "none"
    ranges: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def _render_packed_diff(diff: str, files: Sequence[_DiffFile], selected: Sequence[set[int]]) -> str:
    output = [
        "# Diff summary\n",
        f"files: {len(files)}\n",
        f"added_lines: {sum(file.added for file in files)}\n",
        f"deleted_lines: {sum(file.deleted for file in files)}\n",
        f"original_bytes: {len(diff.encode())}\n\n",
        "# Changed files\n",
    ]
    for index, file in enumerate(files):
        chosen = selected[index]
        units = file.hunks or [""]
        total = len(file.preamble.encode()) + sum(len(hunk.encode()) for hunk in file.hunks)
        included = 0 if not chosen else len(file.preamble.encode())
        included += sum(len(units[unit].encode()) for unit in chosen)
        omitted = [unit + 1 for unit in range(len(units)) if unit not in chosen]
        if not chosen:
            status = "omitted-file"
        elif included == total:
            status = "complete"
        else:
            status = "partial"
        output.append(
            f"- {file.path} | +{file.added} -{file.deleted} | status={status} | "
            f"omitted_hunks={_int_ranges(omitted)} | omitted_bytes={total - included}\n"
        )
    output.append("\n# Packed patch\n")
    for index, file in enumerate(files):
        if not selected[index]:
            continue
        output.append(file.preamble)
        output.extend(file.hunks[unit] for unit in sorted(selected[index]) if file.hunks)
    return "".join(output)


def pack_diff(diff: str, max_size: int = DEFAULT_MAX_DIFF_SIZE) -> str:
    """Pack a unified diff into an auditable, fairly sampled byte budget."""
    if max_size <= 0:
        max_size = DEFAULT_MAX_DIFF_SIZE
    files = _parse_diff(diff)
    selected = [set() for _ in files]
    payload = _render_packed_diff(diff, files, selected)
    if len(payload.encode()) > max_size:
        raise DotError(f"budget {max_size} bytes cannot hold the {len(payload.encode())}-byte omission manifest")
    for file_index, unit in _diff_units(files):
        selected[file_index].add(unit)
        candidate = _render_packed_diff(diff, files, selected)
        if len(candidate.encode()) <= max_size:
            payload = candidate
        else:
            selected[file_index].remove(unit)
    return payload


def scan_payload_for_secrets(state: State, payload: str) -> None:
    """Fail closed unless gitleaks accepts the exact outgoing payload."""
    scanner = _tool(state, "gitleaks")
    try:
        state.runner.run([str(scanner), "stdin", "--no-banner", "--redact"], input_text=payload)
    except DotError as error:
        raise DotError("outgoing payload secret scan failed") from error


def scan_diff_for_secrets(state: State, diff: str) -> None:
    """Scan the exact AI-bound diff with a diff-specific error."""
    try:
        scan_payload_for_secrets(state, diff)
    except DotError as error:
        raise DotError(f"outgoing diff secret scan failed: {error}") from error


def scan_prompt_for_secrets(state: State, prompt: str) -> None:
    """Scan the exact AI-bound prompt without exposing its contents."""
    try:
        scan_payload_for_secrets(state, prompt)
    except DotError as error:
        raise DotError(f"outgoing prompt secret scan failed: {error}") from error


def limit_ai_input(value: str, max_size: int) -> str:
    """Truncate text on a UTF-8 boundary without exceeding the byte limit."""
    limit = max_size if max_size > 0 else DEFAULT_MAX_DIFF_SIZE
    raw = value.encode()
    if len(raw) <= limit:
        return value
    return raw[:limit].decode("utf-8", errors="ignore")


def generate_text(state: State, prompt: str, input_text: str, max_size: int = DEFAULT_MAX_DIFF_SIZE) -> str:
    """Invoke the configured AI binary from an isolated temporary directory."""
    binary = state.config.ai.binary or DEFAULT_AI_BINARY
    executable = _tool(state, binary)
    args = [str(executable), "--prompt", prompt]
    if Path(binary).name == DEFAULT_AI_BINARY:
        args.insert(1, "--sandbox")
    try:
        with tempfile.TemporaryDirectory(prefix="dot-ai-") as directory:
            output = state.runner.run(
                args,
                cwd=Path(directory),
                input_text=limit_ai_input(input_text, max_size),
            ).stdout.strip()
    except DotError as error:
        raise DotError("AI invocation failed") from error
    if not output:
        raise DotError("AI returned empty output")
    return output


def _rollback_index(state: State, root: Path, cause: BaseException) -> None:
    try:
        state.runner.run(["git", "reset", "--mixed"], cwd=root)
    except DotError as rollback_error:
        raise DotError(f"{cause}; failed to restore initially clean index") from rollback_error


def run_commit(
    state: State,
    commit_type: str = "",
    scope: str = "",
    *,
    all_changes: bool = False,
    cwd: Path | None = None,
) -> str | None:
    """Generate a Conventional Commit message and open the git editor."""
    root = git_root(state, cwd)
    auto_staged = False
    try:
        complete_diff = get_cached_diff_unfiltered(state, cwd=root)
        if not complete_diff.strip():
            status = state.runner.run(["git", "status", "--porcelain"], cwd=root).stdout
            if not status.strip():
                state.stdout.write("No changes to commit.\n")
                return None
            if not all_changes:
                raise DotError("no staged changes; stage the intended files or use --all")
            auto_staged = True
            state.runner.run(["git", "add", "-A"], cwd=root)
            complete_diff = get_cached_diff_unfiltered(state, cwd=root)
            if not complete_diff.strip():
                raise DotError("git add -A completed without producing a staged diff")
            state.stdout.write("No staged changes found. Staged all working tree changes.\n")
        diff = get_cached_diff(state, cwd=root)
        if not diff.strip():
            raise DotError("git changes exist, but every changed path is excluded from AI diff generation")
        prompt = state.config.commit.prompt or CommitConfig().prompt
        allowed = ", ".join(state.config.commit.allowed_types)
        if "%s" in prompt:
            prompt %= allowed
        if commit_type and scope:
            prompt += f" Use type '{commit_type}' and scope '{scope}'."
        elif commit_type:
            prompt += f" Suggest a scope and use '{commit_type}' as the type."
        elif scope:
            prompt += f" Use scope '{scope}' and suggest an appropriate type."
        packed = pack_diff(diff, state.config.commit.max_diff_size)
        scan_diff_for_secrets(state, packed)
        message = generate_text(state, prompt, packed, state.config.commit.max_diff_size)
        paths = state.runner.run(["git", "diff", "--cached", "--name-only", "-z", "--", ":/"], cwd=root).stdout.split(
            "\0"
        )
        selected = [path for path in paths if path]
        state.stdout.write(f"Staged files ({len(selected)}):\n")
        for path in selected:
            display = path.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            state.stdout.write(f"  {display}\n")
        code = state.runner.interactive(
            ["git", "commit", "-e", "-m", message],
            cwd=root,
            stdin=state.stdin,
            stdout=state.stdout,
            stderr=state.stderr,
        )
        if code:
            raise DotError(f"git commit failed with status {code}")
    except BaseException as error:
        # Auto-staging is transactional even when the user interrupts the editor.
        if auto_staged:
            _rollback_index(state, root, error)
        raise
    return message


def _pr_template(root: Path, paths: Iterable[str]) -> str:
    for configured in paths:
        path = Path(configured)
        relative = not path.is_absolute()
        path = path if not relative else root / path
        try:
            info = path.lstat() if relative else path.stat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise DotError(f"failed to inspect PR template {configured}") from error
        if relative:
            if not stat.S_ISREG(info.st_mode):
                raise DotError(f"relative PR template must be a regular file: {configured}")
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root.resolve(strict=True))
            except ValueError as error:
                raise DotError(f"relative PR template escapes repository root: {configured}") from error
            except (OSError, RuntimeError) as error:
                raise DotError(f"failed to inspect PR template {configured}") from error
            path = resolved
        if stat.S_ISDIR(info.st_mode):
            continue
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise DotError(f"failed to read PR template {configured}") from error
    return ""


def run_pull_request(
    state: State,
    *,
    base: str | None = None,
    title: str = "",
    draft: bool = False,
    labels: Sequence[str] = (),
    reviewers: Sequence[str] = (),
    assignees: Sequence[str] = (),
    cwd: Path | None = None,
    print_only: bool = False,
    body_file: Path | None = None,
    yes: bool = False,
) -> str | None:
    """Generate a reviewed PR body and invoke ``gh pr create``."""
    if print_only and yes:
        raise DotError("--print and --yes are mutually exclusive")
    root = git_root(state, cwd)
    gh = _tool(state, "gh") if not print_only else None
    base_branch = base or state.config.pr.base_branch
    complete_diff = get_base_diff_unfiltered(state, base_branch, cwd=root)
    if not complete_diff.strip():
        state.stdout.write(f"No changes detected against base branch '{base_branch}'.\n")
        return None
    diff = get_base_diff(state, base_branch, cwd=root)
    if not diff.strip():
        raise DotError(
            f"changes exist against base branch {base_branch!r}, but every changed path is excluded from AI diff generation"
        )
    prompt = state.config.pr.prompt or PRConfig().prompt
    template = _pr_template(root, state.config.pr.templates or PRConfig().templates)
    if template:
        prompt += "\n\nFollow the repository pull request template below:\n\n" + template
    packed = pack_diff(diff, state.config.commit.max_diff_size)
    scan_prompt_for_secrets(state, prompt)
    scan_diff_for_secrets(state, packed)
    description = (
        body_file.read_text(encoding="utf-8")
        if body_file
        else generate_text(state, prompt, packed, state.config.commit.max_diff_size)
    )
    if print_only:
        state.stdout.write(description.rstrip() + "\n")
        return description
    if not description.strip():
        raise DotError("pull request body is empty")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="dot-pr-", suffix=".md", delete=False
    ) as stream:
        stream.write(description)
        body_path = Path(stream.name)
    published = False
    try:
        if not yes:
            editor = shlex.split(os.environ.get("EDITOR", "vi")) or ["vi"]
            _tool(state, editor[0])
            code = state.runner.interactive(
                [*editor, str(body_path)], cwd=root, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr
            )
            if code:
                raise DotError(f"PR editor exited with status {code}")
        description = body_path.read_text(encoding="utf-8")
        if not description.strip():
            raise DotError("pull request body is empty; publication cancelled")
        scan_payload_for_secrets(state, description)
        args = [str(gh), "pr", "create", "--base", base_branch, "--body-file", str(body_path)]
        if title:
            args.extend(["--title", title])
        if draft:
            args.append("--draft")
        for option, values in (("--label", labels), ("--reviewer", reviewers), ("--assignee", assignees)):
            for value in values:
                args.extend([option, value])
        code = state.runner.interactive(
            args,
            cwd=root,
            stdin=state.stdin,
            stdout=state.stdout,
            stderr=state.stderr,
        )
        if code:
            raise DotError(f"gh pr create failed with status {code}")
        published = True
    finally:
        if published:
            body_path.unlink(missing_ok=True)
        else:
            state.stderr.write(f"PR body retained at {body_path}; retry with dot pr --body-file {body_path}\n")
    return description


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
    timeout = duration_seconds(state.config.pull.timeout)
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


def commit_command(
    context: typer.Context,
    commit_type: Annotated[str, typer.Option("--type", "-t", help="Conventional Commit type")] = "",
    scope: Annotated[str, typer.Option("--scope", "-s", help="Conventional Commit scope")] = "",
    all_changes: Annotated[
        bool, typer.Option("--all", help="Stage the whole worktree when the index is empty")
    ] = False,
) -> None:
    run_commit(_state_from(context), commit_type, scope, all_changes=all_changes)


def pull_request_command(
    context: typer.Context,
    base: Annotated[str | None, typer.Option("--base", "-b", help="Base branch to diff against")] = None,
    title: Annotated[str, typer.Option("--title", "-t", help="Pull request title")] = "",
    draft: Annotated[bool, typer.Option("--draft", "-d", help="Create a draft pull request")] = False,
    label: Annotated[list[str] | None, typer.Option("--label", "-l", help="Label to add")] = None,
    reviewer: Annotated[list[str] | None, typer.Option("--reviewer", "-r", help="Reviewer to request")] = None,
    assignee: Annotated[list[str] | None, typer.Option("--assignee", "-a", help="Assignee to add")] = None,
    print_only: Annotated[
        bool, typer.Option("--print", help="Print the body without creating a PR or pushing")
    ] = False,
    body_file: Annotated[
        Path | None,
        typer.Option("--body-file", exists=True, dir_okay=False, help="Reuse a prepared body without AI generation"),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Publish without opening the editor")] = False,
) -> None:
    if not print_only and not yes and not _state_from(context).stdin.isatty():
        raise DotError("PR review needs a terminal; use --print or provide --yes to publish without the editor")
    run_pull_request(
        _state_from(context),
        base=base,
        title=title,
        draft=draft,
        labels=label or (),
        reviewers=reviewer or (),
        assignees=assignee or (),
        print_only=print_only,
        body_file=body_file,
        yes=yes,
    )


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
    """Register the repository command surface."""
    commands = (
        (commit_command, "commit", (), "Generate and apply an AI-authored Conventional Commit message"),
        (pull_request_command, "pull-request", ("pr",), "Generate a pull request body and invoke gh"),
        (pull_command, "pull", (), "Update configured Git repositories concurrently"),
        (status_command, "status", (), "Show Git repository and Docker status"),
    )
    for callback, name, aliases, help_text in commands:
        aliased_command(parent, name, *aliases, help_text=help_text)(callback)
