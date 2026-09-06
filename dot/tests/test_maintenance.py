from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import IO

import pytest
import typer
from typer import _click
from typer.testing import CliRunner, Result

import fmind_dot.maintenance as maintenance
from fmind_dot.config import Config, SessionStoreConfig
from fmind_dot.errors import DotError
from fmind_dot.maintenance import (
    PruneOptions,
    backup_orphans,
    get_chezmoi_target_path,
    push_prepared_commit,
    push_release_tag,
    read_release_version,
    register,
    remote_release_tag_commit,
    run_chezmoi_clean,
    run_prune,
    run_release,
    validate_prune_path,
    validate_release_status,
    write_release_version,
)
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


class RecordingRunner(Runner):
    def __init__(self) -> None:
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
    ) -> int:
        del cwd, stdin, stdout, stderr, env
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
    ) -> int:
        code = super().interactive(args, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr, env=env)
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


def invoke_prune(
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    *,
    state: State | None = None,
) -> tuple[Result, list[PruneOptions]]:
    captured: list[PruneOptions] = []

    def capture(_state: State, options: PruneOptions) -> int:
        captured.append(options)
        return 0

    monkeypatch.setattr(maintenance, "run_prune", capture)
    app = typer.Typer()
    register(app)
    result = CliRunner().invoke(app, ["prune", *args], obj=state or make_state())
    return result, captured


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


def test_registration_exposes_python_maintenance_contract() -> None:
    app = typer.Typer()
    register(app)

    root = CliRunner().invoke(app, ["--help"])
    prune = CliRunner().invoke(app, ["prune", "--help"])

    assert root.exit_code == 0
    assert {"chezmoi", "prune", "release"} <= set(_click.utils.strip_ansi(root.stdout).split())
    assert prune.exit_code == 0
    prune_output = _click.utils.strip_ansi(prune.stdout)
    for target, levels in {
        "--agents": "[=sessions]",
        "--docker": "[=build|system]",
        "--python": "[=cache|all]",
        "--mise": "[=cache|configs]",
        "--tools": "[=cache]",
        "--all": "[=shallow|deep]",
    }.items():
        assert target in prune_output
        assert levels in prune_output
    assert "--go" not in prune_output
    assert "--node" not in prune_output


def test_prune_cli_bare_flags_use_configured_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    state = make_state()
    state.config.prune.docker.level = "system"
    state.config.prune.python.level = "all"
    state.config.prune.mise.level = "configs"

    result, captured = invoke_prune(
        monkeypatch,
        ["--agents", "--docker", "--python", "--mise", "--tools"],
        state=state,
    )

    assert result.exit_code == 0
    assert captured == [
        PruneOptions(
            targets={
                "agents": "sessions",
                "docker": "system",
                "python": "all",
                "mise": "configs",
                "tools": "cache",
            }
        )
    ]


@pytest.mark.parametrize(
    "args",
    [
        ["-a", "-d", "-p", "-m", "-t"],
        ["-A"],
    ],
)
def test_prune_cli_bare_short_flags_compose(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    result, captured = invoke_prune(monkeypatch, args)

    assert result.exit_code == 0
    assert captured == [
        PruneOptions(
            targets={
                "agents": "sessions",
                "docker": "build",
                "python": "cache",
                "mise": "cache",
                "tools": "cache",
            }
        )
    ]


@pytest.mark.parametrize("option", ["--all", "--all=shallow"])
def test_prune_cli_all_accepts_bare_and_shallow_levels(monkeypatch: pytest.MonkeyPatch, option: str) -> None:
    result, captured = invoke_prune(monkeypatch, [option])

    assert result.exit_code == 0
    assert captured == [
        PruneOptions(
            targets={
                "agents": "sessions",
                "docker": "build",
                "python": "cache",
                "mise": "cache",
                "tools": "cache",
            }
        )
    ]


def test_prune_cli_accepts_explicit_named_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    result, captured = invoke_prune(
        monkeypatch,
        ["--agents=sessions", "--docker=system", "--python=all", "--mise=configs", "--tools=cache"],
    )

    assert result.exit_code == 0
    assert captured == [
        PruneOptions(
            targets={
                "agents": "sessions",
                "docker": "system",
                "python": "all",
                "mise": "configs",
                "tools": "cache",
            }
        )
    ]


def test_prune_cli_all_deep_allows_explicit_target_override(monkeypatch: pytest.MonkeyPatch) -> None:
    result, captured = invoke_prune(monkeypatch, ["--all=deep", "--docker=build"])

    assert result.exit_code == 0
    assert captured == [
        PruneOptions(
            targets={
                "agents": "sessions",
                "docker": "build",
                "python": "all",
                "mise": "configs",
                "tools": "cache",
            }
        )
    ]


@pytest.mark.parametrize(
    ("option", "expected"),
    [
        ("--agents=invalid", "expected one of: sessions"),
        ("--docker=invalid", "expected one of: build, system"),
        ("--python=invalid", "expected one of: cache, all"),
        ("--mise=invalid", "expected one of: cache, configs"),
        ("--tools=invalid", "expected one of: cache"),
        ("--all=invalid", "expected one of: shallow, deep"),
    ],
)
def test_prune_cli_rejects_invalid_levels_before_running(
    monkeypatch: pytest.MonkeyPatch, option: str, expected: str
) -> None:
    result, captured = invoke_prune(monkeypatch, [option])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert expected in str(result.exception)
    assert captured == []


def test_registered_prune_command_uses_state_and_registration_is_idempotent() -> None:
    app = typer.Typer()
    register(app)
    register(app)
    runner = RecordingRunner()
    state = make_state(runner)

    result = CliRunner().invoke(app, ["prune", "--python", "--deep", "--dry-run"], obj=state)

    assert result.exit_code == 0
    assert isinstance(state.stdout, io.StringIO)
    assert "Prune (dry run)" in state.stdout.getvalue()
    assert "would cleaned the uv cache" in state.stdout.getvalue()
    assert runner.calls == []


def test_registered_prune_command_fails_without_cli_state() -> None:
    app = typer.Typer()
    register(app)

    result = CliRunner().invoke(app, ["prune"])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert str(result.exception) == "CLI state is unavailable"


def test_prune_dry_run_preserves_confined_cache_and_uses_python_first_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache = tmp_path / ".cache" / "trivy"
    cache.mkdir(parents=True)
    (cache / "db.bin").write_bytes(b"1234")
    runner = RecordingRunner()
    state = make_state(runner)
    state.config.prune.tools.paths = [str(cache)]

    reclaimed = run_prune(
        state,
        PruneOptions(targets={"python": "cache", "mise": "cache", "tools": "cache"}, dry_run=True),
    )

    assert reclaimed == 4
    assert cache.exists()
    assert ("uv", "cache", "prune") not in runner.calls
    assert ("mise", "prune", "-y") not in runner.calls
    assert isinstance(state.stdout, io.StringIO)
    assert "Would reclaim 4 B" in state.stdout.getvalue()


def test_prune_executes_only_python_first_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = RecordingRunner()
    state = make_state(runner)
    state.config.prune.mise.paths = []
    state.config.prune.tools.paths = []

    run_prune(
        state,
        PruneOptions(targets={"python": "all", "mise": "configs", "tools": "cache"}),
    )

    assert runner.calls == [
        ("uv", "cache", "clean"),
        ("pip", "cache", "purge"),
        ("mise", "prune", "-y"),
        ("mise", "cache", "clear"),
        ("mise", "prune", "--configs", "-y"),
        ("dprint", "clear-cache"),
    ]


def test_prune_mise_contents_stays_bound_to_open_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache = tmp_path / ".local" / "share" / "mise" / "downloads"
    cache.mkdir(parents=True)
    (cache / "cached.tar").write_text("discard")
    original_cache = cache.with_name("downloads-original")
    outside = tmp_path / "sibling"
    outside.mkdir()
    outside_victim = outside / "cached.tar"
    outside_victim.write_text("preserve")
    real_directory_bytes = maintenance._directory_bytes_confined  # noqa: SLF001 - exercise the race boundary.
    swapped = False

    def race_directory_bytes(directory_fd: int) -> int:
        nonlocal swapped
        size = real_directory_bytes(directory_fd)
        cache.rename(original_cache)
        cache.symlink_to(outside, target_is_directory=True)
        swapped = True
        return size

    monkeypatch.setattr(maintenance, "_directory_bytes_confined", race_directory_bytes)
    state = make_state()
    state.config.prune.mise.paths = [str(cache)]

    run_prune(state, PruneOptions(targets={"mise": "cache"}))

    assert swapped
    assert list(original_cache.iterdir()) == []
    assert cache.is_symlink()
    assert outside_victim.read_text() == "preserve"


def test_prune_tool_tree_fails_closed_if_open_directory_is_renamed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache = tmp_path / ".cache" / "trivy"
    cache.mkdir(parents=True)
    (cache / "db.bin").write_text("discard")
    original_cache = cache.with_name("trivy-original")
    outside = tmp_path / "sibling"
    outside.mkdir()
    outside_victim = outside / "db.bin"
    outside_victim.write_text("preserve")
    real_directory_bytes = maintenance._directory_bytes_confined  # noqa: SLF001 - exercise the race boundary.

    def race_directory_bytes(directory_fd: int) -> int:
        size = real_directory_bytes(directory_fd)
        cache.rename(original_cache)
        cache.symlink_to(outside, target_is_directory=True)
        return size

    monkeypatch.setattr(maintenance, "_directory_bytes_confined", race_directory_bytes)
    state = make_state()
    state.config.prune.tools.paths = [str(cache)]

    with pytest.raises(DotError, match="prune path changed during deletion"):
        run_prune(state, PruneOptions(targets={"tools": "cache"}))

    assert list(original_cache.iterdir()) == []
    assert cache.is_symlink()
    assert outside_victim.read_text() == "preserve"


def test_prune_configured_path_fails_closed_without_descriptor_confinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache = tmp_path / ".cache" / "trivy"
    cache.mkdir(parents=True)
    victim = cache / "db.bin"
    victim.write_text("preserve")
    monkeypatch.setattr(maintenance.os, "O_NOFOLLOW", 0)
    state = make_state()
    state.config.prune.tools.paths = [str(cache)]

    with pytest.raises(DotError, match="cannot safely confine filesystem deletion"):
        run_prune(state, PruneOptions(targets={"tools": "cache"}))

    assert victim.read_text() == "preserve"


def test_prune_rejects_parent_traversal_before_removing_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    (home / ".cache").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "keep.txt"
    victim.write_text("preserve")
    monkeypatch.setenv("HOME", str(home))
    runner = RecordingRunner()
    state = make_state(runner)
    state.config.prune.tools.paths = [str(home / ".cache" / ".." / ".." / "outside")]

    with pytest.raises(DotError, match="parent traversal"):
        run_prune(state, PruneOptions(targets={"tools": "cache"}))

    assert victim.read_text() == "preserve"
    assert runner.calls == []


@pytest.mark.parametrize("suffix", [".cache/..", "../outside", ".cache/../../outside"])
def test_validate_prune_path_rejects_parent_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(DotError, match="parent traversal"):
        validate_prune_path(tmp_path / suffix)


def test_validate_prune_path_rejects_home_and_link_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    linked = tmp_path / ".cache-link"
    linked.symlink_to(outside, target_is_directory=True)

    with pytest.raises(DotError, match="home directory"):
        validate_prune_path(tmp_path)
    with pytest.raises(DotError, match="symbolic-link"):
        validate_prune_path(linked / "tool")

    monkeypatch.chdir(tmp_path)
    with pytest.raises(DotError, match="non-absolute"):
        validate_prune_path(".cache/tool")


def test_prune_validates_requests_and_resolves_configured_levels() -> None:
    state = make_state()
    state.config.prune.python.level = "all"

    assert maintenance.resolve_prune_targets(state, {"python": None}, all_targets=False, deep=False) == {
        "python": "all"
    }
    assert maintenance.resolve_prune_targets(state, {}, all_targets=True, deep=True) == {
        "agents": "sessions",
        "docker": "system",
        "python": "all",
        "mise": "configs",
        "tools": "cache",
    }
    assert maintenance.human_bytes(17) == "17 B"
    assert maintenance.human_bytes(1536) == "1.5 KiB"
    assert maintenance.human_bytes(1024**4) == "1.0 TiB"

    state.config.prune.python.level = "invalid"
    with pytest.raises(DotError, match=r"invalid prune\.python\.level"):
        maintenance.resolve_prune_targets(state, {"python": None}, all_targets=False, deep=False)
    with pytest.raises(DotError, match="retention days cannot be negative"):
        run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=-1))
    with pytest.raises(DotError, match="unknown prune target"):
        run_prune(state, PruneOptions(targets={"unknown": "cache"}))
    with pytest.raises(DotError, match="invalid level"):
        run_prune(state, PruneOptions(targets={"python": "invalid"}))

    assert run_prune(state, PruneOptions(targets={})) == 0
    assert isinstance(state.stdout, io.StringIO)
    assert "No target selected" in state.stdout.getvalue()


def test_prune_removes_files_trees_and_reports_absent_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    tree = tmp_path / ".cache" / "tree"
    nested = tree / "nested"
    nested.mkdir(parents=True)
    (nested / "payload").write_bytes(b"abc")
    file = tmp_path / ".cache" / "single.bin"
    file.write_bytes(b"wxyz")
    absent = tmp_path / ".cache" / "absent"
    state = make_state()
    state.config.prune.tools.paths = [str(tree), str(file), str(absent)]

    reclaimed = run_prune(state, PruneOptions(targets={"tools": "cache"}))

    assert reclaimed == 7
    assert not tree.exists()
    assert not file.exists()
    assert not absent.exists()
    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    assert "removed" in output
    assert "nothing to remove" in output


def test_prune_reports_unavailable_tools_and_all_docker_modes() -> None:
    unavailable = RecordingRunner()
    unavailable.installed -= {"docker", "dprint", "pip", "uv"}
    unavailable_state = make_state(unavailable)
    unavailable_state.config.prune.tools.paths = []

    run_prune(
        unavailable_state,
        PruneOptions(targets={"docker": "system", "python": "all", "tools": "cache"}),
    )

    assert isinstance(unavailable_state.stdout, io.StringIO)
    output = unavailable_state.stdout.getvalue()
    for command in ("docker", "uv", "pip", "dprint"):
        assert f"{command} is not installed" in output

    dry_runner = RecordingRunner()
    dry_state = make_state(dry_runner)
    run_prune(dry_state, PruneOptions(targets={"docker": "system"}, dry_run=True))
    assert dry_runner.calls == []
    assert isinstance(dry_state.stdout, io.StringIO)
    assert "would prune the Docker build cache" in dry_state.stdout.getvalue()
    assert "would prune stopped containers" in dry_state.stdout.getvalue()

    stopped_runner = RecordingRunner()
    stopped_runner.responses[("docker", "info")] = CommandResult("", "", 1)
    stopped_state = make_state(stopped_runner)
    run_prune(stopped_state, PruneOptions(targets={"docker": "build"}))
    assert isinstance(stopped_state.stdout, io.StringIO)
    assert "docker daemon is not running" in stopped_state.stdout.getvalue()

    running_runner = RecordingRunner()
    run_prune(make_state(running_runner), PruneOptions(targets={"docker": "system"}))
    assert running_runner.calls == [
        ("docker", "info"),
        ("docker", "builder", "prune", "-af"),
        ("docker", "system", "prune", "-f"),
    ]


def _digest(*values: str) -> str:
    hasher = hashlib.sha256()
    for value in values:
        hasher.update(value.encode())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _write_successor(home: Path, source: str, session_id: str, raw: Path) -> Path:
    fingerprint = hashlib.sha256(raw.read_bytes()).hexdigest()
    lineage = _digest(source, session_id)
    generation = home / ".agents" / "sessions" / "v1" / source / lineage / _digest("1", fingerprint)
    generation.mkdir(mode=0o700, parents=True)
    generation.chmod(0o700)
    transcript = json.dumps({"ts": "", "agent": source, "sid": session_id, "role": "user", "content": "saved"}) + "\n"
    transcript_path = generation / "transcript.jsonl"
    transcript_path.write_text(transcript)
    transcript_path.chmod(0o600)
    manifest = {
        "parser_version": "1",
        "agent": source,
        "session_id": session_id,
        "lineage_id": lineage,
        "source_type": f"{source}-jsonl",
        "source_fingerprint": fingerprint,
        "ingested_at": "2026-09-01T00:00:00Z",
        "completeness": "complete",
        "transcript_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
        "schema_version": 1,
        "record_count": 1,
        "malformed_records": 0,
        "skipped_records": 0,
    }
    manifest_path = generation / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    manifest_path.chmod(0o600)
    return generation


def test_session_identity_accepts_only_supported_source_layouts(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    raw_session_identity = maintenance._raw_session_identity  # noqa: SLF001 - test source-layout safety.

    assert raw_session_identity(root, root / "claude-id.jsonl", "claude") == "claude-id"
    assert raw_session_identity(root, root / "memory.jsonl", "claude") is None
    assert (
        raw_session_identity(
            root,
            root / "2026" / "rollout-2026-09-06T10-20-30-codex_id.jsonl",
            "codex",
        )
        == "codex_id"
    )
    assert raw_session_identity(root, root / "grok-id" / "updates.jsonl", "grok") == "grok-id"
    assert raw_session_identity(root, root / "agy-id" / "task" / "transcript_full.jsonl", "agy") == "agy-id"
    assert raw_session_identity(root, root / "invalid space.jsonl", "claude") is None
    assert raw_session_identity(root, root / "session.jsonl", "unknown") is None


def test_successor_evidence_distinguishes_fail_closed_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    find_successor = maintenance._find_successor  # noqa: SLF001 - test fail-closed classifications.
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    interrupted_id = "interrupted"
    interrupted_lineage = _digest("claude", interrupted_id)
    interrupted = tmp_path / ".agents" / "sessions" / "v1" / "claude" / interrupted_lineage / ".ingest-run"
    interrupted.mkdir(parents=True)

    partial_raw = raw_root / "partial.jsonl"
    partial_raw.write_text("partial")
    partial = _write_successor(tmp_path, "claude", "partial", partial_raw)
    partial_manifest = partial / "manifest.json"
    partial_value = json.loads(partial_manifest.read_text())
    partial_value["completeness"] = "partial"
    partial_manifest.write_text(json.dumps(partial_value))

    stale_raw = raw_root / "stale.jsonl"
    stale_raw.write_text("stale")
    _write_successor(tmp_path, "claude", "stale", stale_raw)

    ambiguous_raw = raw_root / "ambiguous.jsonl"
    ambiguous_raw.write_text("ambiguous")
    duplicate = _write_successor(tmp_path, "claude", "ambiguous", ambiguous_raw)
    shutil.copytree(duplicate, duplicate.with_name("duplicate"))

    unreadable_id = "unreadable"
    unreadable_lineage = _digest("claude", unreadable_id)
    unreadable = tmp_path / ".agents" / "sessions" / "v1" / "claude" / unreadable_lineage
    unreadable.mkdir(parents=True)
    (unreadable / "not-a-generation").write_text("invalid")

    assert find_successor("claude", "missing", "fingerprint").reason == "unnormalized"
    assert find_successor("claude", interrupted_id, "fingerprint").reason == "interrupted-ingestion"
    assert find_successor("claude", "partial", hashlib.sha256(b"partial").hexdigest()).reason == "partial-successor"
    assert find_successor("claude", "stale", "different").reason == "stale-successor"
    assert (
        find_successor("claude", "ambiguous", hashlib.sha256(b"ambiguous").hexdigest()).reason == "verified-successor"
    )
    assert find_successor("claude", unreadable_id, "fingerprint").reason == "unreadable-successor"

    duplicate.rename(duplicate.with_name("misnamed-generation"))
    assert (
        find_successor("claude", "ambiguous", hashlib.sha256(b"ambiguous").hexdigest()).reason == "unreadable-successor"
    )


def test_raw_session_dry_run_reports_each_retention_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".claude" / "projects"
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "memory").mkdir()
    (root / "linked-directory").symlink_to(outside, target_is_directory=True)
    protected = root / "memory.jsonl"
    recent = root / "recent.jsonl"
    unrecognized = root / "notes.txt"
    unreadable = root / "unreadable.jsonl"
    linked_file = root / "linked.jsonl"
    for path in (protected, recent, unrecognized, unreadable):
        path.write_text(path.name)
    linked_file.symlink_to(outside / "missing")
    old = 1_700_000_000
    for path in (protected, unrecognized, unreadable):
        os.utime(path, (old, old))
    real_fingerprint_at = maintenance._fingerprint_at  # noqa: SLF001

    def fail_one_fingerprint(directory_fd: int, name: str) -> str:
        if name == unreadable.name:
            raise OSError("simulated read failure")
        return real_fingerprint_at(directory_fd, name)

    monkeypatch.setattr(maintenance, "_fingerprint_at", fail_one_fingerprint)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(root), source="claude", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}, dry_run=True))

    assert reclaimed == 0
    assert all(path.exists() for path in (protected, recent, unrecognized, unreadable))
    assert linked_file.is_symlink()
    assert isinstance(state.stdout, io.StringIO)
    output = state.stdout.getvalue()
    for reason in (
        "protected-tree",
        "link-or-special-file",
        "protected-name",
        "within-retention",
        "unrecognized-source",
        "unreadable-source",
    ):
        assert f"reason={reason}" in output


def test_grok_prune_removes_verified_transcript_and_sibling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".grok" / "sessions"
    session = root / "grok-id"
    session.mkdir(parents=True)
    transcript = session / "updates.jsonl"
    sibling = session / "chat_history.jsonl"
    transcript.write_text("verified raw")
    sibling.write_text("related raw")
    old = 1_700_000_000
    os.utime(transcript, (old, old))
    os.utime(sibling, (old, old))
    _write_successor(tmp_path, "grok", "grok-id", transcript)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(root), source="grok", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}))

    assert reclaimed == len("verified raw") + len("related raw")
    assert not transcript.exists()
    assert not sibling.exists()
    assert not session.exists()


def test_grok_prune_retains_whole_session_when_chat_history_is_recent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".grok" / "sessions"
    session = root / "grok-id"
    session.mkdir(parents=True)
    transcript = session / "updates.jsonl"
    sibling = session / "chat_history.jsonl"
    transcript.write_text("verified raw")
    sibling.write_text("recent related raw")
    os.utime(transcript, (1_700_000_000, 1_700_000_000))
    _write_successor(tmp_path, "grok", "grok-id", transcript)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(root), source="grok", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}))

    assert reclaimed == 0
    assert transcript.read_text() == "verified raw"
    assert sibling.read_text() == "recent related raw"
    assert isinstance(state.stdout, io.StringIO)
    assert "deleted 0 file(s)" in state.stdout.getvalue()


def test_archive_dry_run_counts_only_expired_regular_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".cache" / "archive"
    lineage = root / "lineage"
    lineage.mkdir(parents=True)
    expired = lineage / "expired.json"
    recent = lineage / "recent.json"
    protected = lineage / "memory.jsonl"
    linked = lineage / "linked.json"
    expired.write_text("expired")
    recent.write_text("recent")
    protected.write_text("protected")
    linked.symlink_to(expired)
    old = 1_700_000_000
    os.utime(expired, (old, old))
    os.utime(protected, (old, old))
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(root), source="archive", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}, dry_run=True))

    assert reclaimed == len("expired")
    assert all(path.exists() for path in (expired, recent, protected))
    assert linked.is_symlink()
    assert isinstance(state.stdout, io.StringIO)
    assert "would delete 1 file(s)" in state.stdout.getvalue()


def test_agent_prune_reports_absent_stores_and_aggregates_invalid_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    empty_state = make_state()
    empty_state.config.prune.agents.sessions = []

    run_prune(empty_state, PruneOptions(targets={"agents": "sessions"}))

    assert isinstance(empty_state.stdout, io.StringIO)
    assert "no session stores found" in empty_state.stdout.getvalue()

    invalid_state = make_state()
    invalid_state.config.prune.agents.sessions = [
        SessionStoreConfig(path=str(tmp_path / "missing"), source="unsupported"),
        SessionStoreConfig(path=str(tmp_path.parent / "outside"), source="archive"),
    ]
    with pytest.raises(DotError, match=r"invalid session source.*invalid agent session path"):
        run_prune(invalid_state, PruneOptions(targets={"agents": "sessions"}))


def test_agent_prune_requires_exact_complete_successor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".claude" / "projects" / "project"
    root.mkdir(parents=True)
    verified = root / "verified.jsonl"
    retained = root / "retained.jsonl"
    verified.write_text("raw verified")
    retained.write_text("raw retained")
    old = 1_700_000_000
    os.utime(verified, (old, old))
    os.utime(retained, (old, old))
    successor = _write_successor(tmp_path, "claude", "verified", verified)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path="~/.claude/projects", source="claude", keep_days=7)]

    run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert not verified.exists()
    assert retained.exists()
    assert successor.exists()
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=unnormalized" in state.stdout.getvalue()


def test_agent_prune_deletion_stays_bound_to_open_session_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store = tmp_path / ".claude" / "projects"
    project = store / "project"
    project.mkdir(parents=True)
    raw = project / "session.jsonl"
    raw.write_text("verified raw session")
    os.utime(raw, (1_700_000_000, 1_700_000_000))
    _write_successor(tmp_path, "claude", "session", raw)

    outside = tmp_path / "outside"
    outside.mkdir()
    outside_victim = outside / raw.name
    outside_victim.write_text("must survive")
    original_project = store / "project-original"
    real_fingerprint_at = maintenance._fingerprint_at  # noqa: SLF001 - exercise the deletion race boundary.
    fingerprint_calls = 0
    swapped = False

    def race_fingerprint_at(directory_fd: int, name: str) -> str:
        nonlocal fingerprint_calls, swapped
        fingerprint_calls += 1
        if fingerprint_calls == 2:
            project.rename(original_project)
            project.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_fingerprint_at(directory_fd, name)

    monkeypatch.setattr(maintenance, "_fingerprint_at", race_fingerprint_at)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(store), source="claude", keep_days=7)]

    run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert swapped
    assert fingerprint_calls == 2
    assert outside_victim.read_text() == "must survive"
    assert not (original_project / raw.name).exists()


@pytest.mark.parametrize("mutation", ["replace", "touch"])
def test_agent_prune_retains_raw_session_changed_after_successor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store = tmp_path / ".claude" / "projects"
    project = store / "project"
    project.mkdir(parents=True)
    raw = project / "session.jsonl"
    content = "verified raw session"
    raw.write_text(content)
    old_ns = 1_700_000_000_000_000_000
    os.utime(raw, ns=(old_ns, old_ns))
    _write_successor(tmp_path, "claude", "session", raw)
    real_fingerprint_at = maintenance._fingerprint_at  # noqa: SLF001 - inject the final-check race.
    fingerprint_calls = 0

    def mutate_before_final_fingerprint(directory_fd: int, name: str) -> str:
        nonlocal fingerprint_calls
        fingerprint_calls += 1
        if fingerprint_calls == 2:
            if mutation == "replace":
                replacement = raw.with_name("replacement.jsonl")
                replacement.write_text(content)
                os.utime(replacement, ns=(old_ns, old_ns))
                replacement.replace(raw)
            else:
                os.utime(raw, ns=(old_ns + 1, old_ns + 1))
        return real_fingerprint_at(directory_fd, name)

    monkeypatch.setattr(maintenance, "_fingerprint_at", mutate_before_final_fingerprint)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(store), source="claude", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert fingerprint_calls == 2
    assert reclaimed == 0
    assert raw.read_text() == content
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=changed-during-prune" in state.stdout.getvalue()


@pytest.mark.parametrize("mutation", ["replace", "touch", "rewrite"])
def test_grok_prune_retains_sibling_changed_after_successor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / ".grok" / "sessions"
    session = root / "grok-id"
    session.mkdir(parents=True)
    transcript = session / "updates.jsonl"
    sibling = session / "chat_history.jsonl"
    transcript_content = "verified raw"
    sibling_content = "related raw"
    transcript.write_text(transcript_content)
    sibling.write_text(sibling_content)
    old_ns = 1_700_000_000_000_000_000
    os.utime(transcript, ns=(old_ns, old_ns))
    os.utime(sibling, ns=(old_ns, old_ns))
    _write_successor(tmp_path, "grok", "grok-id", transcript)
    real_fingerprint_at = maintenance._fingerprint_at  # noqa: SLF001 - inject the sibling race.
    transcript_fingerprint_calls = 0
    changed_content = "changed raw"
    assert len(changed_content) == len(sibling_content)

    def mutate_sibling_before_final_fingerprint(directory_fd: int, name: str) -> str:
        nonlocal transcript_fingerprint_calls
        if name == transcript.name:
            transcript_fingerprint_calls += 1
        if name == transcript.name and transcript_fingerprint_calls == 2:
            if mutation == "replace":
                replacement = sibling.with_name("replacement.jsonl")
                replacement.write_text(sibling_content)
                os.utime(replacement, ns=(old_ns, old_ns))
                replacement.replace(sibling)
            elif mutation == "touch":
                os.utime(sibling, ns=(old_ns + 1, old_ns + 1))
            else:
                sibling.write_text(changed_content)
                os.utime(sibling, ns=(old_ns, old_ns))
        return real_fingerprint_at(directory_fd, name)

    monkeypatch.setattr(maintenance, "_fingerprint_at", mutate_sibling_before_final_fingerprint)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(root), source="grok", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}))

    assert transcript_fingerprint_calls == 2
    assert reclaimed == 0
    assert transcript.read_text() == transcript_content
    assert sibling.read_text() == (changed_content if mutation == "rewrite" else sibling_content)
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=changed-during-prune" in state.stdout.getvalue()


def test_archive_prune_deletion_stays_bound_to_open_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store = tmp_path / ".agents" / "sessions"
    lineage = store / "v1" / "claude" / "lineage"
    lineage.mkdir(parents=True)
    archived = lineage / "session.json"
    archived.write_text("discard")
    os.utime(archived, (1_700_000_000, 1_700_000_000))
    original_lineage = lineage.with_name("lineage-original")
    outside = tmp_path / "sibling"
    outside.mkdir()
    outside_victim = outside / archived.name
    outside_victim.write_text("preserve")
    real_stat_at = maintenance._stat_at  # noqa: SLF001 - exercise the archive deletion race boundary.
    swapped = False

    def race_stat_at(directory_fd: int, name: str) -> os.stat_result:
        nonlocal swapped
        if name == archived.name and not swapped:
            lineage.rename(original_lineage)
            lineage.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_stat_at(directory_fd, name)

    monkeypatch.setattr(maintenance, "_stat_at", race_stat_at)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(store), source="archive", keep_days=7)]

    run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert swapped
    assert not (original_lineage / archived.name).exists()
    assert lineage.is_symlink()
    assert outside_victim.read_text() == "preserve"


@pytest.mark.parametrize("mutation", ["replace", "touch"])
def test_archive_prune_retains_session_that_becomes_recent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store = tmp_path / ".agents" / "sessions"
    lineage = store / "v1" / "claude" / "lineage"
    lineage.mkdir(parents=True)
    archived = lineage / "session.json"
    content = "preserve"
    archived.write_text(content)
    old_ns = 1_700_000_000_000_000_000
    recent_ns = 1_800_000_000_000_000_000
    os.utime(archived, ns=(old_ns, old_ns))
    real_stat_at = maintenance._stat_at  # noqa: SLF001 - inject the age-check race.
    mutated = False

    def mutate_after_initial_stat(directory_fd: int, name: str) -> os.stat_result:
        nonlocal mutated
        info = real_stat_at(directory_fd, name)
        if name == archived.name and not mutated:
            if mutation == "replace":
                replacement = archived.with_name("replacement.json")
                replacement.write_text(content)
                os.utime(replacement, ns=(recent_ns, recent_ns))
                replacement.replace(archived)
            else:
                os.utime(archived, ns=(recent_ns, recent_ns))
            mutated = True
        return info

    monkeypatch.setattr(maintenance, "_stat_at", mutate_after_initial_stat)
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path=str(store), source="archive", keep_days=7)]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert mutated
    assert reclaimed == 0
    assert archived.read_text() == content


def test_agent_prune_retains_tampered_successor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    raw = tmp_path / ".claude" / "projects" / "project" / "session.jsonl"
    raw.parent.mkdir(parents=True)
    raw.write_text("raw")
    old = 1_700_000_000
    os.utime(raw, (old, old))
    generation = _write_successor(tmp_path, "claude", "session", raw)
    (generation / "transcript.jsonl").write_text("tampered\n")
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path="~/.claude/projects", source="claude", keep_days=7)]

    run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert raw.exists()
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=unreadable-successor" in state.stdout.getvalue()


def test_agent_prune_retains_successor_with_invalid_record_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    raw = tmp_path / ".claude" / "projects" / "project" / "session.jsonl"
    raw.parent.mkdir(parents=True)
    raw.write_text("raw")
    os.utime(raw, (1_700_000_000, 1_700_000_000))
    generation = _write_successor(tmp_path, "claude", "session", raw)
    transcript = b'{"ts":"","agent":"claude","sid":"session","role":42,"content":"saved"}\n'
    (generation / "transcript.jsonl").write_bytes(transcript)
    manifest_path = generation / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["transcript_sha256"] = hashlib.sha256(transcript).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    state = make_state()
    state.config.prune.agents.sessions = [SessionStoreConfig(path="~/.claude/projects", source="claude", keep_days=7)]

    run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert raw.exists()
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=unreadable-successor" in state.stdout.getvalue()


def test_agent_prune_retains_copilot_canonical_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    database = tmp_path / ".copilot/session-store.db"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"canonical Copilot session store")
    os.utime(database, (1_700_000_000, 1_700_000_000))
    state = make_state()
    state.config.prune.agents.sessions = [
        SessionStoreConfig(path="~/.copilot/session-store.db", source="copilot", keep_days=7)
    ]

    reclaimed = run_prune(state, PruneOptions(targets={"agents": "sessions"}, days=7))

    assert reclaimed == 0
    assert database.read_bytes() == b"canonical Copilot session store"
    assert isinstance(state.stdout, io.StringIO)
    assert "reason=ambiguous-shared-store" in state.stdout.getvalue()


def test_backup_orphans_is_recoverable_and_owner_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    orphan = tmp_path / ".config" / "old.conf"
    orphan.parent.mkdir()
    orphan.write_text("secret")
    state = make_state()

    backup = backup_orphans(state, [orphan])

    restored = backup / ".config" / "old.conf"
    assert restored.read_text() == "secret"
    assert not orphan.exists()
    assert backup.stat().st_mode & 0o777 == 0o700
    assert restored.parent.stat().st_mode & 0o777 == 0o700


def test_backup_orphans_refuses_symlinked_parent_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    monkeypatch.setenv("HOME", str(home))
    victim = outside / "victim.conf"
    victim.write_text("keep")
    (home / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(DotError, match="symbolic-link ancestor"):
        backup_orphans(make_state(), [home / "linked" / victim.name])

    assert victim.read_text() == "keep"


def test_backup_orphans_moves_final_symlink_without_following_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    monkeypatch.setenv("HOME", str(home))
    victim = outside / "victim.conf"
    victim.write_text("keep")
    orphan = home / ".oldrc"
    orphan.symlink_to(victim)

    backup = backup_orphans(make_state(), [orphan])

    restored = backup / orphan.name
    assert restored.is_symlink()
    assert restored.readlink() == victim
    assert victim.read_text() == "keep"


def test_backup_orphans_fails_closed_if_source_parent_is_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    source_parent = home / ".config"
    source_parent.mkdir(parents=True)
    orphan = source_parent / "settings.json"
    orphan.write_text("approved")
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_sibling = outside / orphan.name
    outside_sibling.write_text("must survive")
    original_parent = home / ".config-original"
    monkeypatch.setenv("HOME", str(home))
    real_allocate = maintenance._allocate_backup_directory  # noqa: SLF001 - inject the parent-swap race.
    swapped = False

    def swapping_allocate(home_path: Path, home_fd: int) -> tuple[Path, int]:
        nonlocal swapped
        result = real_allocate(home_path, home_fd)
        source_parent.rename(original_parent)
        source_parent.symlink_to(outside, target_is_directory=True)
        swapped = True
        return result

    monkeypatch.setattr(maintenance, "_allocate_backup_directory", swapping_allocate)

    with pytest.raises(DotError, match="source parent changed"):
        backup_orphans(make_state(), [orphan])

    assert swapped
    assert (original_parent / orphan.name).read_text() == "approved"
    assert outside_sibling.read_text() == "must survive"


def test_backup_orphans_allocates_an_exclusive_recovery_root_on_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    orphan = home / ".config" / "settings.json"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("approved")
    monkeypatch.setenv("HOME", str(home))
    fixed_now = datetime(2026, 9, 6, 10, 20, 30)

    class FixedDateTime:
        @classmethod
        def now(cls) -> datetime:
            return fixed_now

    monkeypatch.setattr(maintenance, "datetime", FixedDateTime)
    prior_backup = home / ".cache" / "dot" / "chezmoi-clean" / "20260906-102030"
    prior_file = prior_backup / ".config" / orphan.name
    prior_file.parent.mkdir(parents=True)
    prior_file.write_text("prior backup")

    backup = backup_orphans(make_state(), [orphan])

    assert backup != prior_backup
    assert prior_file.read_text() == "prior backup"
    assert (backup / ".config" / orphan.name).read_text() == "approved"


def test_chezmoi_probe_parent_swap_preserves_outside_file_and_cleans_bound_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    probe_parent = source / "nested"
    probe_parent.mkdir(parents=True)
    original_parent = source / "nested-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_probe = outside / "dot_victim"
    outside_probe.write_text("must survive")
    runner = RecordingRunner()
    real_run = runner.run
    swapped = False

    def swapping_run(
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        nonlocal swapped
        if tuple(args[:2]) == ("chezmoi", "target-path"):
            probe_parent.rename(original_parent)
            probe_parent.symlink_to(outside, target_is_directory=True)
            swapped = True
            return CommandResult(".victim\n", "", 0)
        return real_run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)

    monkeypatch.setattr(runner, "run", swapping_run)

    with pytest.raises(DotError, match="probe parent changed"):
        get_chezmoi_target_path(make_state(runner), source, "nested/dot_victim")

    assert swapped
    assert outside_probe.read_text() == "must survive"
    assert not (original_parent / "dot_victim").exists()


def test_chezmoi_probe_cleanup_preserves_same_name_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    probe = source / "dot_victim"
    runner = RecordingRunner()
    real_run = runner.run

    def replace_probe(
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        if tuple(args[:2]) == ("chezmoi", "target-path"):
            probe.unlink()
            probe.write_text("new source content")
            return CommandResult(".victim\n", "", 0)
        return real_run(args, cwd=cwd, input_text=input_text, env=env, timeout=timeout, check=check)

    monkeypatch.setattr(runner, "run", replace_probe)

    with pytest.raises(DotError, match="probe changed during cleanup"):
        get_chezmoi_target_path(make_state(runner), source, probe.name)

    assert probe.read_text() == "new source content"


def test_chezmoi_clean_propagates_mapping_failure_without_claiming_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    source = tmp_path / "source"
    home.mkdir()
    source.mkdir()
    monkeypatch.setenv("HOME", str(home))
    probe = source / "dot_oldrc"
    runner = RecordingRunner()
    runner.responses = {
        ("chezmoi", "source-path"): CommandResult(str(source), "", 0),
        ("chezmoi", "managed"): CommandResult("", "", 0),
        ("git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"): CommandResult(
            "dot_oldrc\n", "", 0
        ),
        ("chezmoi", "target-path", str(probe)): DotError("target mapping failed"),
    }
    state = make_state(runner)

    with pytest.raises(DotError, match=r"failed to map deleted chezmoi source.*target mapping failed"):
        run_chezmoi_clean(state, yes=True)

    assert not probe.exists()
    assert isinstance(state.stdout, io.StringIO)
    assert "No orphaned files found" not in state.stdout.getvalue()


def test_chezmoi_clean_propagates_probe_cleanup_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    source = tmp_path / "source"
    home.mkdir()
    source.mkdir()
    monkeypatch.setenv("HOME", str(home))
    probe = source / "dot_oldrc"
    runner = RecordingRunner()
    runner.responses = {
        ("chezmoi", "source-path"): CommandResult(str(source), "", 0),
        ("chezmoi", "managed"): CommandResult("", "", 0),
        ("git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"): CommandResult(
            "dot_oldrc\n", "", 0
        ),
        ("chezmoi", "target-path", str(probe)): CommandResult(".oldrc\n", "", 0),
    }

    def failing_cleanup(
        probe_path: Path,
        parent_fd: int,
        probe_fd: int,
        probe_metadata: tuple[int, ...] | None,
        created: list[maintenance._CreatedDirectory],
    ) -> None:
        del probe_path, parent_fd, probe_fd, probe_metadata, created
        raise DotError("simulated cleanup denial")

    monkeypatch.setattr(maintenance, "_cleanup_probe", failing_cleanup)
    state = make_state(runner)

    with pytest.raises(DotError, match=r"failed to map deleted chezmoi source.*simulated cleanup denial"):
        run_chezmoi_clean(state, yes=True)

    assert probe.exists()
    assert isinstance(state.stdout, io.StringIO)
    assert "No orphaned files found" not in state.stdout.getvalue()


def test_chezmoi_probe_refuses_symlinked_parent_escape(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    source.mkdir()
    outside.mkdir()
    (source / "linked").symlink_to(outside, target_is_directory=True)
    runner = RecordingRunner()

    with pytest.raises(DotError, match="symbolic-link ancestor"):
        get_chezmoi_target_path(make_state(runner), source, "linked/dot_victim")

    assert not (outside / "dot_victim").exists()
    assert not any(call[:2] == ("chezmoi", "target-path") for call in runner.calls)


def test_chezmoi_clean_maps_deleted_source_and_backs_up_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    source = tmp_path / "source"
    home.mkdir()
    source.mkdir()
    monkeypatch.setenv("HOME", str(home))
    orphan = home / ".oldrc"
    orphan.write_text("recover me")
    runner = RecordingRunner()
    probe = source / "dot_oldrc"
    runner.responses = {
        ("chezmoi", "source-path"): CommandResult(str(source), "", 0),
        ("chezmoi", "managed"): CommandResult(".still-managed\n", "", 0),
        ("git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"): CommandResult(
            "dot_oldrc\n", "", 0
        ),
        ("chezmoi", "target-path", str(probe)): CommandResult(".oldrc\n", "", 0),
    }
    state = make_state(runner)

    found = run_chezmoi_clean(state, yes=True)

    assert found == [orphan]
    assert not orphan.exists()
    backups = list((home / ".cache" / "dot" / "chezmoi-clean").glob("*/.oldrc"))
    assert len(backups) == 1
    assert backups[0].read_text() == "recover me"
    assert not probe.exists()


def test_chezmoi_clean_preview_and_rejected_confirmation_preserve_orphans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    source = tmp_path / "source"
    home.mkdir()
    source.mkdir()
    monkeypatch.setenv("HOME", str(home))
    orphan = home / ".oldrc"
    orphan.write_text("preserve")
    probe = source / "dot_oldrc"
    runner = RecordingRunner()
    runner.responses = {
        ("chezmoi", "source-path"): CommandResult(str(source), "", 0),
        ("chezmoi", "managed"): CommandResult("", "", 0),
        ("git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"): CommandResult(
            "dot_oldrc\n", "", 0
        ),
        ("chezmoi", "target-path", str(probe)): CommandResult(".oldrc\n", "", 0),
    }

    preview_state = make_state(runner)
    assert run_chezmoi_clean(preview_state) == [orphan]
    assert orphan.read_text() == "preserve"
    assert isinstance(preview_state.stdout, io.StringIO)
    assert "Re-run with --yes" in preview_state.stdout.getvalue()

    rejected_state = make_state(runner)
    rejected_state.stdin = io.StringIO("no\n")
    assert run_chezmoi_clean(rejected_state, interactive=True) == [orphan]
    assert orphan.read_text() == "preserve"
    assert isinstance(rejected_state.stdout, io.StringIO)
    assert "Clean up canceled" in rejected_state.stdout.getvalue()


def test_chezmoi_clean_filters_non_orphans_without_mutating_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    source = tmp_path / "source"
    home.mkdir()
    source.mkdir()
    monkeypatch.setenv("HOME", str(home))
    (source / "dot_existing").write_text("still sourced")
    managed = home / ".managed"
    managed.write_text("managed")
    empty_probe = source / "dot_empty"
    absent_probe = source / "dot_absent"
    managed_probe = source / "dot_managed"
    deleted = "README.md\nrun_once_setup\ndot_existing\ndot_empty\ndot_absent\ndot_managed\n"
    runner = RecordingRunner()
    runner.responses = {
        ("chezmoi", "source-path"): CommandResult(str(source), "", 0),
        ("chezmoi", "managed"): CommandResult(".managed\n", "", 0),
        ("git", "log", "--no-renames", "--diff-filter=D", "--name-only", "--pretty=format:"): CommandResult(
            deleted, "", 0
        ),
        ("chezmoi", "target-path", str(empty_probe)): CommandResult("", "", 0),
        ("chezmoi", "target-path", str(absent_probe)): CommandResult(".absent\n", "", 0),
        ("chezmoi", "target-path", str(managed_probe)): CommandResult(".managed\n", "", 0),
    }
    state = make_state(runner)

    assert run_chezmoi_clean(state, yes=True) == []

    assert managed.read_text() == "managed"
    assert not (home / ".absent").exists()
    assert not any(path.name.startswith("dot_") for path in source.iterdir() if path.name != "dot_existing")
    assert isinstance(state.stdout, io.StringIO)
    assert "No orphaned files found" in state.stdout.getvalue()


def test_chezmoi_clean_rejects_invalid_mode_and_source(tmp_path: Path) -> None:
    state = make_state()
    with pytest.raises(DotError, match="mutually exclusive"):
        run_chezmoi_clean(state, yes=True, interactive=True)

    runner = RecordingRunner()
    runner.responses[("chezmoi", "source-path")] = CommandResult("", "", 0)
    with pytest.raises(DotError, match="source path is empty"):
        run_chezmoi_clean(make_state(runner))

    missing = tmp_path / "missing"
    runner.responses[("chezmoi", "source-path")] = CommandResult(str(missing), "", 0)
    with pytest.raises(DotError, match="source path is not a directory"):
        run_chezmoi_clean(make_state(runner))


def test_chezmoi_probe_rejects_unsafe_or_occupied_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    state = make_state()

    for relative in ("../victim", str(tmp_path / "absolute")):
        with pytest.raises(DotError, match="unsafe chezmoi source path"):
            get_chezmoi_target_path(state, source, relative)

    occupied = source / "nested" / "dot_file"
    occupied.parent.mkdir()
    occupied.write_text("must survive")
    with pytest.raises(FileExistsError):
        get_chezmoi_target_path(state, source, "nested/dot_file")
    assert occupied.read_text() == "must survive"


def test_backup_orphans_rejects_paths_outside_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.write_text("preserve")
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(DotError, match="outside home"):
        backup_orphans(make_state(), [outside])

    assert outside.read_text() == "preserve"


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
    ) -> int:
        if tuple(args[:2]) == ("git", "push") and not self.mutated:
            self.mutation()
            self.mutated = True
        return super().interactive(args, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr, env=env)


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
    state._config = Config()  # noqa: SLF001 - isolate the release contract from the workstation config.

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


def test_config_shape_used_by_maintenance_remains_strict() -> None:
    config = Config()

    assert config.prune.docker.level == "build"
    assert config.prune.python.level == "cache"
    assert config.release.default_branch == "main"
