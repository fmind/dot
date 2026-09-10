from __future__ import annotations

import io
import json
from collections.abc import Sequence
from pathlib import Path
from threading import Barrier, Lock

import pytest

from fmind_dot.config import Config, PullConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.repository import (
    find_git_repositories,
    run_pull,
    run_status,
)
from fmind_dot.state import State


class RecordingRunner(Runner):
    def __init__(
        self,
        responses: dict[tuple[str, ...], list[CommandResult]],
        tools: set[str],
        *,
        interactive_status: int = 0,
    ) -> None:
        super().__init__()
        self.responses = responses
        self.tools = tools
        self.interactive_status = interactive_status
        self.calls: list[tuple[tuple[str, ...], Path | None, str | None]] = []
        self.interactive_calls: list[tuple[str, ...]] = []
        self.interactive_payloads: list[str] = []

    def which(self, command: str) -> Path | None:
        return Path(f"/tools/{command}") if command in self.tools else None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: object = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        del env, timeout
        key = tuple(args)
        self.calls.append((key, cwd, input_text))
        result = self.responses[key].pop(0)
        if check and result.returncode:
            raise DotError(f"command failed ({result.returncode}): {args[0]}")
        return result

    def interactive(self, args: Sequence[str], **_: object) -> int:
        self.interactive_calls.append(tuple(args))
        if "--body-file" in args:
            path = Path(args[args.index("--body-file") + 1])
            self.interactive_payloads.append(path.read_text(encoding="utf-8"))
        return self.interactive_status


class ConcurrentPullRunner(RecordingRunner):
    def __init__(self) -> None:
        super().__init__({}, {"git"})
        self.barrier = Barrier(2)
        self.lock = Lock()
        self.concurrent_fetches: set[str] = set()

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: object = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        del input_text, env, timeout, check
        assert cwd is not None
        command = tuple(args)
        if command == ("git", "branch", "--show-current"):
            return result("main\n")
        if command == ("git", "status", "--porcelain"):
            return result()
        if command == ("git", "fetch", "--prune"):
            with self.lock:
                self.concurrent_fetches.add(cwd.name)
            self.barrier.wait(timeout=2)
            return result()
        if command == ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"):
            return result("origin/main\n")
        if command in {
            ("git", "rev-list", "--count", "HEAD..@{u}"),
            ("git", "rev-list", "--count", "@{u}..HEAD"),
        }:
            return result("0\n")
        if command == ("git", "pull", "--ff-only"):
            return result()
        raise AssertionError(f"unexpected command: {command}")


class InterruptingPullRunner(RecordingRunner):
    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: object = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        if tuple(args) == ("git", "fetch", "--prune"):
            raise KeyboardInterrupt
        return super().run(
            args,
            cwd=cwd,
            input_text=input_text,
            env=env,
            timeout=timeout,
            check=check,
        )


def result(stdout: str = "", returncode: int = 0) -> CommandResult:
    return CommandResult(stdout=stdout, stderr="", returncode=returncode)


def state_with(runner: Runner, config: Config | None = None) -> State:
    state = State(runner=runner, stdout=io.StringIO(), stderr=io.StringIO())
    state.__dict__["_config"] = config or Config()
    return state


def test_repository_discovery_does_not_follow_workspace_symlinks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    local = workspace / "local"
    external = tmp_path / "external"
    (local / ".git").mkdir(parents=True)
    (external / ".git").mkdir(parents=True)
    linked = workspace / "linked"
    linked.symlink_to(external, target_is_directory=True)
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    assert find_git_repositories(state_with(RecordingRunner({}, set()), config)) == [local]
    assert linked.is_symlink()


@pytest.mark.parametrize("blocked", ["root", "entry"])
def test_repository_discovery_reports_unreadable_paths(tmp_path: Path, blocked: str) -> None:
    workspace = tmp_path / "workspace"
    repository = workspace / "project"
    (repository / ".git").mkdir(parents=True)
    inaccessible = workspace if blocked == "root" else repository
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    inaccessible.chmod(0)
    try:
        with pytest.raises(DotError, match="failed to inspect repository"):
            find_git_repositories(state_with(RecordingRunner({}, set()), config))
    finally:
        inaccessible.chmod(0o700)


def test_pull_fast_forwards_but_does_not_push_a_dirty_repository(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result(" M work.py\n")],
            ("git", "fetch", "--prune"): [result()],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main\n")],
            ("git", "rev-list", "--count", "HEAD..@{u}"): [result("2\n")],
            ("git", "pull", "--ff-only"): [result()],
            ("git", "rev-list", "--count", "@{u}..HEAD"): [result("1\n")],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))

    results = run_pull(state_with(runner, config), push=True, dirty_policy="allow")

    assert results[0].commits == 2
    assert results[0].ahead == 1
    assert results[0].dirty
    assert not any(call[0] == ("git", "push") for call in runner.calls)


def test_pull_reports_rev_list_failure_instead_of_claiming_no_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result("")],
            ("git", "fetch", "--prune"): [result()],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main\n")],
            ("git", "rev-list", "--count", "HEAD..@{u}"): [result("", returncode=128)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))

    state = state_with(runner, config)
    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state)

    assert isinstance(state.stdout, io.StringIO)
    assert "sample [main]" in state.stdout.getvalue()


def test_pull_timeout_during_upstream_probe_is_a_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result("")],
            ("git", "fetch", "--prune"): [result()],
        },
        {"git"},
    )
    clock = iter([0.0, 0.0, 0.0, 0.0, 2.0])
    monkeypatch.setattr("fmind_dot.repository.monotonic", lambda: next(clock))
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))
    state = state_with(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state)

    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "sample [main]" in output
    assert "timed out" in output
    assert "no upstream" not in output


def test_pull_classifies_nonzero_upstream_probe_as_no_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result("")],
            ("git", "fetch", "--prune"): [result()],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result(returncode=128)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))

    results = run_pull(state_with(runner, config))

    assert results[0].no_upstream
    assert not any(call[0][1] in {"rev-list", "pull"} for call in runner.calls)


def test_status_emits_machine_readable_repository_and_docker_state(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result("")],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main")],
            ("git", "rev-list", "--left-right", "--count", "HEAD...@{u}"): [result("0\t0")],
            ("git", "rev-parse", "--absolute-git-dir"): [result(str(repository / ".git"))],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = state_with(runner, config)

    status = run_status(state, as_json=True)

    assert status.repositories[0].branch == "main"
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document["docker"] == {"installed": False, "running": False, "details": "command not found"}
    assert document["repositories"][0]["name"] == "sample"
    assert "error" not in document["repositories"][0]


def test_status_omits_empty_optional_json_fields(tmp_path: Path) -> None:
    docker_info = (
        "/tools/docker",
        "info",
        "--format",
        "{{.Name}} (Containers: {{.Containers}}, Running: {{.ContainersRunning}})",
    )
    runner = RecordingRunner({docker_info: [result("")]}, {"git", "docker"})
    config = Config(pull=PullConfig(directories=[str(tmp_path)]))
    state = state_with(runner, config)

    run_status(state, as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document == {
        "docker": {"installed": True, "running": False},
        "repositories": [],
        "complete": True,
        "remote_state": "cached",
    }


def test_pull_with_no_repositories_reports_a_clean_noop(tmp_path: Path) -> None:
    state = state_with(
        RecordingRunner({}, {"git"}),
        Config(pull=PullConfig(directories=[str(tmp_path)], concurrency=2, timeout_seconds=1)),
    )

    assert run_pull(state) == []
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == "No git repositories found in configured pull directories.\n"


def test_pull_pushes_clean_detached_repository_that_is_ahead(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result()],
            ("git", "rev-parse", "--short", "HEAD"): [result("abc123\n")],
            ("git", "status", "--porcelain"): [result()],
            ("git", "fetch", "--prune"): [result()],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main\n")],
            ("git", "rev-list", "--count", "HEAD..@{u}"): [result("0\n")],
            ("git", "pull", "--ff-only"): [result()],
            ("git", "rev-list", "--count", "@{u}..HEAD"): [result("2\n")],
            ("git", "push"): [result()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))
    state = state_with(runner, config)

    results = run_pull(state, push=True)

    assert results[0].branch == "abc123"
    assert results[0].pushed
    assert isinstance(state.stdout, io.StringIO)
    assert "↑ pushed 2 commit(s)" in state.stdout.getvalue()


def test_pull_reports_push_failure_after_successful_fast_forward(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result()],
            ("git", "fetch", "--prune"): [result()],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main\n")],
            ("git", "rev-list", "--count", "HEAD..@{u}"): [result("1\n")],
            ("git", "pull", "--ff-only"): [result()],
            ("git", "rev-list", "--count", "@{u}..HEAD"): [result("1\n")],
            ("git", "push"): [result(returncode=1)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))
    state = state_with(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state, push=True)

    assert isinstance(state.stdout, io.StringIO)
    assert "pulled 1 commit(s)" in state.stdout.getvalue()
    assert "Push failed" in state.stdout.getvalue()


@pytest.mark.parametrize("has_upstream", [False, True])
def test_pull_classifies_fetch_failure_by_upstream_state(tmp_path: Path, has_upstream: bool) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result()],
            ("git", "fetch", "--prune"): [result(returncode=1)],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [
                result("origin/main\n" if has_upstream else "", returncode=0 if has_upstream else 128)
            ],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))
    state = state_with(runner, config)

    if has_upstream:
        with pytest.raises(DotError, match="failed to pull 1 repositories"):
            run_pull(state)
        assert isinstance(state.stdout, io.StringIO)
        assert "failed to fetch repository" in state.stdout.getvalue()
    else:
        results = run_pull(state)
        assert results[0].no_upstream


def test_pull_uses_configured_concurrency_for_independent_repositories(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    for name in ("one", "two"):
        (workspace / name / ".git").mkdir(parents=True)
    runner = ConcurrentPullRunner()
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=2, timeout_seconds=5))

    results = run_pull(state_with(runner, config))

    assert [item.path.name for item in results] == ["one", "two"]
    assert runner.concurrent_fetches == {"one", "two"}


def test_pull_propagates_user_cancellation(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = InterruptingPullRunner(
        {
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout_seconds=1))

    with pytest.raises(KeyboardInterrupt):
        run_pull(state_with(runner, config))


def test_status_human_output_distinguishes_running_and_dirty_repository(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    docker_info = (
        "/tools/docker",
        "info",
        "--format",
        "{{.Name}} (Containers: {{.Containers}}, Running: {{.ContainersRunning}})",
    )
    runner = RecordingRunner(
        {
            docker_info: [result("desktop (Containers: 3, Running: 2)\n")],
            ("git", "branch", "--show-current"): [result("main\n")],
            ("git", "status", "--porcelain"): [result(" M changed.py\n")],
            ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): [result("origin/main")],
            ("git", "rev-list", "--left-right", "--count", "HEAD...@{u}"): [result("0\t0")],
            ("git", "rev-parse", "--absolute-git-dir"): [result(str(repository / ".git"))],
        },
        {"git", "docker"},
    )
    state = state_with(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    status = run_status(state)

    assert status.docker.running
    assert status.repositories[0].dirty
    assert isinstance(state.stdout, io.StringIO)
    assert "✓ Running: desktop" in state.stdout.getvalue()
    assert "work/sample [main] [dirty]" in state.stdout.getvalue()


def test_status_json_reports_probe_and_repository_failures(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    docker_info = (
        "/tools/docker",
        "info",
        "--format",
        "{{.Name}} (Containers: {{.Containers}}, Running: {{.ContainersRunning}})",
    )
    runner = RecordingRunner(
        {
            docker_info: [result(returncode=1)],
            ("git", "branch", "--show-current"): [result(returncode=1)],
        },
        {"git", "docker"},
    )
    state = state_with(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    with pytest.raises(DotError, match="inspection is incomplete"):
        run_status(state, as_json=True)
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document["docker"]["details"] == "inspection command failed"
    assert not document["complete"]
    assert document["repositories"][0]["branch"] == ""
    assert "command failed" in document["repositories"][0]["error"]


def test_status_human_output_reports_missing_docker_and_empty_workspace(tmp_path: Path) -> None:
    state = state_with(
        RecordingRunner({}, {"git"}),
        Config(pull=PullConfig(directories=[str(tmp_path)])),
    )

    run_status(state)

    assert isinstance(state.stdout, io.StringIO)
    assert "✗ Not installed." in state.stdout.getvalue()
    assert "No repositories found" in state.stdout.getvalue()
