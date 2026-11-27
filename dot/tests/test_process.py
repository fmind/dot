from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from fmind_dot import process as process_module
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.process import Runner, diagnostic_line, run_parallel
from tests.fakes import TerminalIO


@pytest.mark.parametrize("mode", ["captured", "pull-worker", "status-worker", "doctor-worker", "interactive"])
def test_sigterm_exits_130_and_stops_child(tmp_path: Path, mode: str) -> None:
    started, finished, release = tmp_path / "started", tmp_path / "finished", tmp_path / "release"
    child = (
        "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); p=pathlib.Path(sys.argv[3]);\n"
        "while not p.exists(): time.sleep(0.01)\n"
        "pathlib.Path(sys.argv[2]).touch()"
    )
    launcher = (
        "import os,sys; from pathlib import Path; from fmind_dot import cli,repository,system; "
        "from fmind_dot.process import Runner; from fmind_dot.state import State\n"
        "cmd=[sys.executable,'-c',os.environ['C'],os.environ['S'],os.environ['F'],os.environ['R']]\n"
        "def inv():\n"
        " r=Runner(); m=os.environ['M']\n"
        " if m=='captured': r.run(cmd)\n"
        " elif m=='pull-worker':\n"
        "  repository.find_git_repositories=lambda *_a:[Path('.')]; repository._pull_repository=lambda *_a,**_k:r.run(cmd); repository.run_pull(State(runner=r))\n"
        " elif m=='status-worker':\n"
        "  repository.find_git_repositories=lambda *_a:[Path('.')]; repository._repository_status=lambda *_a,**_k:r.run(cmd); repository.gather_status(State(runner=r))\n"
        " elif m=='doctor-worker':\n"
        "  r.which=lambda _t:Path(sys.executable); orig=r.run; r.run=lambda _a,**kw:orig(cmd,**kw); system.DOCTOR_TOOLS=('x',); system._tool_results(State(runner=r))\n"
        " else: r.interactive(cmd)\n"
        " return 0\n"
        "cli.app=inv; cli.main()\n"
    )
    env = os.environ | {"C": child, "F": str(finished), "M": mode, "R": str(release), "S": str(started)}
    proc = subprocess.Popen(
        [sys.executable, "-c", launcher],
        cwd=Path(__file__).parents[1],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while not started.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert started.exists(), f"child did not start (exit: {proc.poll()})"
        proc.send_signal(process_module.signal.SIGTERM)
        out, err = proc.communicate(timeout=30)
        release.touch()
        time.sleep(0.1)
        assert (proc.returncode, out, err, finished.exists()) == (130, "", "Cancelled.\n", False)
    finally:
        if proc.poll() is None:
            release.touch()
            proc.terminate()
        proc.communicate(timeout=30)


def test_runner_basics_cancellation_and_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Runner()
    assert runner.which(sys.executable) == Path(sys.executable)
    assert runner.which("fmind-dot-nonexistent-bin") is None
    for fn in (runner.run, runner.interactive):
        with pytest.raises(DotError, match="empty command"):
            fn([])
    assert runner.run([sys.executable, "-c", "import sys; sys.exit(3)"], check=False).returncode == 3
    with pytest.raises(DotError, match="command failed"):
        runner.run([sys.executable, "-c", "import sys; sys.exit(3)"])
    with pytest.raises(CommandTimeoutError, match="timed out"):
        runner.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)

    runner.cancel()
    with pytest.raises(DotError, match="cancelled"):
        runner.run([sys.executable, "-c", "from pathlib import Path; Path('nope').touch()"], cwd=tmp_path)
    assert not (tmp_path / "nope").exists()

    r2, popen, children = Runner(), subprocess.Popen, []

    def launch(*args, **kwargs):
        c = popen(*args, **kwargs)
        children.append(c)
        r2.cancel()
        return c

    monkeypatch.setattr(process_module.subprocess, "Popen", launch)
    with pytest.raises(DotError, match="operation cancelled"):
        r2.run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=2)
    assert children[0].poll() is not None
    assert children[0].stdout.closed
    assert children[0].stderr.closed


@pytest.mark.parametrize("mode", ["captured", "interactive"])
@pytest.mark.parametrize("signum", [process_module.signal.SIGINT, process_module.signal.SIGTERM])
def test_signal_during_child_launch_stops_child(
    mode: str, signum: process_module.signal.Signals, monkeypatch: pytest.MonkeyPatch
) -> None:
    popen_cls: Any = subprocess.Popen
    runner, execute_child, children = Runner(), popen_cls._execute_child, []  # noqa: SLF001

    def launch(proc, *args, **kwargs) -> None:
        execute_child(proc, *args, **kwargs)
        children.append(proc)
        process_module.signal.raise_signal(signum)

    def interrupt(_s, _f) -> None:
        raise KeyboardInterrupt

    prev = process_module.signal.signal(signum, interrupt)
    monkeypatch.setattr(subprocess.Popen, "_execute_child", launch)
    try:
        invoke = runner.run if mode == "captured" else runner.interactive
        with pytest.raises(KeyboardInterrupt):
            invoke([sys.executable, "-c", "import time; time.sleep(10)"])
        assert children[0].poll() is not None
        assert process_module.signal.getsignal(signum) is interrupt
        assert not runner._processes  # noqa: SLF001
    finally:
        process_module.signal.signal(signum, prev)
        with suppress(ProcessLookupError):
            children[0].kill() if children and children[0].poll() is None else None
        if children:
            children[0].wait(timeout=5)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("token ghp_0123456789abcdefghijklmnopqrstuvwxyz", "token <redacted>"),
        ("key " + "sk-proj-" + "0123456789abcdefghij", "key <redacted>"),
        ("google " + "AIza" + "SyA1234567890abcdefghijklmnopqrstuvwx", "google <redacted>"),
        ("oauth " + "ya29." + "a0AfH6SMBx1234567890abcdef.segment", "oauth <redacted>"),
        ("refresh " + "1//0g" + "abcdefghijklmnopqrstuv", "refresh <redacted>"),
        ("aws " + "AKIA" + "IOSFODNN7EXAMPLE denied", "aws <redacted> denied"),
        ("jwt " + ".".join(("eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxMjM0NTY3ODkwIn0", "sigPart123")), "jwt <redacted>"),
        ("token " + "hf_" + "0123456789abcdefghijk", "token <redacted>"),
        ("sig " + "A1b2C3d4" * 5, "sig <redacted>"),
        (
            "fatal: /home/user/projects/a-very-long-name/src/module: x",
            "fatal: /home/user/projects/a-very-long-name/src/module: x",
        ),
        ("open ~/projects/another-very-long-name/subdirectory", "open ~/projects/another-very-long-name/subdirectory"),
        ("read /tmp/ghp_0123456789abcdefghijklmnopqrstuvwxyz/x", "read /tmp/<redacted>"),
        ("https://host/" + "A1b2C3d4" * 5, "https:<redacted>"),
        ("error: token /" + "A1b2C3d4" * 5 + " rejected", "error: token /<redacted> rejected"),
        ("open (/tmp/" + "A1b2C3d4" * 3 + ").", "open (/tmp/<redacted>)."),
        ("read /tmp/" + "A1b2C3d4" * 3 + ".json", "read /tmp/" + "A1b2C3d4" * 3 + ".json"),
        (
            "open /var/folders/7k/T/0F3C2A1B-4D5E-4F60-8A9B-C0D1E2F3A4B5/x",
            "open /var/folders/7k/T/0F3C2A1B-4D5E-4F60-8A9B-C0D1E2F3A4B5/x",
        ),
        ("read ~/.cache/uv/archive-v0/" + "9f86d081" * 8, "read ~/.cache/uv/archive-v0/" + "9f86d081" * 8),
        ("load /usr/lib/x86_64-linux-gnu/libpython3.14.so", "load /usr/lib/x86_64-linux-gnu/libpython3.14.so"),
        ("", ""),
    ],
    ids=[
        "ghp",
        "openai-proj",
        "google-aiza",
        "google-ya29",
        "google-refresh",
        "aws-akia",
        "jwt",
        "hf-token",
        "high-entropy-sig",
        "abs-path",
        "tilde-path",
        "tmp-ghp-path",
        "https-url-token",
        "slash-token",
        "paren-tmp-token",
        "tmp-json-file",
        "macos-uuid-tmpdir",
        "uv-sha256-cache",
        "linux-soname-path",
        "empty",
    ],
)
def test_diagnostic_line_redacts_tokens_and_preserves_paths(
    text: str, expected: str, request: pytest.FixtureRequest
) -> None:
    param_id = request.node.name.partition("[")[2].removesuffix("]")
    assert param_id
    # Keep synthetic credentials out of pytest nodeids (.pytest_cache/v/cache/nodeids -> betterleaks).
    assert diagnostic_line(param_id) == param_id
    assert diagnostic_line(text) == expected


def test_interactive_env_stdin_eof_and_sigint_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = Runner().interactive(
        [
            sys.executable,
            "-c",
            "import os,pathlib; pathlib.Path('out').write_text(os.environ['T']); raise SystemExit(6)",
        ],
        cwd=tmp_path,
        env={"T": "ok"},
    )
    assert code == 6
    assert (tmp_path / "out").read_text() == "ok"

    reader = "import sys; print(len(sys.stdin.read()))"
    assert Runner().run([sys.executable, "-c", reader], input_text="x" * (256 * 1024)).stdout == f"{256 * 1024}\n"
    assert Runner().run([sys.executable, "-c", reader], input_text="").stdout == "0\n"

    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(process_module.os, "killpg", lambda p, s: signals.append((p, s)))
    with pytest.raises(KeyboardInterrupt):
        Runner().interactive([sys.executable, "-c", "import os,signal; signal.signal(2, 0); os.kill(os.getpid(), 2)"])
    assert signals == []

    opened_calls: list[list[str]] = []
    with monkeypatch.context() as mp:
        mp.setattr(process_module.sys, "platform", "linux")
        mp.delenv("DISPLAY", raising=False)
        mp.delenv("WAYLAND_DISPLAY", raising=False)
        mp.setattr(process_module.shutil, "which", lambda _name: "/usr/bin/xdg-open")
        mp.setattr(process_module.subprocess, "Popen", lambda cmd, **_kw: opened_calls.append(cmd))
        process_module._open_browser("https://accounts.google.com/o/oauth2/auth")  # noqa: SLF001
        assert opened_calls == []
        mp.setenv("DISPLAY", ":0")
        mp.setenv("SSH_TTY", "/dev/pts/0")
        process_module._open_browser("https://accounts.google.com/o/oauth2/auth")  # noqa: SLF001
        assert opened_calls == []
        mp.delenv("SSH_TTY", raising=False)
        mp.delenv("SSH_CONNECTION", raising=False)
        for bad_url in (
            "http://example.com",
            "file:///tmp/evil.html",
            "https://",
            "https://" + "u:" + "p@example.com/auth",
            "https://accounts.google.com/o/oauth2/auth with space",
            "https://accounts.google.com/o/oauth2/auth\n",
            "https://accounts.google.com/o/oauth2/auth\x7f",
        ):
            process_module._open_browser(bad_url)  # noqa: SLF001
        process_module._open_browser("https://accounts.google.com/o/oauth2/auth")  # noqa: SLF001
    assert opened_calls == [["/usr/bin/xdg-open", "https://accounts.google.com/o/oauth2/auth"]]

    opened_urls: list[str] = []
    monkeypatch.setattr(process_module, "_open_browser", opened_urls.append)
    url_re = re.compile(r"https://accounts\.google\.com/o/oauth2/[^\s<>\"'`()\[\]{}\x00-\x1f]+")
    script = (
        "import sys; "
        r"sys.stderr.write('Open:\n  (\x1b[34mhttps://accounts.google.com/o/oauth2/auth?x=1.\x1b[0m)\n"
        r"  https://accounts.google.com/o/oauth2/auth?x=2\n')"
    )
    tty_err = TerminalIO()
    assert Runner().interactive([sys.executable, "-c", script], stderr=tty_err, open_url=url_re) == 0
    assert opened_urls == ["https://accounts.google.com/o/oauth2/auth?x=1"]
    assert "oauth2/auth?x=2" in tty_err.getvalue()

    det_err = io.StringIO()
    assert Runner().interactive([sys.executable, "-c", script], stderr=det_err, open_url=url_re) == 0
    assert len(opened_urls) == 1
    assert "oauth2/auth?x=1" in det_err.getvalue()


def test_run_parallel_inline_workers_errors_and_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Runner()
    with pytest.raises(ValueError, match="workers must be at least 1"):
        run_parallel(runner, lambda x: x, [], 0)
    assert run_parallel(runner, lambda x: x, [], 2) == []

    monkeypatch.setattr(process_module, "ThreadPoolExecutor", Mock(side_effect=AssertionError("pool spawned")))
    assert run_parallel(runner, lambda x: x * 2, [21], 4) == [42]

    monkeypatch.undo()
    assert run_parallel(runner, lambda x: x + 1, [1, 2, 3], 2) == [2, 3, 4]
    with pytest.raises(DotError, match="boom"):
        run_parallel(runner, lambda x: (_ for _ in ()).throw(DotError("boom")) if x == 1 else x, [0, 1], 2)
    assert runner.run([sys.executable, "-c", "print('ok')"]).stdout == "ok\n"

    with pytest.raises(KeyboardInterrupt):
        run_parallel(runner, lambda _x: (_ for _ in ()).throw(KeyboardInterrupt()), [0], 1)
    with pytest.raises(DotError, match="cancelled"):
        runner.run([sys.executable, "-c", "pass"])


def test_runner_run_decodes_and_encodes_utf8_under_c_locale() -> None:
    dot_src = str(Path(__file__).resolve().parents[1] / "src")
    script = (
        "import sys; "
        f"sys.path.insert(0, {dot_src!r}); "
        "from fmind_dot.process import Runner; "
        "sample = '\\u276f\\u21b3\\u03bcs\\u2014\\n'; "
        "res = Runner().run([sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'], input_text=sample); "
        "assert res.stdout == sample, repr(res.stdout); "
        "assert '\\ufffd' not in res.stdout"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_sigterm_as_keyboard_interrupt_restores_handler() -> None:
    prev = process_module.signal.getsignal(process_module.signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt), process_module.sigterm_as_keyboard_interrupt():
        process_module.signal.raise_signal(process_module.signal.SIGTERM)
    assert process_module.signal.getsignal(process_module.signal.SIGTERM) is prev


def test_runner_run_bytes_and_stream_stdout() -> None:
    runner = Runner()
    raw = runner.run_bytes([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff\\x00ok')"])
    assert raw.stdout == b"\xff\x00ok"
    assert raw.returncode == 0
    with pytest.raises(DotError, match="command failed"):
        runner.run_bytes([sys.executable, "-c", "raise SystemExit(3)"], check=True)

    payload, rc, stderr = runner.stream_stdout(
        [sys.executable, "-c", "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1])"],
        lambda stream: stream.read(),
        input_bytes=b"\x00abc\xff",
        timeout=10,
    )
    assert (payload, rc, stderr) == (b"\xffcba\x00", 0, b"")

    # Empty command and pre-cancelled runner fail closed.
    with pytest.raises(DotError, match="empty command"):
        runner.stream_stdout([], lambda stream: stream.read())
    cancelled = Runner()
    cancelled.cancel()
    with pytest.raises(DotError, match="cancelled"):
        cancelled.stream_stdout([sys.executable, "-c", "pass"], lambda stream: stream.read())

    # Timeout raises CommandTimeoutError cleanly (no ValueError: read of closed file).
    with pytest.raises(CommandTimeoutError, match="timed out"):
        runner.stream_stdout(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            lambda stream: stream.read(),
            timeout=0.15,
        )

    # Non-zero exit + large stderr (>64 KiB) drains cleanly without deadlock, retaining first 4096 bytes.
    _, rc_err, err_bytes = runner.stream_stdout(
        [sys.executable, "-c", "import sys; sys.stderr.buffer.write(b'E' * 80000); raise SystemExit(7)"],
        lambda stream: stream.read(),
        timeout=10,
    )
    assert rc_err == 7
    assert len(err_bytes) == 4096

    # Early-returning handler against huge stdout does not deadlock; stdout closure breaks the pipe cleanly.
    head, _, _ = runner.stream_stdout(
        [
            sys.executable,
            "-c",
            "import sys\ntry:\n sys.stdout.buffer.write(b'X' * 500000)\nexcept BrokenPipeError:\n pass",
        ],
        lambda stream: stream.read(4),
        timeout=10,
    )
    assert head == b"XXXX"

    # Handler exception terminates child cleanly and propagates.
    with pytest.raises(RuntimeError, match="handler boom"):
        runner.stream_stdout(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            lambda _stream: (_ for _ in ()).throw(RuntimeError("handler boom")),
            timeout=10,
        )


def test_stream_stdout_timeout_reaps_grandchild_and_signal_handles_eperm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A leader that spawns a grandchild keeping stderr open (and ignoring SIGTERM) must be reaped via PGID SIGKILL
    # without leaking the grandchild or deadlocking BufferedReader.close().
    monkeypatch.setattr(process_module, "_TERMINATION_GRACE_SECONDS", 0.2)
    pid_file = tmp_path / "grandchild.pid"
    leader = (
        "import pathlib, signal, subprocess, sys, time; "
        "gc = subprocess.Popen([sys.executable, '-c', "
        "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)']); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(gc.pid)); "
        "time.sleep(60)"
    )
    with pytest.raises(CommandTimeoutError, match="timed out"):
        Runner().stream_stdout([sys.executable, "-c", leader], lambda stream: stream.read(), timeout=0.25)

    assert pid_file.exists()
    gc_pid = int(pid_file.read_text().strip())
    deadline = time.monotonic() + 5.0
    alive = True
    while time.monotonic() < deadline:
        try:
            os.kill(gc_pid, 0)
        except ProcessLookupError:
            alive = False
            break
        time.sleep(0.05)
    assert not alive, f"grandchild pid {gc_pid} leaked after stream_stdout timeout"

    # PermissionError from os.killpg must not fall through to send_signal or escape _signal.
    fake_proc = Mock()
    fake_proc.pid = 999999
    fake_proc.send_signal.side_effect = PermissionError("eperm")
    monkeypatch.setattr(process_module.os, "killpg", Mock(side_effect=PermissionError("eperm")))
    process_module._signal(fake_proc, process_module.signal.SIGTERM, group=True)  # noqa: SLF001
    fake_proc.send_signal.assert_not_called()
    process_module._signal(fake_proc, process_module.signal.SIGTERM, group=False)  # noqa: SLF001
