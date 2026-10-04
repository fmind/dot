from __future__ import annotations

import os
import pty
import select
import signal
import sys
import time
from contextlib import suppress
from pathlib import Path

import pytest

# Each case cold-starts an interpreter that imports the whole CLI, so the bound must
# absorb a loaded `-n auto` run; a satisfied wait exits immediately and never pays it.
ARRIVAL_DEADLINE_SECONDS = 30


@pytest.mark.parametrize("interrupt", ["keyboard", "sigterm"])
def test_terminal_input_and_interrupt(tmp_path: Path, interrupt: str) -> None:
    child_pid_path = tmp_path / "terminal-child"
    child = (
        "import os,pathlib,signal,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        # Exercise OS signal termination rather than Python exception/shutdown timing.
        "signal.signal(signal.SIGINT,signal.SIG_DFL)\n"
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
        "  return Runner().interactive([sys.executable,'-c',sys.argv[1],sys.argv[2]])\n"
        " finally: print('RETURNED',flush=True)\n"
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
        # Ctrl+Z reaches dot and the child natively; a PTY without a job-control shell discards it.
        if interrupt == "keyboard":
            os.write(terminal, b"\x03")
        else:
            os.kill(pid, signal.SIGTERM)
        read_until(b"RETURNED")
        deadline = time.monotonic() + ARRIVAL_DEADLINE_SECONDS
        status = 0
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


@pytest.mark.parametrize(
    ("input_bytes", "expected_exit"),
    [(b"\x03", 130), (b"n\n", 1), (b"\x04", 1), (b"\n", 1), (b"yes\n", 0), (b"Y\n", 0), (b"invalid\nyes\n", 0)],
)
def test_prune_prompt_cancellation_is_clean(tmp_path: Path, input_bytes: bytes, expected_exit: int) -> None:
    cleanup = "(print('CLEANUP') or 0)" if expected_exit == 0 else "sys.exit('UNEXPECTED CLEANUP')"
    launcher = (
        "import os,sys\nfrom pathlib import Path\n"
        "from fmind_dot.process import Runner\nfrom fmind_dot.cli import main\n"
        "Runner.which=lambda self,command: Path('/fixture') / command\n"
        f"Runner.interactive=lambda *args,**kwargs: {cleanup}\n"
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
        # Send control keys as soon as the complete confirmation prompt is visible.
        prompt_end = b"? [y/N]: "
        while prompt_end not in output and time.monotonic() < deadline:
            if select.select([terminal], [], [], 0.05)[0]:
                output.extend(os.read(terminal, 65536))
        assert prompt_end in output, output.decode(errors="replace")
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
        assert reaped, output.decode(errors="replace")
        # Process exit can precede our next read of its final cancellation message.
        while select.select([terminal], [], [], 0)[0]:
            try:
                chunk = os.read(terminal, 65536)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)
        assert b"Traceback" not in output
        assert b"Abort" not in output
        assert b"UNEXPECTED CLEANUP" not in output
        if expected_exit == 0:
            assert output.count(b"CLEANUP") == 6
        if input_bytes.startswith(b"invalid"):
            assert b"Error: invalid input" in output
            assert output.count(prompt_end) == 2
        if expected_exit != 0:
            assert b"Cancelled" in output
    finally:
        if not reaped:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)
