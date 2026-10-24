from __future__ import annotations

import io
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import chain, repeat
from pathlib import Path
from threading import Barrier, Lock, Thread
from typing import Any

import pytest

from fmind_dot.config import Config, PullConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.repository import (
    find_git_repositories,
    gather_status,
    git_failure,
    run_pull,
    run_status,
)
from tests.fakes import make_state


class RecordingRunner(Runner):
    def __init__(
        self,
        responses: dict[tuple[str, ...], list[CommandResult]],
        tools: set[str],
    ) -> None:
        super().__init__()
        self.responses = responses
        self.tools = tools
        self.calls: list[tuple[tuple[str, ...], Path | None, str | None]] = []

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
        if command == STATUS_V2:
            return v2()
        if command == ("git", "fetch", "--prune"):
            with self.lock:
                self.concurrent_fetches.add(cwd.name)
            self.barrier.wait(timeout=2)
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


STATUS_V2 = ("git", "--no-optional-locks", "status", "--porcelain=v2", "--branch")


def v2(
    branch: str = "main", *, ahead: int = 0, behind: int = 0, dirty: bool = False, gone: bool = False
) -> CommandResult:
    """Porcelain v2 branch status; `gone` drops branch.ab as Git does when the upstream ref is deleted."""
    lines = [f"# branch.head {branch}", "# branch.upstream origin/main"]
    lines += [] if gone else [f"# branch.ab +{ahead} -{behind}"]
    lines += ["1 .M N... 100644 100644 100644 0 0 work.py"] if dirty else []
    return result("\n".join(lines) + "\n")


def test_repository_discovery_does_not_follow_workspace_symlinks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    local = workspace / "local"
    external = tmp_path / "external"
    (local / ".git").mkdir(parents=True)
    (external / ".git").mkdir(parents=True)
    linked = workspace / "linked"
    linked.symlink_to(external, target_is_directory=True)
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    assert find_git_repositories(make_state(RecordingRunner({}, set()), config)) == [local]
    assert linked.is_symlink()


def test_repository_discovery_normalizes_and_deduplicates_relative_workspace_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "work" / "project"
    (repository / ".git").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    config = Config(pull=PullConfig(directories=["work", str(tmp_path / "work")]))

    assert find_git_repositories(make_state(RecordingRunner({}, set()), config)) == [repository]


def test_pull_fast_forwards_a_local_remote_and_rejects_divergence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    runner = Runner()

    def git(path: Path, *args: str) -> str:
        return runner.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
            cwd=path,
            timeout=10,
        ).stdout.strip()

    remote, seed, checkout = (tmp_path / name for name in ("remote.git", "seed", "checkout"))
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(tmp_path, "clone", str(remote), str(seed))
    git(seed, "commit", "--allow-empty", "-m", "initial")
    git(seed, "push", "origin", "main")
    git(tmp_path, "clone", str(remote), str(checkout))
    git(seed, "commit", "--allow-empty", "-m", "remote update")
    git(seed, "push", "origin", "main")
    state = make_state(runner, Config(pull=PullConfig(directories=[str(checkout)])))
    [pulled] = run_pull(state)
    assert pulled.commits == 1
    assert git(checkout, "rev-parse", "HEAD") == git(seed, "rev-parse", "HEAD")
    git(checkout, "commit", "--allow-empty", "-m", "local update")
    local = git(checkout, "rev-parse", "HEAD")
    git(seed, "commit", "--allow-empty", "-m", "diverging update")
    git(seed, "push", "origin", "main")
    with pytest.raises(DotError, match="failed to pull"):
        run_pull(state)
    assert git(checkout, "rev-parse", "HEAD") == local
    assert git(checkout, "status", "--porcelain") == ""


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
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
            find_git_repositories(make_state(RecordingRunner({}, set()), config))
    finally:
        inaccessible.chmod(0o700)


def test_pull_skips_a_dirty_repository_before_fetching_or_pushing(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2(dirty=True)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    results = run_pull(make_state(runner, config), push=True)

    assert results[0].dirty
    assert results[0].skipped == "dirty worktree"
    assert not any(call[0][:2] in {("git", "fetch"), ("git", "push")} for call in runner.calls)


def test_pull_rechecks_worktree_after_fetch_before_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    class EditingRunner(Runner):
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
            response = super().run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)
            if list(args) == ["git", "fetch", "--prune"]:
                (checkout / "editor-work.txt").write_text("unsaved work committed to disk\n")
            return response

    runner = EditingRunner()

    def git(path: Path, *args: str) -> str:
        return runner.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
            cwd=path,
            timeout=10,
        ).stdout.strip()

    remote, checkout = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(tmp_path, "clone", str(remote), str(checkout))
    git(checkout, "commit", "--allow-empty", "-m", "initial")
    git(checkout, "push", "-u", "origin", "main")
    previous = git(remote, "rev-parse", "main")
    git(checkout, "commit", "--allow-empty", "-m", "ahead")
    state = make_state(runner)

    [pulled] = run_pull(state, paths=[checkout], push=True, as_json=True)

    assert pulled.dirty
    assert not pulled.pushed
    assert git(remote, "rev-parse", "main") == previous
    assert isinstance(state.stdout, io.StringIO)
    assert json.loads(state.stdout.getvalue())["repositories"][0]["dirty"] is True


@pytest.mark.parametrize("operation", ["status", "pull"])
def test_repository_disappearing_keeps_partial_json_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    gone, kept = tmp_path / "gone", tmp_path / "kept"

    class RemovingRunner(Runner):
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
            response = super().run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)
            # Remove the repository after its first inspection command, whichever operation runs.
            if cwd == gone and gone.exists() and list(args[:1]) == ["git"]:
                shutil.rmtree(gone)
            return response

    runner = RemovingRunner()
    for path in (gone, kept):
        runner.run(["git", "init", "--initial-branch=main", str(path)], timeout=10)
    state = make_state(runner)

    command = run_status if operation == "status" else run_pull
    with pytest.raises(DotError):
        command(state, paths=[gone, kept], as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document["complete"] is False
    assert len(document["repositories"]) == 2
    by_path = {row["path"]: row for row in document["repositories"]}
    assert by_path[str(gone)]["error"]
    assert not by_path[str(kept)].get("error")


def test_pull_reports_status_failure_after_fetch_instead_of_claiming_no_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2(), result("", returncode=128)],
            ("git", "fetch", "--prune"): [result()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    state = make_state(runner, config)
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
            STATUS_V2: [v2()],
            ("git", "fetch", "--prune"): [result()],
        },
        {"git"},
    )
    clock = chain([0.0] * 3, repeat(121.0))
    monkeypatch.setattr("fmind_dot.repository.monotonic", lambda: next(clock))
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = make_state(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state)

    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "sample [main]" in output
    assert "timed out" in output
    assert "no upstream" not in output


def test_pull_classifies_a_deleted_upstream_as_no_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2(), v2(gone=True)],
            ("git", "fetch", "--prune"): [result()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    results = run_pull(make_state(runner, config))

    assert results[0].no_upstream
    assert not any(call[0][1] in {"merge", "push"} for call in runner.calls)


def test_status_emits_machine_readable_repository_state(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [result(_V2_HEADER + "# branch.ab +0 -0\n")],
            ("git", "rev-parse", "--absolute-git-dir"): [result(str(repository / ".git"))],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = make_state(runner, config)

    status = run_status(state, as_json=True)

    assert status[0].branch == "main"
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert "docker" not in document
    assert document["schema"] == "dot.status/v1"
    assert document["repositories"][0]["name"] == "sample"
    assert "error" not in document["repositories"][0]


def test_status_omits_empty_optional_json_fields(tmp_path: Path) -> None:
    runner = RecordingRunner({}, {"git"})
    config = Config(pull=PullConfig(directories=[str(tmp_path)]))
    state = make_state(runner, config)

    run_status(state, as_json=True)

    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document == {
        "schema": "dot.status/v1",
        "repositories": [],
        "complete": True,
        "needs_attention": False,
        "remote_state": "cached",
    }


_V2_HEADER = (
    "# branch.oid 0123456789abcdef0123456789abcdef01234567\n# branch.head main\n# branch.upstream origin/main\n"
)


def _clean_status_responses(repository: Path) -> dict[tuple[str, ...], list[CommandResult]]:
    return {
        STATUS_V2: [result(_V2_HEADER + "# branch.ab +0 -2\n")],
        ("git", "rev-parse", "--absolute-git-dir"): [result(str(repository / ".git"))],
    }


def test_status_fetch_refreshes_remote_refs_without_merging(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {("git", "fetch", "--prune"): [result()], **_clean_status_responses(repository)},
        {"git"},
    )
    state = make_state(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    run_status(state, as_json=True, fetch=True)

    commands = [call[0] for call in runner.calls]
    assert commands[0] == ("git", "fetch", "--prune")
    assert not any("merge" in command for command in commands)
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert document["remote_state"] == "fetched"
    assert document["needs_attention"] is True
    assert document["repositories"][0]["behind"] == 2
    assert document["repositories"][0]["needs_attention"] is True


def test_status_fetch_failure_marks_inspection_incomplete(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    (workspace / "sample" / ".git").mkdir(parents=True)
    runner = RecordingRunner({("git", "fetch", "--prune"): [result(returncode=128)]}, {"git"})
    state = make_state(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    with pytest.raises(DotError, match="repository inspection is incomplete"):
        run_status(state, fetch=True)

    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "failed to fetch repository" in output
    assert "no upstream" not in output
    assert " \n" not in output


def test_status_needs_attention_confirms_an_all_clear_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    responses = _clean_status_responses(repository)
    responses[STATUS_V2] = [result(_V2_HEADER + "# branch.ab +0 -0\n")]
    state = make_state(RecordingRunner(responses, {"git"}), Config(pull=PullConfig(directories=[str(workspace)])))

    run_status(state, needs_attention=True)

    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "All 1 repositories are clean and in sync." in output
    assert "▶" not in output


def test_pull_with_no_repositories_reports_a_clean_noop(tmp_path: Path) -> None:
    state = make_state(
        RecordingRunner({}, {"git"}),
        Config(pull=PullConfig(directories=[str(tmp_path)])),
    )

    assert run_pull(state) == []
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == "No git repositories found in configured pull directories.\n"


_FOR_EACH_UPSTREAM = ("git", "for-each-ref", "--format=%(upstream:remotename)%00%(upstream:remoteref)")


def test_pull_pushes_ahead_branch_to_its_exact_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2("feature"), v2("feature", ahead=2), v2("feature", ahead=2)],
            ("git", "fetch", "--prune"): [result()],
            (*_FOR_EACH_UPSTREAM, "refs/heads/feature"): [result("origin\0refs/heads/main\n")],
            ("git", "push", "--no-follow-tags", "origin", "HEAD:refs/heads/main"): [result()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = make_state(runner, config)

    results = run_pull(state, push=True)

    assert results[0].branch == "feature"
    assert results[0].pushed
    assert isinstance(state.stdout, io.StringIO)
    assert "↑ pushed 2 commit(s)" in state.stdout.getvalue()


def test_pull_reports_push_failure_after_successful_fast_forward(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2(), v2(ahead=1, behind=1), v2(ahead=1)],
            ("git", "fetch", "--prune"): [result()],
            ("git", "merge", "--ff-only", "@{u}"): [result()],
            (*_FOR_EACH_UPSTREAM, "refs/heads/main"): [result("origin\0refs/heads/main\n")],
            ("git", "push", "--no-follow-tags", "origin", "HEAD:refs/heads/main"): [result(returncode=1)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = make_state(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state, push=True)

    assert isinstance(state.stdout, io.StringIO)
    assert "pulled 1 commit(s)" in state.stdout.getvalue()
    assert "Push failed" in state.stdout.getvalue()


def test_pull_reports_a_fetch_failure_before_inspecting_the_upstream(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner(
        {
            STATUS_V2: [v2()],
            ("git", "fetch", "--prune"): [result(returncode=1)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))
    state = make_state(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state)
    assert [command for command, _, _ in runner.calls].count(STATUS_V2) == 1
    assert isinstance(state.stdout, io.StringIO)
    assert "failed to fetch repository" in state.stdout.getvalue()
    assert "skipped" not in state.stdout.getvalue()


def test_pull_runs_independent_repositories_concurrently(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    for name in ("one", "two"):
        (workspace / name / ".git").mkdir(parents=True)
    runner = ConcurrentPullRunner()
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    results = run_pull(make_state(runner, config))

    assert [item.path.name for item in results] == ["one", "two"]
    assert runner.concurrent_fetches == {"one", "two"}


def test_pull_propagates_user_cancellation(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = InterruptingPullRunner(
        {
            STATUS_V2: [v2()],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    with pytest.raises(KeyboardInterrupt):
        run_pull(make_state(runner, config))


def test_status_human_output_shows_dirty_repository_without_probing_docker(tmp_path: Path) -> None:
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
            STATUS_V2: [result(_V2_HEADER + "# branch.ab +0 -0\n1 .M N... 100644 100644 100644 0 0 changed.py\n")],
            ("git", "rev-parse", "--absolute-git-dir"): [result(str(repository / ".git"))],
        },
        {"git", "docker"},
    )
    state = make_state(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    status = run_status(state)

    assert not any("docker" in str(call[0][0]) for call in runner.calls)
    assert status[0].dirty
    assert isinstance(state.stdout, io.StringIO)
    assert "Docker" not in state.stdout.getvalue()
    assert "work/sample [main] [dirty]" in state.stdout.getvalue()


def test_status_json_reports_repository_failures(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    repository = workspace / "sample"
    (repository / ".git").mkdir(parents=True)
    runner = RecordingRunner({STATUS_V2: [result(returncode=1)]}, {"git"})
    state = make_state(runner, Config(pull=PullConfig(directories=[str(workspace)])))

    with pytest.raises(DotError, match="inspection is incomplete"):
        run_status(state, as_json=True)
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
    assert "docker" not in document
    assert not document["complete"]
    assert document["repositories"][0]["branch"] == ""
    assert document["repositories"][0]["error"] == "git status failed (1)"


def test_status_human_output_reports_empty_workspace(tmp_path: Path) -> None:
    state = make_state(
        RecordingRunner({}, {"git"}),
        Config(pull=PullConfig(directories=[str(tmp_path)])),
    )

    run_status(state)

    assert isinstance(state.stdout, io.StringIO)
    assert "Docker" not in state.stdout.getvalue()
    assert "No repositories found" in state.stdout.getvalue()


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        (
            " ! [rejected]        main -> main (non-fast-forward)\n",
            "git push failed (1): non-fast-forward",
        ),
        (
            "fatal: Authentication failed for 'https://github.com/o/r.git/'\n",
            "git fetch failed (128): authentication failed",
        ),
        (
            "fatal: unable to access 'https://x/': Could not resolve host: x\n",
            "git fetch failed (128): network unavailable",
        ),
        (
            "fatal: unable to access 'https://x/': The requested URL returned error: 403\n",
            "git fetch failed (128): authentication failed",
        ),
        (
            "git@github.com: Permission denied (publickey).\nfatal: Could not read from remote repository.\n",
            "git fetch failed (128): authentication failed",
        ),
        (
            "error: cannot open '.git/FETCH_HEAD': Permission denied\n",
            "git fetch failed (128): error: cannot open '.git/FETCH_HEAD': Permission denied",
        ),
        (
            "error: https://user:ghp_0123456789abcdefghijklmnopqrstuvwxyz@host/r odd\nsecond line\n",
            "git fetch failed (128): error: https://<redacted>@host/r odd",
        ),
        (
            "To github.com:o/r.git\n ! [remote rejected] main -> main (protected branch hook declined)\n",
            "git push failed (1): push rejected by remote",
        ),
        (
            "From github.com:o/r\nfatal: /home/user/projects/a-very-long-repository-name/sub: not found\n",
            "git fetch failed (128): fatal: /home/user/projects/a-very-long-repository-name/sub: not found",
        ),
        ("", "git fetch failed (128)"),
    ],
)
def test_git_failures_name_a_secret_free_cause(stderr: str, expected: str) -> None:
    subcommand = "push" if "rejected" in stderr else "fetch"  # covers "[remote rejected]" too
    code = 1 if subcommand == "push" else 128
    message = git_failure(["--no-optional-locks", subcommand], CommandResult("", stderr, code))
    assert message == expected
    assert "ghp_" not in message


def test_status_names_an_explicit_path_outside_a_work_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    outside = tmp_path / "plain"
    outside.mkdir()

    with pytest.raises(DotError, match=rf"^{outside} is not inside a git work tree$"):
        run_status(make_state(Runner()), paths=[outside])


def test_pull_never_waits_on_credential_prompts(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    (workspace / "sample" / ".git").mkdir(parents=True)
    environments: dict[tuple[str, ...], object] = {}

    class EnvironmentRunner(RecordingRunner):
        def run(self, args: Sequence[str], *, env: object = None, **options: Any) -> CommandResult:
            environments[tuple(args)] = env
            return super().run(args, **options)

    runner = EnvironmentRunner(
        {
            STATUS_V2: [v2()],
            ("git", "fetch", "--prune"): [result(returncode=128)],
        },
        {"git"},
    )
    config = Config(pull=PullConfig(directories=[str(workspace)]))

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(make_state(runner, config))

    # Concurrent fetches fail instead of opening a terminal or askpass prompt.
    assert environments[("git", "fetch", "--prune")] == {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "",
        "SSH_ASKPASS_REQUIRE": "never",
    }


@pytest.mark.parametrize("source", ["GIT_ASKPASS", "core.askPass", "SSH_ASKPASS"])
def test_fetch_does_not_invoke_inherited_askpass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    class Unauthorized(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib handler signature
            pass

    marker = tmp_path / "prompted"
    askpass = tmp_path / "askpass"
    askpass.write_text('#!/bin/sh\nprintf prompted >> "$DOT_ASKPASS_MARKER"\nexit 1\n')
    askpass.chmod(0o700)
    monkeypatch.setenv("DOT_ASKPASS_MARKER", str(marker))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("SSH_ASKPASS", raising=False)
    runner = Runner()
    repository = tmp_path / "repo"
    runner.run(["git", "init", "-q", str(repository)])
    if source == "core.askPass":
        runner.run(["git", "config", source, str(askpass)], cwd=repository)
    else:
        monkeypatch.setenv(source, str(askpass))
    runner.run(["git", "config", "credential.helper", ""], cwd=repository)
    with ThreadingHTTPServer(("127.0.0.1", 0), Unauthorized) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            runner.run(
                ["git", "remote", "add", "origin", f"http://127.0.0.1:{server.server_port}/repo"], cwd=repository
            )
            results = gather_status(make_state(runner), paths=[repository], fetch=True)
        finally:
            server.shutdown()
            worker.join(timeout=2)
    assert len(results) == 1
    assert "authentication failed" in results[0].error
    assert not marker.exists()


def test_status_reads_branch_divergence_and_detached_heads_from_real_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    runner = Runner()

    def git(path: Path, *args: str) -> str:
        return runner.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
            cwd=path,
            timeout=10,
        ).stdout.strip()

    remote, checkout = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(tmp_path, "clone", str(remote), str(checkout))
    git(checkout, "commit", "--allow-empty", "-m", "initial")
    git(checkout, "push", "-u", "origin", "main")
    git(checkout, "commit", "--allow-empty", "-m", "ahead")
    (checkout / "new.txt").write_text("untracked\n")
    state = make_state(runner)

    [tracked] = run_status(state, paths=[checkout])
    assert (tracked.branch, tracked.upstream, tracked.ahead, tracked.behind, tracked.dirty) == (
        "main",
        "origin/main",
        1,
        0,
        True,
    )

    # A deleted upstream ref reports no upstream instead of failing; a detached HEAD shows its short hash.
    git(checkout, "update-ref", "-d", "refs/remotes/origin/main")
    [gone] = run_status(state, paths=[checkout])
    assert (gone.upstream, gone.error) == ("", "")
    git(checkout, "checkout", "--detach")
    [detached] = run_status(state, paths=[checkout])
    assert detached.branch == git(checkout, "rev-parse", "--short", "HEAD")
