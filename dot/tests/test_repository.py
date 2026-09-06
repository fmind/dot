from __future__ import annotations

import io
import json
from collections.abc import Sequence
from pathlib import Path
from threading import Barrier, Lock

import pytest

from fmind_dot.config import AIConfig, Config, PRConfig, PullConfig
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.repository import (
    build_exclude_pathspecs,
    find_git_repositories,
    generate_text,
    get_base_diff,
    git_root,
    pack_diff,
    run_commit,
    run_pull,
    run_pull_request,
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


class InterruptingCommitRunner(RecordingRunner):
    def interactive(self, args: Sequence[str], **kwargs: object) -> int:
        super().interactive(args, **kwargs)
        raise KeyboardInterrupt


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


def test_git_diff_is_root_anchored_and_base_diff_falls_back() -> None:
    expected = ("git", "diff", "main", "--", ":/", ":(exclude,top)uv.lock")
    runner = RecordingRunner(
        {
            ("git", "diff", "main...", "--", ":/", ":(exclude,top)uv.lock"): [result(returncode=1)],
            expected: [result("patch")],
        },
        {"git"},
    )

    assert build_exclude_pathspecs(["uv.lock"]) == [":/", ":(exclude,top)uv.lock"]
    assert get_base_diff(state_with(runner), "main", excludes=["uv.lock"]) == "patch"
    assert runner.calls[-1][0] == expected


def test_pack_diff_keeps_auditable_inventory_when_patch_is_truncated() -> None:
    diff = (
        "diff --git a/docs.md b/docs.md\n--- a/docs.md\n+++ b/docs.md\n@@ -1 +1 @@\n-old\n+new\n"
        "diff --git a/auth.py b/auth.py\n--- a/auth.py\n+++ b/auth.py\n@@ -1 +1 @@\n-old\n+secure\n"
    )
    manifest = pack_diff(diff, 1_000_000)
    budget = len(manifest.encode()) - len(b"@@ -1 +1 @@\n-old\n+new\n")

    packed = pack_diff(diff, budget)

    assert "files: 2" in packed
    assert "docs.md | +1 -1 |" in packed
    assert "auth.py | +1 -1 |" in packed
    assert "secure" in packed
    assert "omitted_hunks=1" in packed


def test_generate_text_limits_utf8_input_and_isolates_working_directory() -> None:
    runner = RecordingRunner({("/tools/agy", "--sandbox", "--prompt", "prompt"): [result(" message \n")]}, {"agy"})

    output = generate_text(state_with(runner), "prompt", "ééé", 5)

    assert output == "message"
    _, cwd, input_text = runner.calls[0]
    assert input_text == "éé"
    assert cwd is not None
    assert not cwd.exists()


def test_commit_restores_initially_clean_index_when_secret_scan_cannot_run() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result(""), result(diff)],
            ("git", "status", "--porcelain"): [result(" M a.py\n")],
            ("git", "add", "-A"): [result()],
            (
                "git",
                "diff",
                "--cached",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("git", "reset", "--mixed"): [result()],
        },
        {"git", "agy"},
    )

    with pytest.raises(DotError, match="gitleaks"):
        run_commit(state_with(runner))

    assert runner.calls[-1][0] == ("git", "reset", "--mixed")


def test_commit_restores_auto_staged_index_when_editor_is_interrupted() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    commit_config = Config().commit
    prompt = commit_config.prompt % ", ".join(commit_config.allowed_types)
    runner = InterruptingCommitRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result(""), result(diff)],
            ("git", "status", "--porcelain"): [result(" M a.py\n")],
            ("git", "add", "-A"): [result()],
            (
                "git",
                "diff",
                "--cached",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result()],
            ("/tools/agy", "--sandbox", "--prompt", prompt): [result("fix: message")],
            ("git", "reset", "--mixed"): [result()],
        },
        {"git", "gitleaks", "agy"},
    )

    with pytest.raises(KeyboardInterrupt):
        run_commit(state_with(runner))

    assert runner.calls[-1][0] == ("git", "reset", "--mixed")


def test_pull_request_scans_generated_input_and_uses_private_temporary_body() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    filtered = (
        "git",
        "diff",
        "main...",
        "--",
        ":/",
        ":(exclude,top)*-lock.json",
        ":(exclude,top)uv.lock",
    )
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            filtered: [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result(), result()],
            ("/tools/agy", "--sandbox", "--prompt", Config().pr.prompt): [result("PR body")],
        },
        {"git", "gh", "gitleaks", "agy"},
    )

    description = run_pull_request(
        state_with(runner),
        title="Change",
        draft=True,
        labels=["python"],
        reviewers=["reviewer"],
        assignees=["owner"],
    )

    assert description == "PR body"
    assert runner.interactive_payloads == ["PR body"]
    args = runner.interactive_calls[0]
    assert args[:6] == ("/tools/gh", "pr", "create", "--base", "main", "--body-file")
    assert "--draft" in args
    assert args[-6:] == ("--label", "python", "--reviewer", "reviewer", "--assignee", "owner")
    assert not Path(args[6]).exists()


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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))

    results = run_pull(state_with(runner, config), push=True)

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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))

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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))
    state = state_with(runner, config)

    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(state)

    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "sample [main]" in output
    assert "timed out" in output
    assert "no upstream" not in output


def test_pull_request_reports_invalid_template_path(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result(f"{tmp_path}\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
        },
        {"git", "gh"},
    )
    config = Config(pr=PRConfig(templates=["blocker/PULL_REQUEST_TEMPLATE.md"]))

    with pytest.raises(DotError, match="failed to inspect PR template"):
        run_pull_request(state_with(runner, config))


def test_pull_request_rejects_relative_symlink_template_before_ai(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    template_path = repository / ".github" / "pull_request_template.md"
    template_path.parent.mkdir(parents=True)
    secret_path = tmp_path / "outside-secret"
    secret_path.write_text("private local content", encoding="utf-8")
    template_path.symlink_to(secret_path)
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result(f"{repository}\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
        },
        {"git", "gh", "gitleaks", "agy"},
    )

    with pytest.raises(DotError, match="relative PR template must be a regular file"):
        run_pull_request(state_with(runner))

    assert not any(call[0][0] in {"/tools/gitleaks", "/tools/agy"} for call in runner.calls)


def test_pull_request_scans_final_prompt_with_template_before_ai(tmp_path: Path) -> None:
    template = "template-secret-marker"
    template_path = tmp_path / ".github" / "pull_request_template.md"
    template_path.parent.mkdir()
    template_path.write_text(template, encoding="utf-8")
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    prompt = Config().pr.prompt + "\n\nFollow the repository pull request template below:\n\n" + template
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result(f"{tmp_path}\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result(returncode=1)],
        },
        {"git", "gh", "gitleaks", "agy"},
    )

    with pytest.raises(DotError, match="outgoing prompt secret scan failed") as raised:
        run_pull_request(state_with(runner))

    assert template not in str(raised.value)
    assert runner.calls[-1][2] == prompt
    assert not any(call[0][0] == "/tools/agy" for call in runner.calls)


def test_pull_request_uses_default_template_when_configured_list_is_empty(tmp_path: Path) -> None:
    template = "## Test plan\n"
    template_path = tmp_path / ".github" / "pull_request_template.md"
    template_path.parent.mkdir()
    template_path.write_text(template, encoding="utf-8")
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    prompt = Config().pr.prompt + "\n\nFollow the repository pull request template below:\n\n" + template
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result(f"{tmp_path}\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result(), result()],
            ("/tools/agy", "--sandbox", "--prompt", prompt): [result("PR body")],
        },
        {"git", "gh", "gitleaks", "agy"},
    )
    config = Config(pr=PRConfig(templates=[]))

    assert run_pull_request(state_with(runner, config)) == "PR body"


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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))

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
    assert document == {"docker": {"installed": True, "running": False}, "repositories": []}


@pytest.mark.parametrize("invalid", ["plain text\n", "\n", "\ud800"])
def test_pack_diff_rejects_non_git_or_non_utf8_input(invalid: str) -> None:
    with pytest.raises(DotError, match=r"unified Git diff|no changed files|valid UTF-8"):
        pack_diff(invalid)


def test_pack_diff_rejects_budget_below_auditable_manifest() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"

    with pytest.raises(DotError, match=r"cannot hold.*omission manifest"):
        pack_diff(diff, 1)

    assert pack_diff(diff, 0).endswith("-a\n+b\n")


def test_pack_diff_inventories_quoted_binary_path() -> None:
    diff = 'diff --git "a/assets/file name.bin" "b/assets/file name.bin"\nBinary files differ\n'

    packed = pack_diff(diff)

    assert "assets/file name.bin | +0 -0 | status=complete" in packed
    assert "Binary files differ" in packed


def test_git_root_and_ai_failures_have_context_without_payloads() -> None:
    with pytest.raises(DotError, match="required tool is not installed: git"):
        git_root(state_with(RecordingRunner({}, set())))

    failing_root = RecordingRunner(
        {("git", "rev-parse", "--show-toplevel"): [result(returncode=128)]},
        {"git"},
    )
    with pytest.raises(DotError, match="not inside a git work tree"):
        git_root(state_with(failing_root))

    empty_ai = RecordingRunner({("/tools/llm", "--prompt", "summarize"): [result()]}, {"llm"})
    with pytest.raises(DotError, match="AI returned empty output"):
        generate_text(state_with(empty_ai, Config(ai=AIConfig(binary="llm"))), "summarize", "input")
    assert empty_ai.calls[0][0] == ("/tools/llm", "--prompt", "summarize")


def test_commit_no_changes_is_a_clean_noop() -> None:
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result()],
            ("git", "status", "--porcelain"): [result()],
        },
        {"git"},
    )
    state = state_with(runner)

    assert run_commit(state) is None
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == "No changes to commit.\n"
    assert runner.interactive_calls == []


def test_commit_scans_packed_staged_diff_and_forwards_prompt_hints() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    commit_config = Config().commit
    prompt = commit_config.prompt % ", ".join(commit_config.allowed_types)
    prompt += " Use type 'fix' and scope 'cli'."
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "--cached",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result()],
            ("/tools/agy", "--sandbox", "--prompt", prompt): [result("fix(cli): explain failure")],
        },
        {"git", "gitleaks", "agy"},
    )

    message = run_commit(state_with(runner), "fix", "cli")

    assert message == "fix(cli): explain failure"
    assert runner.interactive_calls == [("git", "commit", "-e", "-m", message)]
    scanned = next(call[2] for call in runner.calls if call[0][0] == "/tools/gitleaks")
    generated = next(call[2] for call in runner.calls if call[0][0] == "/tools/agy")
    assert scanned == generated
    assert scanned is not None
    assert "# Diff summary" in scanned


def test_commit_rejects_changes_excluded_from_ai_input_without_touching_index() -> None:
    diff = "diff --git a/uv.lock b/uv.lock\n--- a/uv.lock\n+++ b/uv.lock\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "--cached",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result()],
        },
        {"git"},
    )

    with pytest.raises(DotError, match="every changed path is excluded"):
        run_commit(state_with(runner))

    assert not any(call[0][1] == "reset" for call in runner.calls)


def test_commit_surfaces_failure_to_restore_auto_staged_index() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "--cached", "--", ":/"): [result(), result(diff)],
            ("git", "status", "--porcelain"): [result("?? a.py\n")],
            ("git", "add", "-A"): [result()],
            (
                "git",
                "diff",
                "--cached",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("git", "reset", "--mixed"): [result(returncode=1)],
        },
        {"git"},
    )

    with pytest.raises(DotError, match="failed to restore initially clean index"):
        run_commit(state_with(runner))


def test_pull_request_no_changes_is_a_clean_noop() -> None:
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "main...", "--", ":/"): [result()],
        },
        {"git", "gh"},
    )
    state = state_with(runner)

    assert run_pull_request(state) is None
    assert isinstance(state.stdout, io.StringIO)
    assert "No changes detected against base branch 'main'." in state.stdout.getvalue()


def test_pull_request_rejects_relative_template_escape(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("private", encoding="utf-8")
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result(f"{repository}\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
        },
        {"git", "gh"},
    )
    config = Config(pr=PRConfig(templates=["../outside.md"]))

    with pytest.raises(DotError, match="escapes repository root"):
        run_pull_request(state_with(runner, config))


def test_pull_request_reports_cli_failure_and_removes_temporary_body() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n"
    runner = RecordingRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): [result("/repo\n")],
            ("git", "diff", "main...", "--", ":/"): [result(diff)],
            (
                "git",
                "diff",
                "main...",
                "--",
                ":/",
                ":(exclude,top)*-lock.json",
                ":(exclude,top)uv.lock",
            ): [result(diff)],
            ("/tools/gitleaks", "stdin", "--no-banner", "--redact"): [result(), result()],
            ("/tools/agy", "--sandbox", "--prompt", Config().pr.prompt): [result("PR body")],
        },
        {"git", "gh", "gitleaks", "agy"},
        interactive_status=2,
    )

    with pytest.raises(DotError, match="gh pr create failed with status 2"):
        run_pull_request(state_with(runner))

    body_path = Path(runner.interactive_calls[0][6])
    assert not body_path.exists()


def test_pull_with_no_repositories_reports_a_clean_noop(tmp_path: Path) -> None:
    state = state_with(
        RecordingRunner({}, {"git"}),
        Config(pull=PullConfig(directories=[str(tmp_path)], concurrency=2, timeout="1s")),
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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))
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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))
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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))
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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=2, timeout="5s"))

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
    config = Config(pull=PullConfig(directories=[str(workspace)], concurrency=1, timeout="1s"))

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

    status = run_status(state, as_json=True)

    assert status.docker.details == "inspection command failed"
    assert status.repositories[0].error
    assert isinstance(state.stdout, io.StringIO)
    document = json.loads(state.stdout.getvalue())
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
