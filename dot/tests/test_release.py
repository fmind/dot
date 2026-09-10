from __future__ import annotations

import io
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO

import pytest

from dot_tasks.release import (
    push_prepared_commit,
    push_release_tag,
    read_release_version,
    remote_release_tag_commit,
    run_release,
    validate_release_status,
    write_release_version,
)
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


class RecordingRunner(Runner):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, ...]] = []
        self.interactive_calls: list[tuple[str, ...]] = []
        self.responses: dict[tuple[str, ...], CommandResult | Exception | KeyboardInterrupt] = {}
        self.output_limits: list[int | None] = []
        self.installed = {"chezmoi", "docker", "dprint", "gh", "git", "git-cliff", "mise", "pip", "uv"}

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
        del cwd, input_text, env, timeout
        call = tuple(args)
        self.calls.append(call)
        response = self.responses.get(call, CommandResult("", "", 0))
        if isinstance(response, BaseException):
            raise response
        if check and response.returncode != 0:
            raise DotError(f"command failed ({response.returncode}): {args[0]}")
        return response

    def run_bounded(
        self,
        args: Sequence[str],
        *,
        max_output_bytes: int,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        self.output_limits.append(max_output_bytes)
        return self.run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stdout_line: Callable[[str], None] | None = None,
    ) -> int:
        del cwd, stdin, stdout, stderr, env, on_stdout_line
        call = tuple(args)
        self.interactive_calls.append(call)
        response = self.responses.get(call, CommandResult("", "", 0))
        if isinstance(response, KeyboardInterrupt):
            raise response
        if isinstance(response, Exception):
            return 1
        if response.returncode == 0 and len(call) == 4 and call[:3] == ("git", "push", "origin"):
            source, destination = call[3].split(":", 1)
            prefix = "refs/heads/"
            if destination.startswith(prefix):
                branch = destination.removeprefix(prefix)
                self.responses[("git", "rev-parse", f"origin/{branch}")] = CommandResult(source, "", 0)
        return response.returncode


class VersionRevertingRunner(RecordingRunner):
    def __init__(self, pyproject: Path, content: str) -> None:
        super().__init__()
        self.pyproject = pyproject
        self.content = content

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stdout_line: Callable[[str], None] | None = None,
    ) -> int:
        code = super().interactive(
            args,
            cwd=cwd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=env,
            on_stdout_line=on_stdout_line,
        )
        if tuple(args) == ("mise", "run", "test"):
            self.pyproject.write_text(self.content)
        return code


class RealLockRunner(RecordingRunner):
    """Keep release side effects fake while exercising uv's real lock writer."""

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
        if tuple(args) == ("uv", "lock", "--project", "dot"):
            self.calls.append(tuple(args))
            command_env = dict(env or {})
            command_env["UV_OFFLINE"] = "1"
            return Runner.run(
                self,
                args,
                cwd=cwd,
                input_text=input_text,
                env=command_env,
                timeout=timeout,
                check=check,
            )
        return super().run(
            args,
            cwd=cwd,
            input_text=input_text,
            env=env,
            timeout=timeout,
            check=check,
        )


def make_state(runner: Runner | None = None) -> State:
    return State(
        runner=runner or RecordingRunner(),
        stdin=io.StringIO(),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )


def copy_release_project(tmp_path: Path) -> tuple[Path, bytes]:
    project = tmp_path / "dot"
    project.mkdir()
    # A dependency-free package keeps the real uv lock rewrite hermetic even
    # when the test runner starts with an empty package cache.
    (project / "pyproject.toml").write_text(
        '[project]\nname = "fmind-dot"\nversion = "1.26.2"\nrequires-python = ">=3.14"\ndependencies = []\n'
    )
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    Runner().run(["uv", "lock", "--project", str(project)], env={"UV_OFFLINE": "1"})
    return project, (project / "uv.lock").read_bytes()


def release_runner(tmp_path: Path) -> RealLockRunner:
    commit = "b" * 40
    tag_object = "c" * 40
    tag_ref = "refs/tags/v1.27.0"
    runner = RealLockRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(commit, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(commit, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: migrate", "", 0),
        ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version"): CommandResult(
            "v1.27.0", "", 0
        ),
        ("git", "describe", "--tags", "--abbrev=0"): CommandResult("v1.26.2", "", 0),
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"): CommandResult(
            " M CHANGELOG.md\0 M dot/pyproject.toml\0 M dot/uv.lock\0", "", 0
        ),
        ("git", "cat-file", "-t", tag_ref): CommandResult("", "", 1),
        ("git", "rev-parse", tag_ref): CommandResult(tag_object, "", 0),
        ("git", "cat-file", "-t", tag_object): CommandResult("tag", "", 0),
        ("git", "rev-parse", f"{tag_object}^{{}}"): CommandResult(commit, "", 0),
        ("git", "ls-remote", "--tags", "origin", tag_ref, f"{tag_ref}^{{}}"): CommandResult(
            f"{tag_object}\t{tag_ref}\n{commit}\t{tag_ref}^{{}}\n", "", 0
        ),
    }
    return runner


def test_uncertain_push_requires_remote_exact_head() -> None:
    commit = "a" * 40
    runner = RecordingRunner()
    refspec = f"{commit}:refs/heads/main"
    runner.responses[("git", "push", "origin", refspec)] = CommandResult("", "", 1)
    runner.responses[("git", "rev-parse", "origin/main")] = CommandResult(commit, "", 0)
    state = make_state(runner)

    push_prepared_commit(state, "origin", "main", commit)
    runner.responses[("git", "rev-parse", "origin/main")] = CommandResult("b" * 40, "", 0)
    with pytest.raises(DotError, match="failed to push prepared commit"):
        push_prepared_commit(state, "origin", "main", commit)


def test_uncertain_push_fails_closed_when_remote_reconciliation_fails() -> None:
    commit = "a" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "push", "origin", f"{commit}:refs/heads/main"): CommandResult("", "", 1),
        ("git", "fetch", "origin", "main"): DotError("network unavailable"),
    }

    with pytest.raises(DotError, match="failed to push prepared commit"):
        push_prepared_commit(make_state(runner), "origin", "main", commit)


def test_remote_tag_resolution_prefers_exact_peeled_commit() -> None:
    commit = "a" * 40
    refspec = "refs/tags/v1.2.3"
    runner = RecordingRunner()
    runner.responses[("git", "ls-remote", "--tags", "origin", refspec, f"{refspec}^{{}}")] = CommandResult(
        f"{'b' * 40}\t{refspec}\n{commit}\t{refspec}^{{}}\n", "", 0
    )

    assert remote_release_tag_commit(make_state(runner), "origin", refspec) == commit
    assert runner.output_limits[-1] == 4096


def test_remote_tag_resolution_rejects_truncated_output() -> None:
    commit = "a" * 40
    refspec = "refs/tags/v1.2.3"
    runner = RecordingRunner()
    runner.responses[("git", "ls-remote", "--tags", "origin", refspec, f"{refspec}^{{}}")] = CommandResult(
        f"{'b' * 40}\t{refspec}\n{commit}\t{refspec}^{{}}\n",
        "",
        0,
        stdout_truncated=True,
    )

    with pytest.raises(DotError, match="exceeded 4096 bytes"):
        remote_release_tag_commit(make_state(runner), "origin", refspec)


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("broken\n", "invalid ls-remote record"),
        (
            f"{'a' * 40}\trefs/tags/v1.2.3\n{'b' * 40}\trefs/tags/v1.2.3\n",
            "conflicting remote values",
        ),
        (
            f"{'a' * 40}\trefs/tags/v1.2.3^{{}}\n{'b' * 40}\trefs/tags/v1.2.3^{{}}\n",
            "conflicting remote values",
        ),
        (f"{'a' * 40}\trefs/tags/unexpected\n", "unexpected remote tag ref"),
        (f"{'a' * 40}\trefs/tags/v1.2.3^{{}}\n", "without its tag object"),
    ],
)
def test_remote_tag_resolution_rejects_ambiguous_records(output: str, message: str) -> None:
    refspec = "refs/tags/v1.2.3"
    runner = RecordingRunner()
    runner.responses[("git", "ls-remote", "--tags", "origin", refspec, f"{refspec}^{{}}")] = CommandResult(
        output, "", 0
    )

    with pytest.raises(DotError, match=message):
        remote_release_tag_commit(make_state(runner), "origin", refspec)


def test_rejected_release_tag_push_accepts_remote_annotated_tag_at_expected_commit() -> None:
    commit = "a" * 40
    tag_object = "b" * 40
    refspec = "refs/tags/v1.2.3"
    runner = RecordingRunner()
    runner.responses = {
        ("git", "cat-file", "-t", refspec): CommandResult("tag", "", 0),
        ("git", "rev-parse", refspec): CommandResult(tag_object, "", 0),
        ("git", "cat-file", "-t", tag_object): CommandResult("tag", "", 0),
        ("git", "rev-parse", f"{tag_object}^{{}}"): CommandResult(commit, "", 0),
        ("git", "push", "origin", f"{tag_object}:{refspec}"): CommandResult("", "", 1),
        ("git", "ls-remote", "--tags", "origin", refspec, f"{refspec}^{{}}"): CommandResult(
            f"{tag_object}\t{refspec}\n{commit}\t{refspec}^{{}}\n", "", 0
        ),
    }

    push_release_tag(make_state(runner), "origin", "v1.2.3", commit)


class GitPushRaceRunner(Runner):
    def __init__(self, mutation: Callable[[], None]) -> None:
        super().__init__()
        self.mutation = mutation
        self.mutated = False

    def interactive(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        stderr: IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        on_stdout_line: Callable[[str], None] | None = None,
    ) -> int:
        if tuple(args[:2]) == ("git", "push") and not self.mutated:
            self.mutation()
            self.mutated = True
        return super().interactive(
            args,
            cwd=cwd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=env,
            on_stdout_line=on_stdout_line,
        )


def _release_race_repository(tmp_path: Path) -> tuple[Path, Path, str, str]:
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    git = Runner()
    git.run(["git", "init", "--bare", str(remote)])
    git.run(["git", "init", str(local)])
    git.run(["git", "config", "user.name", "Release Test"], cwd=local)
    git.run(["git", "config", "user.email", "release@example.invalid"], cwd=local)
    tracked = local / "tracked"
    tracked.write_text("first\n")
    git.run(["git", "add", "tracked"], cwd=local)
    git.run(["git", "commit", "-m", "first"], cwd=local)
    first = git.run(["git", "rev-parse", "HEAD"], cwd=local).stdout.strip()
    tracked.write_text("second\n")
    git.run(["git", "commit", "-am", "second"], cwd=local)
    second = git.run(["git", "rev-parse", "HEAD"], cwd=local).stdout.strip()
    git.run(["git", "remote", "add", "origin", str(remote)], cwd=local)
    return remote, local, first, second


def test_prepared_commit_push_is_bound_to_validated_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote, local, prepared, replacement = _release_race_repository(tmp_path)
    git = Runner()
    git.run(["git", "reset", "--hard", prepared], cwd=local)

    def switch_head() -> None:
        git.run(["git", "reset", "--hard", replacement], cwd=local)

    runner = GitPushRaceRunner(switch_head)
    monkeypatch.chdir(local)

    with (
        Path(os.devnull).open() as stdin,
        Path(os.devnull).open("w") as stdout,
        Path(os.devnull).open("w") as stderr,
    ):
        push_prepared_commit(
            State(runner=runner, stdin=stdin, stdout=stdout, stderr=stderr), "origin", "main", prepared
        )

    accepted = git.run(["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"]).stdout.strip()
    assert runner.mutated
    assert accepted == prepared


def test_release_tag_push_is_bound_to_validated_tag_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote, local, prepared, replacement = _release_race_repository(tmp_path)
    git = Runner()
    tag = "v1.2.3"
    refspec = f"refs/tags/{tag}"
    git.run(["git", "tag", "-a", tag, "-m", tag, prepared], cwd=local)
    tag_object = git.run(["git", "rev-parse", refspec], cwd=local).stdout.strip()

    def retarget() -> None:
        git.run(["git", "tag", "-f", "-a", tag, "-m", "replacement", replacement], cwd=local)

    runner = GitPushRaceRunner(retarget)
    monkeypatch.chdir(local)
    with (
        Path(os.devnull).open() as stdin,
        Path(os.devnull).open("w") as stdout,
        Path(os.devnull).open("w") as stderr,
    ):
        push_release_tag(State(runner=runner, stdin=stdin, stdout=stdout, stderr=stderr), "origin", tag, prepared)

    accepted_object = git.run(["git", "--git-dir", str(remote), "rev-parse", refspec]).stdout.strip()
    accepted_commit = git.run(["git", "--git-dir", str(remote), "rev-parse", f"{refspec}^{{}}"]).stdout.strip()
    assert runner.mutated
    assert accepted_object == tag_object
    assert accepted_commit == prepared


def test_rejected_release_tag_push_does_not_accept_remote_lightweight_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    git = Runner()
    git.run(["git", "init", "--bare", str(remote)])
    git.run(["git", "init", str(local)])
    git.run(["git", "config", "user.name", "Release Test"], cwd=local)
    git.run(["git", "config", "user.email", "release@example.invalid"], cwd=local)
    (local / "tracked").write_text("release\n")
    git.run(["git", "add", "tracked"], cwd=local)
    git.run(["git", "commit", "-m", "initial"], cwd=local)
    commit = git.run(["git", "rev-parse", "HEAD"], cwd=local).stdout.strip()
    git.run(["git", "remote", "add", "origin", str(remote)], cwd=local)
    git.run(["git", "tag", "v1.2.3"], cwd=local)
    git.run(["git", "push", "origin", "refs/tags/v1.2.3"], cwd=local)
    git.run(["git", "tag", "--delete", "v1.2.3"], cwd=local)
    monkeypatch.chdir(local)

    with (
        Path(os.devnull).open() as stdin,
        Path(os.devnull).open("w") as stdout,
        Path(os.devnull).open("w") as stderr,
        pytest.raises(DotError, match=r"failed to push tag v1\.2\.3 to origin"),
    ):
        push_release_tag(State(runner=git, stdin=stdin, stdout=stdout, stderr=stderr), "origin", "v1.2.3", commit)


def test_local_lightweight_release_tag_is_rejected_before_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    git = Runner()
    git.run(["git", "init", "--bare", str(remote)])
    git.run(["git", "init", str(local)])
    git.run(["git", "config", "user.name", "Release Test"], cwd=local)
    git.run(["git", "config", "user.email", "release@example.invalid"], cwd=local)
    (local / "tracked").write_text("release\n")
    git.run(["git", "add", "tracked"], cwd=local)
    git.run(["git", "commit", "-m", "initial"], cwd=local)
    commit = git.run(["git", "rev-parse", "HEAD"], cwd=local).stdout.strip()
    git.run(["git", "remote", "add", "origin", str(remote)], cwd=local)
    git.run(["git", "tag", "v1.2.3"], cwd=local)
    monkeypatch.chdir(local)

    with (
        Path(os.devnull).open() as stdin,
        Path(os.devnull).open("w") as stdout,
        Path(os.devnull).open("w") as stderr,
        pytest.raises(DotError, match=r"local tag v1\.2\.3 must be annotated"),
    ):
        push_release_tag(State(runner=git, stdin=stdin, stdout=stdout, stderr=stderr), "origin", "v1.2.3", commit)

    assert git.run(["git", "ls-remote", "--tags", "origin", "refs/tags/v1.2.3"], cwd=local).stdout == ""


def test_release_regenerates_valid_lock_and_stages_it(tmp_path: Path) -> None:
    project, original_lock = copy_release_project(tmp_path)
    runner = release_runner(tmp_path)

    assert run_release(make_state(runner), yes=True) == "v1.27.0"

    lock = (project / "uv.lock").read_bytes()
    assert lock != original_lock
    assert b'name = "fmind-dot"\nversion = "1.27.0"' in lock
    Runner().run(
        ["uv", "lock", "--project", str(project), "--check"],
        env={"UV_OFFLINE": "1"},
    )
    assert ("uv", "lock", "--project", "dot") in runner.calls
    assert ("git", "add", "CHANGELOG.md", "dot/pyproject.toml", "dot/uv.lock") in runner.calls


@pytest.mark.parametrize("task", ["test", "build"])
def test_release_failure_restores_regenerated_lock(tmp_path: Path, task: str) -> None:
    project, original_lock = copy_release_project(tmp_path)
    runner = release_runner(tmp_path)
    runner.responses[("mise", "run", task)] = CommandResult("", "", 1)

    with pytest.raises(DotError, match=f"project {task} failed"):
        run_release(make_state(runner), yes=True)

    assert read_release_version(tmp_path) == "1.26.2"
    assert (project / "uv.lock").read_bytes() == original_lock
    assert ("uv", "lock", "--project", "dot") in runner.calls
    Runner().run(
        ["uv", "lock", "--project", str(project), "--check"],
        env={"UV_OFFLINE": "1"},
    )


def test_release_validation_failure_restores_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    original = '[project]\nname = "fmind-dot"\nversion = "1.26.2"\n'
    original_lock = "version = 1\n"
    pyproject.write_text(original)
    (tmp_path / "dot" / "uv.lock").write_text(original_lock)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    parent = "b" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(parent, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(parent, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: migrate", "", 0),
        ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version"): CommandResult(
            "v1.27.0", "", 0
        ),
        ("git", "describe", "--tags", "--abbrev=0"): CommandResult("v1.26.2", "", 0),
        ("mise", "run", "test"): CommandResult("", "", 1),
    }
    state = make_state(runner)

    with pytest.raises(DotError, match="project test failed"):
        run_release(state, yes=True)

    assert pyproject.read_text() == original
    assert (tmp_path / "dot" / "uv.lock").read_text() == original_lock
    assert ("git", "add", "CHANGELOG.md", "dot/pyproject.toml", "dot/uv.lock") not in runner.calls


def test_release_validation_interrupt_restores_files_and_propagates(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    original_project = '[project]\nname = "fmind-dot"\nversion = "1.26.2"\n'
    original_changelog = "# Changelog\n"
    original_lock = "version = 1\n"
    pyproject.write_text(original_project)
    (tmp_path / "dot" / "uv.lock").write_text(original_lock)
    (tmp_path / "CHANGELOG.md").write_text(original_changelog)
    parent = "b" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(parent, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(parent, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: migrate", "", 0),
        ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version"): CommandResult(
            "v1.27.0", "", 0
        ),
        ("git", "describe", "--tags", "--abbrev=0"): CommandResult("v1.26.2", "", 0),
        ("mise", "run", "test"): KeyboardInterrupt(),
    }

    with pytest.raises(KeyboardInterrupt):
        run_release(make_state(runner), yes=True)

    assert pyproject.read_text() == original_project
    assert (tmp_path / "CHANGELOG.md").read_text() == original_changelog
    assert (tmp_path / "dot" / "uv.lock").read_text() == original_lock
    assert ("git", "add", "CHANGELOG.md", "dot/pyproject.toml", "dot/uv.lock") not in runner.calls


def test_release_commit_interrupt_restores_files_and_index_then_propagates(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    original_project = '[project]\nname = "fmind-dot"\nversion = "1.26.2"\n'
    original_changelog = "# Changelog\n"
    original_lock = "version = 1\n"
    pyproject.write_text(original_project)
    (tmp_path / "dot" / "uv.lock").write_text(original_lock)
    (tmp_path / "CHANGELOG.md").write_text(original_changelog)
    parent = "b" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(parent, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(parent, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: migrate", "", 0),
        ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version"): CommandResult(
            "v1.27.0", "", 0
        ),
        ("git", "describe", "--tags", "--abbrev=0"): CommandResult("v1.26.2", "", 0),
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"): CommandResult(
            " M CHANGELOG.md\0 M dot/pyproject.toml\0", "", 0
        ),
        ("git", "commit", "-m", "chore(release): v1.27.0"): KeyboardInterrupt(),
    }

    with pytest.raises(KeyboardInterrupt):
        run_release(make_state(runner), yes=True)

    assert pyproject.read_text() == original_project
    assert (tmp_path / "CHANGELOG.md").read_text() == original_changelog
    assert (tmp_path / "dot" / "uv.lock").read_text() == original_lock
    assert ("git", "reset", "--mixed", "HEAD") in runner.calls


def test_release_validation_rejects_reverted_package_version(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    original_project = '[project]\nname = "fmind-dot"\nversion = "1.26.2"\n'
    pyproject.write_text(original_project)
    (tmp_path / "dot" / "uv.lock").write_text("version = 1\n")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    parent = "b" * 40
    runner = VersionRevertingRunner(pyproject, original_project)
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(parent, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(parent, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: migrate", "", 0),
        ("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version"): CommandResult(
            "v1.27.0", "", 0
        ),
        ("git", "describe", "--tags", "--abbrev=0"): CommandResult("v1.26.2", "", 0),
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"): CommandResult(" M CHANGELOG.md\0", "", 0),
    }

    with pytest.raises(DotError, match="release validation changed the package version"):
        run_release(make_state(runner), yes=True)

    assert pyproject.read_text() == original_project


def test_prepared_release_refreshes_installed_python_cli(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    pyproject.write_text('[project]\nname = "fmind-dot"\nversion = "1.27.0"\n')
    commit = "a" * 40
    tag_object = "c" * 40
    tag_ref = "refs/tags/v1.27.0"
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(commit, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(commit, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("chore(release): v1.27.0", "", 0),
        ("git", "cat-file", "-t", tag_ref): CommandResult("tag", "", 0),
        ("git", "rev-parse", tag_ref): CommandResult(tag_object, "", 0),
        ("git", "cat-file", "-t", tag_object): CommandResult("tag", "", 0),
        ("git", "rev-parse", f"{tag_object}^{{}}"): CommandResult(commit, "", 0),
        ("git", "ls-remote", "--tags", "origin", tag_ref, f"{tag_ref}^{{}}"): CommandResult(
            f"{tag_object}\t{tag_ref}\n{commit}\t{tag_ref}^{{}}\n", "", 0
        ),
    }
    state = make_state(runner)

    assert run_release(state, yes=True) == "v1.27.0"
    assert [("mise", "run", task) for task in ("format", "check", "test", "build")] == [
        call for call in runner.interactive_calls if call[:2] == ("mise", "run")
    ]
    assert ("mise", "run", "--force", "deploy") in runner.calls


@pytest.mark.parametrize("task", ["check", "build"])
def test_prepared_release_gate_failure_blocks_remote_mutation(tmp_path: Path, task: str) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    pyproject.write_text('[project]\nname = "fmind-dot"\nversion = "1.27.0"\n')
    commit = "a" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(commit, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(commit, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("chore(release): v1.27.0", "", 0),
        ("mise", "run", task): CommandResult("", "", 1),
    }

    with pytest.raises(DotError, match=f"project {task} failed"):
        run_release(make_state(runner), yes=True)

    assert all(call[:2] != ("git", "push") for call in runner.interactive_calls)


def test_release_preflight_rejects_missing_tools_and_unsafe_repository_states(tmp_path: Path) -> None:
    missing_git = RecordingRunner()
    missing_git.installed.remove("git")
    with pytest.raises(DotError, match="git is not installed"):
        run_release(make_state(missing_git), yes=True)

    missing_cliff = RecordingRunner()
    missing_cliff.installed.remove("git-cliff")
    with pytest.raises(DotError, match=r"git-cliff is not installed.*mise run tools"):
        run_release(make_state(missing_cliff), yes=True)

    cases: list[tuple[dict[tuple[str, ...], CommandResult | Exception | KeyboardInterrupt], str]] = [
        (
            {("git", "status", "--porcelain"): CommandResult(" M tracked", "", 0)},
            "working directory has uncommitted",
        ),
        (
            {("git", "rev-parse", "--show-toplevel"): CommandResult("", "", 0)},
            "empty repository root",
        ),
        (
            {
                ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
                ("git", "branch", "--show-current"): CommandResult("", "", 0),
            },
            "detached HEAD",
        ),
        (
            {
                ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
                ("git", "branch", "--show-current"): CommandResult("feature", "", 0),
            },
            "requires branch 'main'",
        ),
    ]
    for responses, message in cases:
        runner = RecordingRunner()
        runner.responses = responses
        with pytest.raises(DotError, match=message):
            run_release(make_state(runner), yes=True)


def test_release_refuses_divergence_without_a_direct_prepared_commit(tmp_path: Path) -> None:
    head = "a" * 40
    upstream = "b" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(head, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(upstream, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("feat: unrelated", "", 0),
    }

    with pytest.raises(DotError, match="release branch diverged"):
        run_release(make_state(runner), yes=True)


def test_release_refuses_prepared_commit_with_wrong_parent(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    pyproject.write_text('[project]\nname = "fmind-dot"\nversion = "1.27.0"\n')
    head = "a" * 40
    upstream = "b" * 40
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(head, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(upstream, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("chore(release): v1.27.0", "", 0),
        ("git", "rev-parse", "HEAD^"): CommandResult("c" * 40, "", 0),
    }

    with pytest.raises(DotError, match="not directly ahead"):
        run_release(make_state(runner), yes=True)


def test_release_retry_pushes_a_directly_ahead_prepared_commit(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    pyproject.write_text('[project]\nname = "fmind-dot"\nversion = "1.27.0"\n')
    head = "a" * 40
    upstream = "b" * 40
    tag_object = "c" * 40
    tag_ref = "refs/tags/v1.27.0"
    runner = RecordingRunner()
    runner.responses = {
        ("git", "rev-parse", "--show-toplevel"): CommandResult(str(tmp_path), "", 0),
        ("git", "branch", "--show-current"): CommandResult("main", "", 0),
        ("git", "rev-parse", "HEAD"): CommandResult(head, "", 0),
        ("git", "rev-parse", "origin/main"): CommandResult(upstream, "", 0),
        ("git", "rev-parse", "HEAD^"): CommandResult(upstream, "", 0),
        ("git", "log", "-1", "--pretty=%s"): CommandResult("chore(release): v1.27.0", "", 0),
        ("git", "cat-file", "-t", tag_ref): CommandResult("tag", "", 0),
        ("git", "rev-parse", tag_ref): CommandResult(tag_object, "", 0),
        ("git", "cat-file", "-t", tag_object): CommandResult("tag", "", 0),
        ("git", "rev-parse", f"{tag_object}^{{}}"): CommandResult(head, "", 0),
        ("git", "ls-remote", "--tags", "origin", tag_ref, f"{tag_ref}^{{}}"): CommandResult(
            f"{tag_object}\t{tag_ref}\n{head}\t{tag_ref}^{{}}\n", "", 0
        ),
    }

    assert run_release(make_state(runner), yes=True) == "v1.27.0"

    assert ("git", "push", "origin", f"{head}:refs/heads/main") in runner.interactive_calls
    assert ("git", "push", "origin", f"{tag_object}:{tag_ref}") in runner.interactive_calls


def test_release_no_change_and_cancellation_have_no_side_effects(tmp_path: Path) -> None:
    no_change_runner = release_runner(tmp_path)
    no_change_runner.responses[("git-cliff", "--config", "dot_config/git-cliff/cliff.toml", "--bumped-version")] = (
        CommandResult("v1.26.2", "", 0)
    )
    no_change_state = make_state(no_change_runner)

    assert run_release(no_change_state, yes=True) is None
    assert ("uv", "lock", "--project", "dot") not in no_change_runner.calls
    assert isinstance(no_change_state.stdout, io.StringIO)
    assert "Nothing to release" in no_change_state.stdout.getvalue()

    cancel_runner = release_runner(tmp_path)
    cancel_state = make_state(cancel_runner)
    cancel_state.stdin = io.StringIO("no\n")
    assert run_release(cancel_state) is None
    assert ("uv", "lock", "--project", "dot") not in cancel_runner.calls
    assert isinstance(cancel_state.stdout, io.StringIO)
    assert "Release canceled" in cancel_state.stdout.getvalue()


def test_pyproject_version_update_is_exact_and_release_status_is_confined(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()
    pyproject.write_text('[project]\nname = "fmind-dot"\nversion = "1.26.2"\n\n[tool.demo]\nversion = "9"\n')

    assert read_release_version(tmp_path) == "1.26.2"
    write_release_version(tmp_path, "v1.27.0")
    assert read_release_version(tmp_path) == "1.27.0"
    assert 'version = "9"' in pyproject.read_text()
    validate_release_status(" M CHANGELOG.md\0 M dot/pyproject.toml\0 M dot/uv.lock\0")
    with pytest.raises(DotError, match="unrelated paths"):
        validate_release_status("?? unrelated.txt\0")
    with pytest.raises(DotError, match="renamed or copied"):
        validate_release_status("R  old -> new\0")
    with pytest.raises(DotError, match="ordinary worktree modifications"):
        validate_release_status(" D dot/pyproject.toml\0")


def test_release_metadata_rejects_missing_ambiguous_and_invalid_versions(tmp_path: Path) -> None:
    pyproject = tmp_path / "dot" / "pyproject.toml"
    pyproject.parent.mkdir()

    with pytest.raises(DotError, match="failed to read"):
        read_release_version(tmp_path)

    pyproject.write_text('[tool.demo]\nversion = "1.0.0"\n')
    with pytest.raises(DotError, match=r"must contain a \[project\] table"):
        read_release_version(tmp_path)

    pyproject.write_text("[project]\nversion = 1\n")
    with pytest.raises(DotError, match="exactly one string version"):
        read_release_version(tmp_path)

    pyproject.write_text('[project]\nversion = "1\\u002e2.3"\n')
    with pytest.raises(DotError, match="ambiguous project version"):
        read_release_version(tmp_path)

    with pytest.raises(DotError, match="invalid semantic version tag"):
        write_release_version(tmp_path, "1.2")
    with pytest.raises(DotError, match="malformed git status record"):
        validate_release_status("bad\0")
