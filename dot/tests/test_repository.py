from __future__ import annotations

import json
import os
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from fmind_dot.cli import app
from fmind_dot.config import Config, PullConfig
from fmind_dot.errors import DotError, NotGitWorkTreeError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.repository import (
    RepositoryStatus,
    find_git_repositories,
    gather_status,
    git_failure,
    git_root,
    run_pull,
    run_status,
)
from tests.fakes import CliRunner, ScriptedRunner, buf, make_state

V2 = ("git", "--no-optional-locks", "status", "--porcelain=v2", "--branch")


def _v2(
    branch: str = "main", *, ahead: int = 0, behind: int = 0, dirty: bool = False, upstream: bool = True
) -> CommandResult:
    lines = [f"# branch.head {branch}"] + (
        ["# branch.upstream origin/main", f"# branch.ab +{ahead} -{behind}"] if upstream else []
    )
    if dirty:
        lines.append("1 .M N... 100644 100644 100644 0 0 w.py")
    return CommandResult("\n".join(lines) + "\n", "", 0)


def _git(runner: Runner, path: Path, *args: str) -> str:
    return runner.run(
        ["git", "-c", "user.name=F", "-c", "user.email=f@example.invalid", "-c", "commit.gpgsign=false", *args],
        cwd=path,
        timeout=10,
    ).stdout.strip()


@pytest.mark.parametrize(
    ("stderr", "needle"),
    [
        (" ! [rejected] main -> main (non-fast-forward)\n", "git push failed (1): ! [rejected]"),
        ("fatal: Authentication failed for https://oauth2:" + "ghp_" + "a" * 30 + "@github.com/\n", "<redacted>"),
        ("ignored\nfatal: bad object\n", "git fetch failed (1): fatal: bad object"),
        ("", "git fetch failed (1)"),
    ],
)
def test_git_failure_uses_first_sanitized_error_line(stderr: str, needle: str) -> None:
    msg = git_failure(
        ["--no-optional-locks", "fetch" if "reject" not in stderr else "push"], CommandResult("", stderr, 1)
    )
    assert needle in msg
    assert "ghp_" not in msg


def test_git_root_and_find_git_repositories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "work"
    local, ext = ws / "local", tmp_path / "external"
    (local / ".git").mkdir(parents=True)
    (ext / ".git").mkdir(parents=True)
    (ws / "linked").symlink_to(ext, target_is_directory=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = Config(pull=PullConfig(directories=["~/work", str(ws) + "/", "~/missing"]))
    assert find_git_repositories(make_state(ScriptedRunner(), cfg)) == [local]

    runner = ScriptedRunner(
        {"git"},
        responses={
            ("git", "rev-parse", "--show-toplevel"): [
                CommandResult("", "err", 128),
                CommandResult("", "", 0),
                CommandResult(f"{local}\n", "", 0),
            ]
        },
    )
    with pytest.raises(NotGitWorkTreeError):
        git_root(make_state(runner), tmp_path)
    with pytest.raises(DotError, match="empty repository root"):
        git_root(make_state(runner), tmp_path)
    assert find_git_repositories(make_state(runner), [local]) == [local.resolve()]


def test_pull_fast_forward_divergence_dirty_and_no_upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    runner = Runner()
    g = partial(_git, runner)
    remote, seed, co = tmp_path / "remote.git", tmp_path / "seed", tmp_path / "co"
    g(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    g(tmp_path, "clone", str(remote), str(seed))
    g(seed, "commit", "--allow-empty", "-m", "init")
    g(seed, "push", "-u", "origin", "main")
    g(tmp_path, "clone", str(remote), str(co))
    g(seed, "commit", "--allow-empty", "-m", "upstream")
    g(seed, "push", "origin", "main")

    st = make_state(runner, Config(pull=PullConfig(directories=[str(co)])))
    [pulled] = run_pull(st, as_json=True)
    assert (pulled.commits, pulled.error) == (1, "")
    assert json.loads(buf(st.stdout))["schema"] == "dot.pull/v1"

    st_txt = make_state(runner, Config(pull=PullConfig(directories=[str(co)])))
    g(co, "commit", "--allow-empty", "-m", "local")
    assert run_pull(st_txt)[0].ahead == 1
    assert "1 unpushed" in buf(st_txt.stdout)

    g(seed, "commit", "--allow-empty", "-m", "diverge")
    g(seed, "push", "origin", "main")
    with pytest.raises(DotError, match="failed to pull 1 repositories"):
        run_pull(make_state(runner, Config(pull=PullConfig(directories=[str(co)]))))
    assert "diverged" in _git(runner, co, "status") or "diverge" not in g(co, "log", "-1", "--format=%s")

    (co / "dirty.txt").write_text("x")
    fetch_head = co / ".git/FETCH_HEAD"
    fetch_head.unlink(missing_ok=True)
    assert run_pull(make_state(runner, Config(pull=PullConfig(directories=[str(co)]))))[0].skipped == "dirty worktree"
    assert not fetch_head.exists()


def test_run_pull_skips_post_fetch_dirty_and_no_upstream(tmp_path: Path) -> None:
    repo = tmp_path / "ws/r"
    (repo / ".git").mkdir(parents=True)
    cfg = Config(pull=PullConfig(directories=[str(tmp_path / "ws")]))
    sr = ScriptedRunner(
        {"git"},
        responses={V2: [_v2(), _v2(dirty=True)], ("git", "fetch", "--prune"): [CommandResult("", "", 0)]},
    )
    assert run_pull(make_state(sr, cfg))[0].skipped == "dirty worktree"

    sr2 = ScriptedRunner(
        {"git"},
        responses={
            V2: [_v2(upstream=False), _v2(upstream=False)],
            ("git", "fetch", "--prune"): [CommandResult("", "", 0)],
        },
    )
    st2 = make_state(sr2, cfg)
    assert run_pull(st2)[0].no_upstream is True
    assert "skipped (no upstream)" in buf(st2.stdout)
    assert run_pull(make_state(ScriptedRunner({"git"}), Config(pull=PullConfig(directories=[])))) == []


def test_fetch_disables_askpass_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    probe = tmp_path / "askpass.called"
    askpass = tmp_path / "askpass.sh"
    askpass.write_text(f"#!/bin/sh\ntouch {probe}\nexit 1\n")
    askpass.chmod(0o755)
    monkeypatch.setenv("GIT_ASKPASS", str(askpass))
    monkeypatch.setenv("SSH_ASKPASS", str(askpass))
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(Runner(), repo, "init")

    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="test"')
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            del format, args

    with ThreadingHTTPServer(("127.0.0.1", 0), H) as srv:
        Thread(target=srv.handle_request, daemon=True).start()
        _git(Runner(), repo, "remote", "add", "origin", f"http://127.0.0.1:{srv.server_address[1]}/r.git")
        [status] = gather_status(make_state(Runner()), [repo], fetch=True)
    assert "failed to fetch repository" in status.error
    assert not probe.exists()


def test_status_operations_worktree_attention_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    repo = ws / "wt"
    repo.mkdir(parents=True)
    meta = tmp_path / "common/worktrees/wt"
    (meta / "rebase-merge").mkdir(parents=True)
    (repo / ".git").write_text(f"gitdir: {meta}\n")
    git_dir_cmd = ("git", "rev-parse", "--absolute-git-dir")
    sr = ScriptedRunner(
        {"git"},
        responses={
            V2: [_v2("(detached)"), _v2(ahead=1), _v2()],
            ("git", "rev-parse", "--short", "HEAD"): [CommandResult("abc1234\n", "", 0)],
            git_dir_cmd: [CommandResult(f"{meta}\n", "", 0)] * 3,
        },
    )
    cfg = Config(pull=PullConfig(directories=[str(ws)]))
    st = make_state(sr, cfg)
    [s1] = run_status(st, as_json=True)
    assert (s1.branch, s1.operation, s1.needs_attention) == ("abc1234", "rebase", True)
    assert json.loads(buf(st.stdout))["remote_state"] == "cached"

    st_attn = make_state(sr, cfg)
    run_status(st_attn, needs_attention=True)
    assert "ahead=1" in buf(st_attn.stdout)

    (meta / "rebase-merge").rmdir()
    st_clean = make_state(sr, cfg)
    run_status(st_clean, needs_attention=True)
    assert "clean and in sync" in buf(st_clean.stdout)

    monkeypatch.setattr(
        "fmind_dot.repository.gather_status", lambda *_a, **_k: [RepositoryStatus("r", "w", error="err")]
    )
    cli = CliRunner().invoke(app, ["status", "--json"])
    assert cli.exit_code != 0
    assert json.loads(cli.stdout)["complete"] is False
