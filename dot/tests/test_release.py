from __future__ import annotations

import io
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO

import pytest

from dot_tasks.release import read_release_version, run_release, validate_release_status
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State

TAG = "v1.27.0"
GIT_CLIFF_BUMPED = ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version")
RESTORE = ("git", "restore", "--staged", "--worktree", "--", "CHANGELOG.md", "dot/pyproject.toml", "dot/uv.lock")
PUSH = ("git", "push", "--atomic", "origin", "HEAD:refs/heads/main", f"refs/tags/{TAG}")
COMMIT = ("git", "commit", "-m", f"chore(release): {TAG}")
DEPLOY = ("mise", "run", "deploy")


class ReleaseRunner(Runner):
    """Record git, git-cliff, and mise while running uv's real version and lock writer offline."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.calls: list[tuple[str, ...]] = []
        self.interactive_calls: list[tuple[str, ...]] = []
        self.installed = {"dprint", "git", "git-cliff", "mise", "uv"}
        self.responses: dict[tuple[str, ...], CommandResult | BaseException] = {
            ("git", "rev-parse", "--show-toplevel"): CommandResult(str(root), "", 0),
            ("git", "branch", "--show-current"): CommandResult("main", "", 0),
            ("git", "rev-parse", "HEAD"): CommandResult("b" * 40, "", 0),
            ("git", "rev-parse", "origin/main"): CommandResult("b" * 40, "", 0),
            GIT_CLIFF_BUMPED: CommandResult(TAG, "", 0),
            ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"): CommandResult(
                " M CHANGELOG.md\0 M dot/pyproject.toml\0 M dot/uv.lock\0", "", 0
            ),
        }
        self.interactive_codes: dict[tuple[str, ...], int | BaseException] = {}

    def which(self, command: str) -> Path | None:
        return Path("/usr/bin") / command if command in self.installed else None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        del input_text
        call = tuple(args)
        self.calls.append(call)
        if args[0] == "uv":
            return Runner().run(args, cwd=cwd, env={**(env or {}), "UV_OFFLINE": "1"}, timeout=timeout)
        response = self.responses.get(call, CommandResult("", "", 0))
        if isinstance(response, BaseException):
            raise response
        if check and response.returncode != 0:
            raise DotError(f"command failed ({response.returncode}): {args[0]}")
        return response

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stderr_line: Callable[[str], None] | None = None,
    ) -> int:
        del cwd, stdin, stdout, stderr, env, on_stderr_line
        call = tuple(args)
        self.interactive_calls.append(call)
        code = self.interactive_codes.get(call, 0)
        if isinstance(code, BaseException):
            raise code
        return code


def make_state(runner: Runner) -> State:
    return State(runner=runner, stdin=io.StringIO(), stdout=io.StringIO(), stderr=io.StringIO())


@pytest.fixture
def project(tmp_path: Path) -> Path:
    package = tmp_path / "dot"
    package.mkdir()
    # A dependency-free package keeps the real uv lock rewrite hermetic.
    (package / "pyproject.toml").write_text(
        '[project]\nname = "fmind-dot"\nversion = "1.26.2"\nrequires-python = ">=3.14"\ndependencies = []\n'
    )
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    Runner().run(["uv", "lock", "--project", str(package)], env={"UV_OFFLINE": "1"})
    return tmp_path


def test_release_bumps_validates_commits_tags_and_pushes_atomically(project: Path) -> None:
    runner = ReleaseRunner(project)
    state = make_state(runner)

    assert run_release(state, yes=True) == TAG

    assert read_release_version(project) == "1.27.0"
    assert 'version = "1.27.0"' in (project / "dot/uv.lock").read_text()
    assert ("dprint", "fmt", "CHANGELOG.md") in runner.calls
    assert runner.interactive_calls == [
        ("mise", "run", "check:network"),
        ("mise", "run", "test:starters"),
        ("mise", "run", "build"),
        ("mise", "run", "check:completions"),
        COMMIT,
        PUSH,
        DEPLOY,
    ]
    assert runner.calls[-1] == ("git", "tag", "-a", TAG, "-m", TAG)
    assert RESTORE not in runner.calls


@pytest.mark.parametrize("task", ["check:network", "test:starters", "build", "check:completions"])
def test_gate_failure_restores_generated_files_without_tagging(project: Path, task: str) -> None:
    runner = ReleaseRunner(project)
    runner.interactive_codes[("mise", "run", task)] = 1

    with pytest.raises(DotError, match=f"project {task} failed"):
        run_release(make_state(runner), yes=True)

    assert RESTORE in runner.calls
    assert COMMIT not in runner.interactive_calls
    assert not any(call[:3] == ("git", "tag", "-a") for call in runner.calls)
    assert PUSH not in runner.interactive_calls


def test_failed_commit_hook_restores_generated_files_without_tagging(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.interactive_codes[COMMIT] = 1

    with pytest.raises(DotError, match="release commit failed; see the hook output above"):
        run_release(make_state(runner), yes=True)

    assert RESTORE in runner.calls
    assert not any(call[:3] == ("git", "tag", "-a") for call in runner.calls)
    assert PUSH not in runner.interactive_calls


def test_interrupt_restores_generated_files_and_propagates(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.interactive_codes[("mise", "run", "build")] = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run_release(make_state(runner), yes=True)

    assert RESTORE in runner.calls


def test_failed_tag_reports_the_local_release_commit_and_its_recovery(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.responses[("git", "tag", "-a", TAG, "-m", TAG)] = CommandResult("", "", 128)

    with pytest.raises(DotError, match=r"tagging failed after the local release commit.*git tag -a v1\.27\.0"):
        run_release(make_state(runner), yes=True)

    assert PUSH not in runner.interactive_calls
    assert RESTORE not in runner.calls


def test_failed_push_reports_the_local_release_and_skips_deploy(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.interactive_codes[PUSH] = 1

    with pytest.raises(DotError, match=r"release commit and tag v1\.27\.0 are local.*then: mise run deploy"):
        run_release(make_state(runner), yes=True)

    assert DEPLOY not in runner.interactive_calls


def test_failed_deploy_after_push_reports_the_published_release(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.interactive_codes[DEPLOY] = 1

    with pytest.raises(DotError, match=r"pushed v1\.27\.0, but refreshing the installed CLI failed"):
        run_release(make_state(runner), yes=True)

    assert RESTORE not in runner.calls


def test_release_preflight_rejects_unsafe_repository_states(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.installed.discard("git-cliff")
    with pytest.raises(DotError, match="missing release tools: git-cliff"):
        run_release(make_state(runner), yes=True)

    runner = ReleaseRunner(project)
    runner.responses[("git", "status", "--porcelain")] = CommandResult(" M README.md", "", 0)
    with pytest.raises(DotError, match="uncommitted"):
        run_release(make_state(runner), yes=True)

    runner = ReleaseRunner(project)
    runner.responses[("git", "branch", "--show-current")] = CommandResult("feature", "", 0)
    with pytest.raises(DotError, match="requires branch 'main'"):
        run_release(make_state(runner), yes=True)

    runner = ReleaseRunner(project)
    runner.responses[("git", "rev-parse", "origin/main")] = CommandResult("a" * 40, "", 0)
    with pytest.raises(DotError, match="HEAD must equal origin/main"):
        run_release(make_state(runner), yes=True)

    runner = ReleaseRunner(project)
    runner.responses[GIT_CLIFF_BUMPED] = CommandResult("v1.27.0-rc.1", "", 0)
    with pytest.raises(DotError, match="invalid semantic version"):
        run_release(make_state(runner), yes=True)

    runner = ReleaseRunner(project)
    runner.responses[("git", "tag", "--list", TAG)] = CommandResult(TAG, "", 0)
    with pytest.raises(DotError, match=r"tag v1\.27\.0 already exists locally"):
        run_release(make_state(runner), yes=True)
    assert not runner.interactive_calls
    assert read_release_version(project) == "1.26.2"


class _TerminalInput(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_no_change_and_cancellation_have_no_side_effects(project: Path) -> None:
    runner = ReleaseRunner(project)
    runner.responses[GIT_CLIFF_BUMPED] = CommandResult("v1.26.2", "", 0)
    assert run_release(make_state(runner), yes=True) is None

    runner = ReleaseRunner(project)
    stdout = io.StringIO()
    state = State(runner=runner, stdin=_TerminalInput("n\n"), stdout=stdout, stderr=io.StringIO())
    assert run_release(state) is None
    assert "Release canceled." in stdout.getvalue()

    runner = ReleaseRunner(project)
    with pytest.raises(DotError, match="pass --yes"):
        run_release(State(runner=runner, stdin=io.StringIO("y\n"), stdout=io.StringIO(), stderr=io.StringIO()))

    assert read_release_version(project) == "1.26.2"
    assert not runner.interactive_calls


def test_release_status_is_confined_to_generated_files() -> None:
    validate_release_status(" M CHANGELOG.md\0 M dot/pyproject.toml\0")
    with pytest.raises(DotError, match=r"unrelated paths: README\.md"):
        validate_release_status(" M CHANGELOG.md\0?? README.md\0")


def test_release_version_rejects_missing_and_dynamic_versions(tmp_path: Path) -> None:
    (tmp_path / "dot").mkdir()
    with pytest.raises(DotError, match="failed to read"):
        read_release_version(tmp_path)
    (tmp_path / "dot/pyproject.toml").write_text('[project]\ndynamic = ["version"]\n')
    with pytest.raises(DotError, match="static string"):
        read_release_version(tmp_path)
