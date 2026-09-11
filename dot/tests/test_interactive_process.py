from __future__ import annotations

import os
import pty
import select
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import pytest

# Each case cold-starts an interpreter that imports the whole CLI, so the bound must
# absorb a loaded `-n auto` run; a satisfied wait exits immediately and never pays it.
ARRIVAL_DEADLINE_SECONDS = 30


@pytest.mark.parametrize("streamed", [False, True])
def test_cancellation_stops_grandchildren(tmp_path: Path, streamed: bool) -> None:
    started, release, finished = (tmp_path / name for name in ("started", "release", "finished"))
    grandchild = (
        "import os,pathlib,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        "deadline=time.monotonic()+30\n"
        "while not pathlib.Path(sys.argv[2]).exists():\n"
        " if time.monotonic()>deadline: raise SystemExit(0)\n"
        " time.sleep(0.01)\n"
        "pathlib.Path(sys.argv[3]).write_text('unexpected write')\n"
    )
    child = "import subprocess,sys,time\nsubprocess.Popen([sys.executable,'-c',*sys.argv[1:]])\ntime.sleep(30)\n"
    launcher = (
        "import sys\n"
        "import fmind_dot.cli as cli\n"
        "from fmind_dot.process import Runner\n"
        f"callback = (lambda line: None) if {streamed!r} else None\n"
        "cli._invoke_app=lambda: Runner().interactive(\n"
        " [sys.executable,'-c',*sys.argv[1:]],on_stdout_line=callback)\n"
        "cli.main()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", launcher, child, grandchild, str(started), str(release), str(finished)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        while not started.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert started.exists()
        process.terminate()
        process.wait(timeout=ARRIVAL_DEADLINE_SECONDS)
        assert process.returncode == 130
        release.touch()
        deadline = time.monotonic() + 0.4
        while not finished.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not finished.exists(), "a grandchild wrote after dot was cancelled"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=ARRIVAL_DEADLINE_SECONDS)
        # started may exist with no PID yet: write_text creates the file before the bytes land.
        pid = started.read_text().strip() if started.exists() else ""
        if pid.isdigit():
            with suppress(ProcessLookupError):
                os.kill(int(pid), signal.SIGKILL)


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("interrupt", ["keyboard", "sigterm"])
def test_terminal_input_suspend_resume_and_interrupt(tmp_path: Path, streamed: bool, interrupt: str) -> None:
    child_pid_path = tmp_path / "terminal-child"
    child = (
        "import os,pathlib,signal,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        # Exercise OS signal termination rather than Python exception/shutdown timing.
        "signal.signal(signal.SIGINT,signal.SIG_DFL)\n"
        "signal.signal(signal.SIGCONT,lambda *_args: print('RESUMED',flush=True))\n"
        "print('READY',flush=True)\n"
        "value=input()\n"
        "print('VALUE:'+value,flush=True)\n"
        "while True: time.sleep(0.1)\n"
    )
    launcher = (
        "import os,sys\n"
        "import fmind_dot.cli as cli\n"
        "from fmind_dot.process import Runner\n"
        "def invoke():\n"
        " try:\n"
        f"  callback=(lambda line: None) if {streamed!r} else None\n"
        "  return Runner().interactive([sys.executable,'-c',sys.argv[1],sys.argv[2]],on_stdout_line=callback)\n"
        " finally: print('RESTORED:'+str(os.tcgetpgrp(0)==os.getpgrp()),flush=True)\n"
        "cli._invoke_app=invoke\n"
        "cli.main()\n"
    )
    pid, terminal = pty.fork()
    if pid == 0:
        # The PTY child executes only the current interpreter and this literal fixture.
        os.execl(sys.executable, sys.executable, "-c", launcher, child, str(child_pid_path))  # noqa: S606
    output = bytearray()
    reaped = False

    def read_until(expected: bytes) -> None:
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        while expected not in output and time.monotonic() < deadline:
            if select.select([terminal], [], [], 0.05)[0]:
                try:
                    output.extend(os.read(terminal, 65536))
                except OSError:
                    break
        assert expected in output, output.decode(errors="replace")

    try:
        read_until(b"READY")
        os.write(terminal, b"hello\n")
        read_until(b"VALUE:hello")
        os.write(terminal, b"\x1a")
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        status = 0
        while time.monotonic() < deadline:
            observed, status = os.waitpid(pid, os.WUNTRACED | os.WNOHANG)
            if observed:
                break
            time.sleep(0.01)
        assert os.WIFSTOPPED(status), output.decode(errors="replace")
        output.clear()
        os.kill(pid, signal.SIGCONT)
        read_until(b"RESUMED")
        if interrupt == "keyboard":
            os.write(terminal, b"\x03")
        else:
            os.kill(pid, signal.SIGTERM)
        read_until(b"RESTORED:True")
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        while time.monotonic() < deadline:
            observed, status = os.waitpid(pid, os.WNOHANG)
            if observed:
                reaped = True
                break
            time.sleep(0.01)
        assert reaped
        assert os.WIFEXITED(status)
        assert os.WEXITSTATUS(status) == 130, output.decode(errors="replace")
    finally:
        if child_pid_path.exists():
            with suppress(ProcessLookupError):
                os.killpg(int(child_pid_path.read_text()), signal.SIGKILL)
        if not reaped:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)


@pytest.mark.parametrize(("input_bytes", "expected_exit"), [(b"\x03", 130), (b"n\n", 1), (b"\x04", 1)])
def test_prune_prompt_cancellation_is_clean(tmp_path: Path, input_bytes: bytes, expected_exit: int) -> None:
    launcher = (
        "import os,sys\nfrom pathlib import Path\n"
        "from fmind_dot.process import Runner\nfrom fmind_dot.cli import main\n"
        "Runner.which=lambda self,command: Path('/fixture') / command\n"
        "Runner.interactive=lambda *args,**kwargs: sys.exit('UNEXPECTED CLEANUP')\n"
        "os.environ.pop('DOT_CONFIG_PATH',None)\n"
        "sys.argv=['dot','prune','all']\nmain()\n"
    )
    pid, terminal = pty.fork()
    if pid == 0:
        os.environ["HOME"] = str(tmp_path)
        os.execl(sys.executable, sys.executable, "-c", launcher)  # noqa: S606
    output = bytearray()
    reaped = False
    try:
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        while b"Clean caches for" not in output and time.monotonic() < deadline:
            if select.select([terminal], [], [], 0.05)[0]:
                output.extend(os.read(terminal, 65536))
        assert b"Clean caches for" in output, output.decode(errors="replace")
        os.write(terminal, input_bytes)
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        while time.monotonic() < deadline:
            if select.select([terminal], [], [], 0.05)[0]:
                with suppress(OSError):
                    output.extend(os.read(terminal, 65536))
            observed, status = os.waitpid(pid, os.WNOHANG)
            if observed:
                reaped = True
                assert os.WIFEXITED(status)
                assert os.WEXITSTATUS(status) == expected_exit, output.decode(errors="replace")
                break
        assert reaped
        assert b"Traceback" not in output
        assert b"Abort" not in output
        assert b"UNEXPECTED CLEANUP" not in output
        assert b"Cancelled" in output
    finally:
        if not reaped:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)
